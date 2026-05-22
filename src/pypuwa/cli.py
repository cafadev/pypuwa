"""
pypuwa CLI — deploy orchestrator.

Syncs Python config to Pulumi YAML, detects new secrets,
offers interactive secret management, and runs pulumi up.

Usage:
    pypuwa deploy <environment> [--dry-run] [--sync-only] [--backup]
    pypuwa preview <environment>
    pypuwa sync <environment>
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

from pypuwa.manager import ConfigurationManager
from pypuwa.secrets import is_interpolation_reference, is_secret


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    MAGENTA = "\033[0;35m"
    NC = "\033[0m"


class ConfigSyncEngine:
    """Syncs Python config to Pulumi YAML, preserving existing encrypted secrets."""

    def __init__(
        self,
        environment_name: str,
        manager: ConfigurationManager,
        project_name: str = "pypuwa",
    ):
        self.environment_name = environment_name
        self.manager = manager
        self.project_name = project_name
        self.config_module_name = environment_name.replace("-", "_")
        self.pulumi_config_path = Path(f"Pulumi.{environment_name}.yaml")

    def load_existing_pulumi_config(self) -> Optional[Dict[str, Any]]:
        if not self.pulumi_config_path.exists():
            return None
        try:
            with open(self.pulumi_config_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            _print("RED", "SYNC", f"Failed to load existing Pulumi config: {e}")
            return None

    def generate_python_config(self) -> Optional[Dict[str, Any]]:
        try:
            return self.manager.generate_stack_config(
                self.environment_name, self.config_module_name
            )
        except Exception as e:
            _print("RED", "SYNC", f"Failed to generate Python config: {e}")
            return None

    def detect_changes(self) -> Tuple[bool, Dict[str, Any]]:
        _print("BLUE", "SYNC", "Detecting configuration changes...")

        python_config = self.generate_python_config()
        if python_config is None:
            return False, {}

        existing_config = self.load_existing_pulumi_config()
        if existing_config is None:
            _print("BLUE", "SYNC", "No existing Pulumi config — will create new file")
            return True, {"type": "new_file", "config": python_config}

        existing_pulumi = existing_config.get("config", {})
        normalized = self._normalize_existing(existing_pulumi)
        changes = self._compare(normalized, python_config)

        if changes:
            return True, changes

        _print("GREEN", "SYNC", "No configuration changes detected")
        return False, {}

    def sync(self, changes: Dict[str, Any], backup: bool = False) -> bool:
        if not changes:
            return True

        _print("BLUE", "SYNC", "Syncing configuration changes to Pulumi file...")

        if backup and self.pulumi_config_path.exists():
            self._backup()

        try:
            existing_config = self.load_existing_pulumi_config()
            new_config = self.generate_python_config()
            if new_config is None:
                return False

            merged = self._merge_preserve_secrets(existing_config, new_config)
            self._write(merged)

            _print("GREEN", "SYNC", f"Configuration synced to {self.pulumi_config_path}")
            self._display_changes(changes)
            return True

        except Exception as e:
            _print("RED", "SYNC", f"Failed to sync configuration: {e}")
            return False

    def _normalize_existing(self, existing: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {}
        for key, value in existing.items():
            if key.startswith(f"{self.project_name}:"):
                normalized[key[len(self.project_name) + 1 :]] = value
            else:
                normalized[key] = value
        return normalized

    def _compare(self, existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        changes: Dict[str, Any] = {
            "added": {},
            "modified": {},
            "removed": {},
        }

        for key, value in new.items():
            if key not in existing:
                changes["added"][key] = value
            elif existing[key] != value:
                changes["modified"][key] = {"old": existing[key], "new": value}

        for key in existing:
            if key not in new:
                changes["removed"][key] = existing[key]

        return {k: v for k, v in changes.items() if v}

    def _merge_preserve_secrets(
        self, existing: Optional[Dict[str, Any]], new_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        if existing is None:
            return {"config": new_config}

        existing_pulumi = existing.get("config", {})
        secrets_map: Dict[str, Any] = {}

        for key, value in existing_pulumi.items():
            normalized_key = key
            if key.startswith(f"{self.project_name}:"):
                normalized_key = key[len(self.project_name) + 1 :]
            if self._has_secrets(value):
                secrets_map[normalized_key] = value

        merged = dict(new_config)
        for key, existing_value in secrets_map.items():
            if key in merged and isinstance(existing_value, dict) and isinstance(merged[key], dict):
                merged[key] = self._deep_merge_secrets(existing_value, merged[key])

        return {"config": merged}

    def _deep_merge_secrets(self, existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(new)
        for key, existing_value in existing.items():
            if key not in result:
                continue
            new_value = result[key]
            if isinstance(existing_value, dict) and isinstance(new_value, dict):
                if "secure" in existing_value:
                    result[key] = existing_value
                else:
                    result[key] = self._deep_merge_secrets(existing_value, new_value)
            elif isinstance(existing_value, dict) and "secure" in existing_value:
                result[key] = existing_value
        return result

    def _has_secrets(self, value: Any) -> bool:
        if isinstance(value, dict):
            if "secure" in value:
                return True
            return any(self._has_secrets(v) for v in value.values())
        return False

    def _write(self, config: Dict[str, Any]) -> None:
        pulumi_config = dict(config)
        if "config" in pulumi_config:
            prefixed: Dict[str, Any] = {}
            for key, value in pulumi_config["config"].items():
                if key == "providers" and isinstance(value, dict):
                    for provider_name, provider_cfg in value.items():
                        if isinstance(provider_cfg, dict):
                            provider_key = provider_name.replace("_", "-")
                            for cfg_key, cfg_value in provider_cfg.items():
                                prefixed[f"{provider_key}:{cfg_key}"] = cfg_value
                    continue
                if not key.startswith(f"{self.project_name}:"):
                    prefixed[f"{self.project_name}:{key}"] = value
                else:
                    prefixed[key] = value
            pulumi_config["config"] = prefixed

        with open(self.pulumi_config_path, "w") as f:
            yaml.dump(pulumi_config, f, default_flow_style=False, sort_keys=False)

    def _backup(self) -> None:
        import shutil

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = Path(f"{self.pulumi_config_path}.backup_{timestamp}")
        shutil.copy2(self.pulumi_config_path, backup_path)
        _print("BLUE", "SYNC", f"Backup created: {backup_path}")

    def _display_changes(self, changes: Dict[str, Any]) -> None:
        if changes.get("type") == "new_file":
            _print("BLUE", "SYNC", "Created new Pulumi configuration file")
            return
        if changes.get("added"):
            _print("BLUE", "SYNC", "Added configuration keys:")
            for key in changes["added"]:
                print(f"  + {key}")
        if changes.get("modified"):
            _print("BLUE", "SYNC", "Modified configuration keys:")
            for key in changes["modified"]:
                print(f"  ~ {key}")
        if changes.get("removed"):
            _print("YELLOW", "SYNC", "Removed configuration keys:")
            for key in changes["removed"]:
                print(f"  - {key}")


class SecretDetector:
    """Detects new secrets in Python config that need values set in Pulumi."""

    def __init__(self, manager: ConfigurationManager):
        self.manager = manager

    def find_new_secrets(
        self, stack_name: str, config_module_name: str
    ) -> Tuple[List[str], List[str]]:
        _print("CYAN", "SECRETS", "Detecting new secrets...")

        envs = self.manager.environments
        if config_module_name not in envs:
            _print("YELLOW", "SECRETS", f"Config module '{config_module_name}' not found")
            return [], []

        env_config = envs[config_module_name]
        source_secrets, derived_secrets = self._discover_secrets(env_config)
        existing = self._get_existing_secret_paths(stack_name)

        new_source = [s for s in source_secrets if s not in existing]
        new_derived = [s for s in derived_secrets if s not in existing]

        return new_source, new_derived

    def _discover_secrets(
        self, config_obj: Any, prefix: str = ""
    ) -> Tuple[List[str], List[str]]:
        source: List[str] = []
        derived: List[str] = []

        if not hasattr(config_obj, "__dict__"):
            return source, derived

        for attr_name, attr_value in config_obj.__dict__.items():
            if attr_name.startswith("_"):
                continue
            current_path = f"{prefix}.{attr_name}" if prefix else attr_name

            if is_secret(attr_value):
                secret_key = str(attr_value)[7:]  # Remove "secret:" prefix
                if is_interpolation_reference(secret_key):
                    derived.append(current_path)
                else:
                    source.append(current_path)
            elif hasattr(attr_value, "__dict__"):
                sub_source, sub_derived = self._discover_secrets(attr_value, current_path)
                source.extend(sub_source)
                derived.extend(sub_derived)

        return source, derived

    def _get_existing_secret_paths(self, stack_name: str) -> Set[str]:
        try:
            pulumi_file = Path(f"Pulumi.{stack_name}.yaml")
            if not pulumi_file.exists():
                return set()

            with open(pulumi_file, "r") as f:
                pulumi_config = yaml.safe_load(f)

            if not pulumi_config or "config" not in pulumi_config:
                return set()

            existing: Set[str] = set()
            self._find_encrypted_paths(pulumi_config["config"], existing)
            return existing

        except Exception:
            return set()

    def get_all_secret_paths(self, stack_name: str) -> List[str]:
        """Get all existing encrypted secret paths from the Pulumi YAML."""
        existing = self._get_existing_secret_paths(stack_name)
        return sorted(existing)

    def _find_encrypted_paths(
        self, data: Dict[str, Any], result: Set[str], prefix: str = ""
    ) -> None:
        for key, value in data.items():
            current = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                if "secure" in value:
                    result.add(current)
                else:
                    self._find_encrypted_paths(value, result, current)


class InteractiveSecretManager:
    """Interactive secret management with arrow-key selection."""

    def __init__(self, stack_name: str):
        self.stack_name = stack_name

    def handle_new_secrets(
        self, source_secrets: List[str], derived_secrets: List[str]
    ) -> bool:
        import questionary

        if not source_secrets and not derived_secrets:
            return True

        print()
        _print("CYAN", "SECRETS", "New secrets detected in Python configuration:")

        if derived_secrets:
            print(f"  {Colors.BLUE}Derived secrets{Colors.NC} (auto-resolved):")
            for s in derived_secrets:
                print(f"    - {s}")

        if not source_secrets:
            _print("CYAN", "SECRETS", "No source secrets to set — all derived!")
            return True

        print(f"  {Colors.CYAN}Source secrets{Colors.NC} (need values):")
        for s in source_secrets:
            print(f"    - {s}")
        print()

        selected = questionary.checkbox(
            "Select secrets to set now (space to toggle, enter to confirm):",
            choices=[questionary.Choice(title=s, value=s, checked=True) for s in source_secrets],
        ).ask()

        if selected is None:
            _print("YELLOW", "SECRETS", "Interrupted")
            return True

        if not selected:
            _print("YELLOW", "SECRETS", "No secrets selected. Set them later with:")
            _print("YELLOW", "SECRETS", "  pulumi config set --secret --path <key> <value>")
            return True

        return self._prompt_secrets(selected)

    def offer_secret_updates(self, existing_secrets: List[str]) -> bool:
        """Offer to update existing secret values with arrow-key selection."""
        import questionary

        if not existing_secrets:
            return True

        print()
        action = questionary.select(
            "Would you like to update any existing secret values?",
            choices=[
                questionary.Choice(title="No, continue to deploy", value="no"),
                questionary.Choice(title="Yes, select secrets to update", value="yes"),
            ],
        ).ask()

        if action is None or action == "no":
            return True

        selected = questionary.checkbox(
            "Select secrets to update (space to select, enter to confirm):",
            choices=[questionary.Choice(title=s, value=s) for s in existing_secrets],
        ).ask()

        if selected is None or not selected:
            return True

        return self._prompt_secrets(selected)

    def _prompt_secrets(self, secrets: List[str]) -> bool:
        import questionary

        try:
            subprocess.run(
                ["pulumi", "stack", "select", self.stack_name],
                check=True,
                capture_output=True,
            )

            for secret_path in secrets:
                value = questionary.password(
                    f"Enter value for {secret_path}:"
                ).ask()

                if value is None:
                    _print("YELLOW", "SECRETS", "Interrupted")
                    return True

                if value.strip():
                    subprocess.run(
                        [
                            "pulumi", "config", "set", "--secret",
                            "--path", secret_path, value,
                        ],
                        check=True,
                    )
                    _print("GREEN", "SECRETS", f"Set secret: {secret_path}")
                else:
                    _print("YELLOW", "SECRETS", f"Skipped: {secret_path}")

            return True
        except subprocess.CalledProcessError as e:
            _print("RED", "SECRETS", f"Failed to set secrets: {e}")
            return False
        except KeyboardInterrupt:
            _print("YELLOW", "SECRETS", "Interrupted")
            return True


class DeployOrchestrator:
    """Orchestrates the full deploy flow: sync -> secrets -> pulumi up."""

    def __init__(
        self,
        environment_name: str,
        manager: ConfigurationManager,
        project_name: str = "pypuwa",
        dry_run: bool = False,
        sync_only: bool = False,
        backup: bool = False,
        runner: str = "pulumi",
    ):
        self.environment_name = environment_name
        self.stack_name = environment_name
        self.config_module_name = environment_name.replace("-", "_")
        self.dry_run = dry_run
        self.sync_only = sync_only
        self.backup = backup
        self.runner = runner

        self.sync_engine = ConfigSyncEngine(environment_name, manager, project_name)
        self.secret_detector = SecretDetector(manager)
        self.secret_manager = InteractiveSecretManager(environment_name)

    def execute(self) -> bool:
        print(f"\n  {Colors.CYAN}pypuwa deploy{Colors.NC}")
        print(f"  Stack: {Colors.YELLOW}{self.stack_name}{Colors.NC}")
        print(f"  Config: {Colors.YELLOW}Pulumi.{self.environment_name}.yaml{Colors.NC}")
        if self.dry_run:
            print(f"  {Colors.MAGENTA}DRY RUN{Colors.NC}")
        print()

        # Step 1: Sync config
        has_changes, changes = self.sync_engine.detect_changes()
        if has_changes:
            if not self.sync_engine.sync(changes, backup=self.backup):
                return False

        if self.sync_only:
            _print("GREEN", "DEPLOY", "Sync completed (--sync-only)")
            return True

        # Step 2: Detect new secrets
        if not self.dry_run:
            new_source, new_derived = self.secret_detector.find_new_secrets(
                self.stack_name, self.config_module_name
            )
            if new_source or new_derived:
                if not self.secret_manager.handle_new_secrets(new_source, new_derived):
                    return False
            else:
                _print("GREEN", "SECRETS", "No new secrets detected")

        # Step 3: Offer to update existing secrets
        if not self.dry_run:
            existing = self.secret_detector.get_all_secret_paths(self.stack_name)
            if existing:
                if not self.secret_manager.offer_secret_updates(sorted(existing)):
                    return False

        # Step 4: Run pulumi
        if self.dry_run:
            _print("GREEN", "DEPLOY", "Dry run completed — no deployment")
            return True

        return self._run_pulumi()

    def _run_pulumi(self) -> bool:
        _print("BLUE", "DEPLOY", "Running Pulumi deployment...")
        try:
            subprocess.run(
                [self.runner, "stack", "select", self.stack_name],
                check=True,
                capture_output=True,
            )
            subprocess.run([self.runner, "up"], check=True)
            _print("GREEN", "DEPLOY", "Deployment completed successfully!")
            return True
        except subprocess.CalledProcessError as e:
            _print("RED", "DEPLOY", f"Deployment failed: {e}")
            return False
        except KeyboardInterrupt:
            _print("YELLOW", "DEPLOY", "Deployment interrupted")
            return True


def _print(color: str, tag: str, message: str) -> None:
    c = getattr(Colors, color, Colors.NC)
    print(f"{c}[{tag}]{Colors.NC} {message}")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pypuwa",
        description="pypuwa — Python Pulumi Wrapper CLI",
    )
    subparsers = parser.add_subparsers(dest="command")

    # deploy
    deploy_parser = subparsers.add_parser(
        "deploy", help="Sync config and run pulumi up"
    )
    deploy_parser.add_argument("environment", help="Environment name (e.g., staging, production)")
    deploy_parser.add_argument("--dry-run", action="store_true", help="Sync config without deploying")
    deploy_parser.add_argument("--sync-only", action="store_true", help="Only sync config, skip secrets and deploy")
    deploy_parser.add_argument("--backup", action="store_true", help="Backup existing Pulumi YAML before sync")
    deploy_parser.add_argument("--project-name", default="pypuwa", help="Pulumi project name for config prefixes")
    deploy_parser.add_argument("--runner", default="pulumi", help="Command to run Pulumi (e.g., 'pulumi', 'uv run pulumi')")

    # preview (alias for deploy --dry-run)
    preview_parser = subparsers.add_parser(
        "preview", help="Sync config and show what would change (no deploy)"
    )
    preview_parser.add_argument("environment", help="Environment name")
    preview_parser.add_argument("--project-name", default="pypuwa")

    # sync (alias for deploy --sync-only)
    sync_parser = subparsers.add_parser(
        "sync", help="Sync Python config to Pulumi YAML only"
    )
    sync_parser.add_argument("environment", help="Environment name")
    sync_parser.add_argument("--backup", action="store_true")
    sync_parser.add_argument("--project-name", default="pypuwa")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    # Add current directory to Python path so environment configs can import
    # project-local modules (e.g., "from config.base.stack import ...")
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    # Load environments from the current project
    # Users must have config/environments/ in their working directory
    env_dir = Path("config/environments")
    if not env_dir.exists():
        _print("RED", "CLI", f"Directory '{env_dir}' not found in current directory")
        _print("RED", "CLI", "Run pypuwa from your infrastructure project root")
        return 1

    manager = ConfigurationManager(
        environments_dir=env_dir,
        environments_module_prefix="config.environments",
    )

    if not manager.environments:
        _print("RED", "CLI", "No environments found in config/environments/")
        return 1

    project_name = getattr(args, "project_name", "pypuwa")

    if args.command == "deploy":
        orchestrator = DeployOrchestrator(
            environment_name=args.environment,
            manager=manager,
            project_name=project_name,
            dry_run=args.dry_run,
            sync_only=args.sync_only,
            backup=args.backup,
            runner=args.runner,
        )
    elif args.command == "preview":
        orchestrator = DeployOrchestrator(
            environment_name=args.environment,
            manager=manager,
            project_name=project_name,
            dry_run=True,
        )
    elif args.command == "sync":
        orchestrator = DeployOrchestrator(
            environment_name=args.environment,
            manager=manager,
            project_name=project_name,
            sync_only=True,
            backup=getattr(args, "backup", False),
        )
    else:
        parser.print_help()
        return 1

    success = orchestrator.execute()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
