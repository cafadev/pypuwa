"""Tests for the ConfigurationManager."""

from dataclasses import dataclass, field
from typing import Optional

from pypuwa.components import BaseComputeConfig, BaseDatabaseConfig
from pypuwa.manager import ConfigurationManager
from pypuwa.secrets import Secret, secret
from pypuwa.stack import BaseStackConfig, ProviderConfig


@dataclass(kw_only=True)
class SampleDatabaseConfig(BaseDatabaseConfig):
    INSTANCE_ID: str = "{stack}-test-db"
    NAME: str = "test_db"
    USERNAME: str = "test_user"


@dataclass(kw_only=True)
class SampleServicesConfig:
    database: SampleDatabaseConfig = field(default_factory=SampleDatabaseConfig)


@dataclass(kw_only=True)
class SampleStackConfig(BaseStackConfig):
    services: SampleServicesConfig = field(default_factory=SampleServicesConfig)


staging_config = SampleStackConfig(
    providers=ProviderConfig(aws={"region": "us-east-1"}),
)

production_config = SampleStackConfig(
    providers=ProviderConfig(aws={"region": "us-west-2"}),
    services=SampleServicesConfig(
        database=SampleDatabaseConfig(
            INSTANCE_ID="{stack}-prod-db",
            NAME="prod_db",
            USERNAME="prod_user",
            MULTI_AZ=True,
        )
    ),
)


class TestConfigurationManager:
    def test_list_environments(self):
        manager = ConfigurationManager(
            environments={"staging": staging_config, "production": production_config}
        )
        envs = manager.list_environments()
        assert "staging" in envs
        assert "production" in envs

    def test_generate_stack_config(self):
        manager = ConfigurationManager(
            environments={"staging": staging_config}
        )
        config = manager.generate_stack_config("staging", "staging")

        assert config["services"]["database"]["NAME"] == "test_db"
        assert config["services"]["database"]["INSTANCE_ID"] == "staging-test-db"

    def test_production_overrides(self):
        manager = ConfigurationManager(
            environments={"production": production_config}
        )
        config = manager.generate_stack_config("production", "production")

        assert config["services"]["database"]["NAME"] == "prod_db"
        assert config["services"]["database"]["MULTI_AZ"] is True
        assert config["services"]["database"]["INSTANCE_ID"] == "production-prod-db"

    def test_invalid_environment_raises(self):
        manager = ConfigurationManager(environments={"staging": staging_config})
        try:
            manager.generate_stack_config("prod", "production")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "production" in str(e)

    def test_to_pulumi_yaml(self):
        manager = ConfigurationManager(
            environments={"staging": staging_config}
        )
        yaml_config = manager.to_pulumi_yaml("staging", "staging")

        assert "config" in yaml_config
        db_config = yaml_config["config"]["services"]["database"]
        assert db_config["NAME"] == "test_db"
        assert db_config["PASSWORD"] == {"secure": "PLACEHOLDER_SECRET"}

    def test_validate(self):
        manager = ConfigurationManager(
            environments={"staging": staging_config}
        )
        issues = manager.validate("staging")
        assert issues == []

    def test_validate_unknown_env(self):
        manager = ConfigurationManager(environments={})
        issues = manager.validate("nonexistent")
        assert len(issues) == 1

    def test_overrides(self):
        manager = ConfigurationManager(
            environments={"staging": staging_config}
        )
        config = manager.generate_stack_config(
            "staging", "staging", overrides={"services": {"database": {"PORT": "5433"}}}
        )
        assert config["services"]["database"]["PORT"] == "5433"
