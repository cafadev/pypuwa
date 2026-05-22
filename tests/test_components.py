"""Tests for base component dataclasses."""

from pypuwa.components import (
    BaseAppRunnerConfig,
    BaseDatabaseConfig,
    BaseECRConfig,
    BaseRedisConfig,
    BaseStorageConfig,
)
from pypuwa.secrets import is_secret


class TestBaseDatabaseConfig:
    def test_defaults(self):
        db = BaseDatabaseConfig(
            NAME="my_db",
            USERNAME="admin",
            INSTANCE_ID="staging-my-db",
        )
        assert db.ENGINE == "postgres"
        assert db.PORT == "5432"
        assert db.MULTI_AZ is False
        assert db.STORAGE_ENCRYPTION is True
        assert is_secret(db.PASSWORD)

    def test_override(self):
        db = BaseDatabaseConfig(
            NAME="prod_db",
            USERNAME="prod_user",
            INSTANCE_ID="prod-db",
            ENGINE_VERSION="16",
            MULTI_AZ=True,
            ALLOCATED_STORAGE=100,
        )
        assert db.ENGINE_VERSION == "16"
        assert db.MULTI_AZ is True
        assert db.ALLOCATED_STORAGE == 100


class TestBaseAppRunnerConfig:
    def test_non_env_fields_excluded(self):
        app = BaseAppRunnerConfig(SERVICE_NAME="my-service")
        env = app.env_dict()

        assert "CPU" not in env
        assert "MEMORY" not in env
        assert "SERVICE_NAME" in env

    def test_custom_exclusions(self):
        from dataclasses import dataclass
        from typing import FrozenSet

        @dataclass(kw_only=True)
        class MyApp(BaseAppRunnerConfig):
            DEBUG: str = "True"
            INTERNAL_PORT: str = "9000"
            _NON_ENV_FIELDS: FrozenSet[str] = frozenset(["CPU", "MEMORY", "INTERNAL_PORT"])

        app = MyApp(SERVICE_NAME="test")
        env = app.env_dict()

        assert "DEBUG" in env
        assert "INTERNAL_PORT" not in env


class TestBaseECRConfig:
    def test_defaults(self):
        ecr = BaseECRConfig(REPOSITORY_NAME="my-repo", SERVICE_NAME="my-service")
        assert ecr.REMOTE_IMAGE_TAG == "latest"


class TestBaseRedisConfig:
    def test_defaults(self):
        redis = BaseRedisConfig(CLUSTER_ID="my-cache")
        assert redis.PORT == 6379
        assert redis.ENGINE_VERSION == "7.0"
        assert redis.AUTH_TOKEN is None


class TestBaseStorageConfig:
    def test_defaults(self):
        storage = BaseStorageConfig(BUCKET_NAME="my-bucket")
        assert storage.ENCRYPTION is True
        assert storage.PUBLIC_ACCESS_BLOCK is True
        assert storage.VERSIONING is False
