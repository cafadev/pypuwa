"""Tests for the EnvironmentVariableMixin."""

from dataclasses import dataclass
from typing import FrozenSet

from pypuwa.env import EnvironmentVariableMixin


@dataclass(kw_only=True)
class SimpleConfig(EnvironmentVariableMixin):
    DEBUG: str = "False"
    DATABASE_URL: str = "postgres://localhost/db"
    PORT: str = "8000"


@dataclass(kw_only=True)
class ConfigWithExclusions(EnvironmentVariableMixin):
    DEBUG: str = "True"
    APP_PORT: str = "9000"
    CPU: str = "2 vCPU"
    MEMORY: str = "4 GB"

    _NON_ENV_FIELDS: FrozenSet[str] = frozenset(["CPU", "MEMORY"])


@dataclass(kw_only=True)
class ConfigWithNone(EnvironmentVariableMixin):
    REQUIRED: str = "value"
    OPTIONAL: str = None


class TestEnvironmentVariableMixin:
    def test_basic_env_dict(self):
        config = SimpleConfig()
        env = config.env_dict()

        assert env == {
            "DEBUG": "False",
            "DATABASE_URL": "postgres://localhost/db",
            "PORT": "8000",
        }

    def test_exclusions(self):
        config = ConfigWithExclusions()
        env = config.env_dict()

        assert "DEBUG" in env
        assert "APP_PORT" in env
        assert "CPU" not in env
        assert "MEMORY" not in env

    def test_none_values_excluded(self):
        config = ConfigWithNone()
        env = config.env_dict()

        assert "REQUIRED" in env
        assert "OPTIONAL" not in env

    def test_bool_and_int_conversion(self):
        @dataclass(kw_only=True)
        class TypedConfig(EnvironmentVariableMixin):
            FLAG: bool = True
            COUNT: int = 5
            RATIO: float = 0.5

        config = TypedConfig()
        env = config.env_dict()

        assert env["FLAG"] == "True"
        assert env["COUNT"] == "5"
        assert env["RATIO"] == "0.5"

    def test_env_dict_with_outputs_no_pulumi(self):
        config = SimpleConfig()
        result = config.env_dict_with_outputs()

        assert isinstance(result, dict)
        assert result["DEBUG"] == "False"

    def test_not_a_dataclass_raises(self):
        class NotADataclass(EnvironmentVariableMixin):
            DEBUG = "True"

        obj = NotADataclass()
        try:
            obj.env_dict()
            assert False, "Should have raised TypeError"
        except TypeError:
            pass
