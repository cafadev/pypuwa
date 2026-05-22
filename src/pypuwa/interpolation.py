"""
Interpolation resolution for configuration values.

Handles two patterns:
- Simple: {stack} -> replaced with the current stack name
- Complex: ${services.my_api.DATABASE.PASSWORD} -> resolved from config tree
"""

import copy
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional


class InterpolationResolver:
    """
    Resolves interpolation patterns in configuration values.

    Supports:
        - {stack} / {stack_name} -> current Pulumi stack name
        - {environment_type} -> detected environment
        - ${path.to.value} -> resolved from flattened config tree
    """

    def __init__(
        self,
        config_data: Any,
        stack_name: Optional[str] = None,
        environment_type: Optional[str] = None,
    ):
        self.config_data = config_data
        self.stack_name = stack_name or self._detect_stack_name()
        self.environment_type = environment_type or "unknown"
        self._context = self._build_context()

    def _detect_stack_name(self) -> str:
        """Detect current Pulumi stack name."""
        try:
            import pulumi
            stack_name = pulumi.get_stack()
            if stack_name and stack_name != "stack":
                return stack_name
        except Exception:
            pass

        env_stack = os.environ.get("PULUMI_STACK")
        if env_stack:
            return env_stack

        return "unknown"

    def _build_context(self) -> Dict[str, Any]:
        """Build the interpolation context from config data."""
        context: Dict[str, Any] = {
            "stack_name": self.stack_name,
            "stack": self.stack_name,
            "environment_type": self.environment_type,
            "timestamp": datetime.now().strftime("%Y%m%d-%H%M%S"),
        }

        if hasattr(self.config_data, "__dict__"):
            flattened = self._flatten(self.config_data.__dict__)
            context.update(flattened)

        return context

    def _flatten(self, obj: Any, prefix: str = "") -> Dict[str, Any]:
        """Flatten nested config into dot-notation paths."""
        result: Dict[str, Any] = {}

        if hasattr(obj, "__dict__"):
            items = obj.__dict__.items()
        elif isinstance(obj, dict):
            items = obj.items()
        else:
            return result

        for key, value in items:
            if key.startswith("_"):
                continue

            key_lower = key.lower()
            current_path = f"{prefix}.{key_lower}" if prefix else key_lower

            if value is not None and (hasattr(value, "__dict__") or isinstance(value, dict)):
                result.update(self._flatten(value, current_path))
            else:
                result[current_path] = value

        return result

    def resolve(self, obj: Any) -> Any:
        """Recursively resolve all interpolations in a config object."""
        if hasattr(obj, "__dict__"):
            resolved = copy.deepcopy(obj)
            for attr_name, attr_value in resolved.__dict__.items():
                if isinstance(attr_value, str):
                    resolved.__dict__[attr_name] = self.resolve_string(attr_value)
                elif hasattr(attr_value, "__dict__"):
                    resolved.__dict__[attr_name] = self.resolve(attr_value)
            return resolved
        return obj

    def resolve_string(self, value: str) -> str:
        """Resolve interpolation patterns in a single string."""
        if not isinstance(value, str):
            return value

        def replace_complex(match: re.Match[str]) -> str:
            path = match.group(1)
            resolved = self._resolve_path(path)
            return str(resolved) if resolved is not None else match.group(0)

        value = re.sub(r"\$\{([^}]+)\}", replace_complex, value)

        def replace_simple(match: re.Match[str]) -> str:
            key = match.group(1)
            if key in self._context:
                return str(self._context[key])
            return match.group(0)

        value = re.sub(r"\{([^}]+)\}", replace_simple, value)

        return value

    def _resolve_path(self, path: str) -> Any:
        """Resolve a dot-notation path against the context."""
        if path in self._context:
            return self._context[path]

        path_lower = path.lower()
        if path_lower in self._context:
            return self._context[path_lower]

        parts = path_lower.split(".")
        current: Any = self._context

        try:
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            return current
        except (KeyError, TypeError):
            return None
