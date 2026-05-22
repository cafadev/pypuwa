"""
Environment variable generation mixin for dataclass-based configs.

Provides EnvironmentVariableMixin which automatically converts dataclass
fields to environment variable dictionaries, with support for excluding
infrastructure-only fields and resolving Pulumi Output objects.
"""

from dataclasses import fields, is_dataclass
from typing import Any, Dict, FrozenSet, Union


class EnvironmentVariableMixin:
    """
    Mixin that converts dataclass fields to environment variable dicts.

    Usage:
        @dataclass(kw_only=True)
        class MyConfig(EnvironmentVariableMixin):
            DEBUG: str = "False"
            DATABASE_URL: str = "postgres://..."
            CPU: str = "1 vCPU"  # Infrastructure setting

            _NON_ENV_FIELDS: FrozenSet[str] = frozenset(["CPU"])

        config = MyConfig()
        env_vars = config.env_dict()  # {"DEBUG": "False", "DATABASE_URL": "postgres://..."}
    """

    _NON_ENV_FIELDS: FrozenSet[str] = frozenset()

    def env_dict(self) -> Dict[str, str]:
        """
        Convert fields to an environment variable dictionary.

        Excludes fields in _NON_ENV_FIELDS, private fields, None values,
        and Pulumi Output objects (use env_dict_with_outputs() for those).
        """
        if not is_dataclass(self):
            raise TypeError(
                "EnvironmentVariableMixin can only be used with dataclasses."
            )

        env_vars: Dict[str, str] = {}

        for field_obj in fields(self):
            field_name = field_obj.name

            if field_name in self._NON_ENV_FIELDS or field_name.startswith("_"):
                continue

            try:
                field_value = getattr(self, field_name)

                if field_value is None:
                    continue

                if hasattr(field_value, "__class__") and "pulumi" in str(type(field_value)).lower():
                    continue

                if isinstance(field_value, (str, int, float, bool)):
                    env_vars[field_name] = str(field_value)
                elif hasattr(field_value, "__str__"):
                    str_value = str(field_value)
                    if not str_value.startswith("<"):
                        env_vars[field_name] = str_value

            except (AttributeError, TypeError, ValueError):
                continue

        return env_vars

    def env_dict_with_outputs(self) -> Union[Dict[str, str], Any]:
        """
        Convert fields to env var dict, resolving Pulumi Output objects.

        Returns:
            Dict[str, str] if no Output objects are present.
            pulumi.Output[Dict[str, str]] if any fields contain Output objects.
        """
        if not is_dataclass(self):
            raise TypeError(
                "EnvironmentVariableMixin can only be used with dataclasses."
            )

        regular_env_vars: Dict[str, str] = {}
        output_env_vars: Dict[str, Any] = {}

        for field_obj in fields(self):
            field_name = field_obj.name

            if field_name in self._NON_ENV_FIELDS or field_name.startswith("_"):
                continue

            try:
                field_value = getattr(self, field_name)

                if field_value is None:
                    continue

                if hasattr(field_value, "__class__") and "pulumi" in str(type(field_value)).lower():
                    output_env_vars[field_name] = field_value
                    continue

                if isinstance(field_value, (str, int, float, bool)):
                    regular_env_vars[field_name] = str(field_value)
                elif hasattr(field_value, "__str__"):
                    str_value = str(field_value)
                    if not str_value.startswith("<"):
                        regular_env_vars[field_name] = str_value

            except (AttributeError, TypeError, ValueError):
                continue

        if not output_env_vars:
            return regular_env_vars

        try:
            import pulumi

            return pulumi.Output.all(**output_env_vars).apply(
                lambda resolved: {
                    **regular_env_vars,
                    **{k: str(v) for k, v in resolved.items()},
                }
            )
        except ImportError:
            return regular_env_vars
