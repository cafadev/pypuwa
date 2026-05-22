"""
Configuration resolver with dot-notation access and automatic
environment detection, secret resolution, and interpolation.
"""

import copy
import os
from typing import Any, Dict, Optional, Union

import pulumi

from pypuwa.interpolation import InterpolationResolver
from pypuwa.secrets import get_secret_key, is_interpolation_reference, is_secret
from pypuwa.stack import BaseStackConfig


class SecretResolver:
    """Resolves secret markers to actual values via Pulumi config."""

    def __init__(self, pulumi_config: pulumi.Config):
        self._config = pulumi_config
        self._cache: Dict[str, pulumi.Output[str]] = {}

    def resolve(self, path: str) -> pulumi.Output[str]:
        """Resolve a secret path to a Pulumi Output."""
        if path in self._cache:
            return self._cache[path]

        path_parts = path.split(".")
        if len(path_parts) < 2:
            raise ValueError(f"Invalid secret path: {path}")

        service_name = path_parts[0]

        try:
            service_config_dict = self._config.require_object(service_name)
            current: Any = service_config_dict
            for part in path_parts[1:]:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    raise KeyError(f"Path '{path}' not found in config")

            if isinstance(current, dict) and "secure" in current:
                try:
                    self._cache[path] = self._config.require_secret(path)
                except Exception:
                    self._cache[path] = pulumi.Output.from_input(
                        f"[Secret {path} not available]"
                    )
            elif isinstance(current, str) and is_interpolation_reference(current):
                actual_path = current[2:-1]
                return self.resolve(actual_path)
            else:
                self._cache[path] = pulumi.Output.from_input(str(current))

        except Exception:
            try:
                self._cache[path] = self._config.require_secret(path)
            except Exception:
                self._cache[path] = pulumi.Output.from_input(
                    f"[Secret {path} not available]"
                )

        return self._cache[path]

    def resolve_in_object(self, obj: Any, path_prefix: str = "") -> Any:
        """Recursively resolve all secrets in a config object."""
        if not hasattr(obj, "__dict__"):
            return obj

        resolved = copy.deepcopy(obj)

        for attr_name, attr_value in resolved.__dict__.items():
            current_path = f"{path_prefix}.{attr_name}" if path_prefix else attr_name

            if is_secret(attr_value):
                secret_key = get_secret_key(attr_value)
                if is_interpolation_reference(secret_key):
                    actual_path = secret_key[2:-1]
                    resolved.__dict__[attr_name] = self.resolve(actual_path)
                else:
                    resolved.__dict__[attr_name] = self.resolve(current_path)
            elif isinstance(attr_value, str) and is_interpolation_reference(attr_value):
                actual_path = attr_value[2:-1]
                resolved.__dict__[attr_name] = self.resolve(actual_path)
            elif hasattr(attr_value, "__dict__"):
                resolved.__dict__[attr_name] = self.resolve_in_object(
                    attr_value, current_path
                )

        return resolved


class ConfigObject:
    """Wrapper providing dot-notation access to dictionary data."""

    def __init__(self, data: Dict[str, Any]):
        self._data = data
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, ConfigObject(value))
            else:
                setattr(self, key, value)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        if name in self._data:
            value = self._data[name]
            if isinstance(value, dict):
                return ConfigObject(value)
            return value
        raise AttributeError(f"Configuration '{name}' not found")

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __repr__(self) -> str:
        return f"ConfigObject({self._data})"


class ConfigResolver:
    """
    Main configuration resolver providing dot-notation access to all services.

    Auto-detects the current environment from the Pulumi stack name,
    loads the corresponding config, and resolves interpolations + secrets.

    Usage:
        from pypuwa.config import create_config

        config = create_config(
            environments={"staging": staging_config, "production": production_config},
            default_environment="staging",
        )

        # Dot-notation access with auto-resolution
        db_name = config.services.my_api.DATABASE.NAME
    """

    def __init__(
        self,
        environments: Optional[Dict[str, BaseStackConfig]] = None,
        default_environment: str = "develop",
        environment_variable: str = "PYPUWA_ENVIRONMENT",
    ):
        self._environments = environments or {}
        self._default_environment = default_environment
        self._env_var = environment_variable
        self._pulumi_config: Optional[pulumi.Config] = None
        self._secret_resolver: Optional[SecretResolver] = None
        self._interpolation_resolver: Optional[InterpolationResolver] = None
        self._stack_config: Optional[BaseStackConfig] = None

        try:
            self._pulumi_config = pulumi.Config()
            self._secret_resolver = SecretResolver(self._pulumi_config)
        except Exception:
            pass

    def _detect_environment(self) -> str:
        """Detect environment from env var, then Pulumi stack name."""
        env_type = os.environ.get(self._env_var)
        if env_type:
            return env_type

        try:
            stack_name = pulumi.get_stack()
            if stack_name and stack_name != "stack":
                if stack_name in self._environments:
                    return stack_name

                underscore = stack_name.replace("-", "_")
                if underscore in self._environments:
                    return underscore

                if "-" in stack_name:
                    for part in stack_name.split("-"):
                        if part in self._environments:
                            return part
                        if part.replace("-", "_") in self._environments:
                            return part.replace("-", "_")
        except Exception:
            pass

        return self._default_environment

    def _load_config(self) -> BaseStackConfig:
        """Load and cache the stack config for the current environment."""
        if self._stack_config is None:
            env = self._detect_environment()
            self._stack_config = self._environments.get(
                env, self._environments.get(self._default_environment, BaseStackConfig())
            )
        return self._stack_config

    def _get_interpolation_resolver(self) -> InterpolationResolver:
        if self._interpolation_resolver is None:
            config = self._load_config()
            self._interpolation_resolver = InterpolationResolver(
                config_data=config,
                environment_type=self._detect_environment(),
            )
        return self._interpolation_resolver

    def _process(self, service_config: Any, service_name: str) -> Any:
        """Resolve interpolations then secrets for a service config."""
        try:
            resolver = self._get_interpolation_resolver()
            config = resolver.resolve(service_config)
        except Exception:
            config = service_config

        if self._secret_resolver:
            try:
                config = self._secret_resolver.resolve_in_object(config, service_name)
            except Exception:
                pass

        return config

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)

        config = self._load_config()

        if hasattr(config, name):
            service_config = getattr(config, name)
            return self._process(service_config, name)

        available = [attr for attr in dir(config) if not attr.startswith("_")]
        raise AttributeError(
            f"Configuration '{name}' not found. Available: {', '.join(sorted(available))}"
        )


def create_config(
    environments: Optional[Dict[str, BaseStackConfig]] = None,
    default_environment: str = "develop",
    environment_variable: str = "PYPUWA_ENVIRONMENT",
) -> ConfigResolver:
    """
    Create a ConfigResolver instance.

    Args:
        environments: Dict mapping environment names to their config objects.
        default_environment: Fallback environment if detection fails.
        environment_variable: Env var name to check for environment override.

    Returns:
        A ConfigResolver with dot-notation access to the resolved config.

    Example:
        from pypuwa import create_config

        config = create_config(
            environments={
                "staging": staging_config,
                "production": production_config,
            }
        )
    """
    return ConfigResolver(
        environments=environments,
        default_environment=default_environment,
        environment_variable=environment_variable,
    )
