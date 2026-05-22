"""
Configuration manager for environment discovery, validation,
and Pulumi YAML generation.
"""

import importlib
import json
from dataclasses import fields, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pypuwa.secrets import is_interpolation_reference


class ConfigurationManager:
    """
    Discovers environment configs, validates them, and generates Pulumi YAML.

    Usage:
        manager = ConfigurationManager(
            environments={"staging": staging_config, "production": production_config}
        )

        # Or auto-discover from a directory
        manager = ConfigurationManager(environments_dir=Path("config/environments"))

        stack = manager.generate_stack_config("my-stack", "staging")
    """

    def __init__(
        self,
        environments: Optional[Dict[str, Any]] = None,
        environments_dir: Optional[Path] = None,
        environments_module_prefix: str = "config.environments",
    ):
        if environments is not None:
            self._environments = environments
        elif environments_dir is not None:
            self._environments = self._discover_environments(
                environments_dir, environments_module_prefix
            )
        else:
            self._environments = {}

    def _discover_environments(
        self, env_dir: Path, module_prefix: str
    ) -> Dict[str, Any]:
        """Auto-discover environment configs from a directory."""
        configs: Dict[str, Any] = {}

        if not env_dir.exists():
            return configs

        for env_file in env_dir.glob("*.py"):
            if env_file.name == "__init__.py":
                continue

            env_name = env_file.stem
            try:
                module_name = f"{module_prefix}.{env_name}"
                module = importlib.import_module(module_name)
                config_obj = getattr(module, f"{env_name}_config", None)
                if config_obj is not None:
                    configs[env_name] = config_obj
            except Exception as e:
                print(f"Warning: Failed to load environment config '{env_name}': {e}")

        return configs

    @property
    def environments(self) -> Dict[str, Any]:
        """All loaded environment configs."""
        return self._environments

    def list_environments(self) -> List[str]:
        """List available environment names."""
        return list(self._environments.keys())

    def generate_stack_config(
        self,
        stack_name: str,
        environment_type: str,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a complete stack configuration dict.

        Args:
            stack_name: The Pulumi stack name.
            environment_type: Which environment config to use.
            overrides: Optional dict to deep-merge on top.

        Returns:
            Fully resolved configuration dictionary.
        """
        if environment_type not in self._environments:
            raise ValueError(
                f"Environment '{environment_type}' not found. "
                f"Available: {self.list_environments()}"
            )

        env_config = self._environments[environment_type]
        config_dict = self._to_dict(env_config)

        if overrides:
            config_dict = self._deep_merge(config_dict, overrides)

        context = self._build_context(config_dict, stack_name)
        config_dict = self._interpolate(config_dict, context)

        return config_dict

    def validate(self, environment_type: str) -> List[str]:
        """Validate an environment config. Returns list of issues."""
        if environment_type not in self._environments:
            return [f"Environment '{environment_type}' not found"]

        issues: List[str] = []
        config = self._environments[environment_type]

        if not is_dataclass(config) and not hasattr(config, "__dict__"):
            issues.append("Config is not a dataclass or object with attributes")

        return issues

    def to_pulumi_yaml(self, stack_name: str, environment_type: str) -> Dict[str, Any]:
        """Generate Pulumi YAML-compatible config dict."""
        config_dict = self.generate_stack_config(stack_name, environment_type)
        return {"config": self._to_pulumi_format(config_dict)}

    def _to_dict(self, obj: Any) -> Any:
        """Convert dataclass/object to dict recursively."""
        if is_dataclass(obj) and not isinstance(obj, type):
            result = {}
            for f in fields(obj):
                if not f.name.startswith("_"):
                    result[f.name] = self._to_dict(getattr(obj, f.name))
            return result
        elif hasattr(obj, "__dict__") and not isinstance(obj, type):
            return {
                k: self._to_dict(v)
                for k, v in obj.__dict__.items()
                if not k.startswith("_")
            }
        elif isinstance(obj, dict):
            return {k: self._to_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._to_dict(item) for item in obj]
        return obj

    def _build_context(self, config_dict: Dict[str, Any], stack_name: str) -> Dict[str, Any]:
        """Build interpolation context."""
        context: Dict[str, Any] = {
            "stack_name": stack_name,
            "stack": stack_name,
            "timestamp": datetime.now().strftime("%Y%m%d-%H%M%S"),
        }
        self._flatten_paths(config_dict, context)
        return context

    def _flatten_paths(
        self, obj: Any, context: Dict[str, Any], prefix: str = ""
    ) -> None:
        """Flatten config into dot-notation paths."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                path = f"{prefix}.{key}" if prefix else key
                if isinstance(value, (dict, list)):
                    self._flatten_paths(value, context, path)
                else:
                    context[path] = value

    def _interpolate(self, config: Any, context: Dict[str, Any]) -> Any:
        """Apply interpolation to all string values."""
        if isinstance(config, str):
            import re

            def replace(match: Any) -> str:
                path = match.group(1)
                if path in context:
                    resolved = context[path]
                    if isinstance(resolved, str) and resolved.startswith("secret:"):
                        return match.group(0)
                    return str(resolved)
                return match.group(0)

            config = re.sub(r"\$\{([^}]+)\}", replace, config)
            try:
                return config.format(**context)
            except KeyError:
                return config
        elif isinstance(config, dict):
            return {k: self._interpolate(v, context) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._interpolate(item, context) for item in config]
        return config

    def _to_pulumi_format(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Convert config dict to Pulumi YAML format (secrets as {secure: ...})."""
        result: Dict[str, Any] = {}
        for key, value in config_dict.items():
            if key.startswith("_"):
                continue
            if isinstance(value, dict):
                result[key] = self._to_pulumi_format(value)
            elif isinstance(value, str) and value.startswith("secret:"):
                secret_key = value[7:]
                if is_interpolation_reference(secret_key):
                    result[key] = secret_key
                else:
                    result[key] = {"secure": "PLACEHOLDER_SECRET"}
            elif isinstance(value, str) and is_interpolation_reference(value):
                result[key] = value
            else:
                result[key] = value
        return result

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dicts."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
