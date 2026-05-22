"""API service configuration — database + app runner."""

from dataclasses import dataclass, field
from typing import FrozenSet

from pypuwa import BaseDatabaseConfig, BaseAppRunnerConfig, Secret, secret


@dataclass(kw_only=True)
class MyAPIDatabaseConfig(BaseDatabaseConfig):
    INSTANCE_ID: str = "{stack}-api-db"
    NAME: str = "my_api"
    USERNAME: str = "api_user"
    ENGINE_VERSION: str = "16"


@dataclass(kw_only=True)
class MyAPIAppRunnerConfig(BaseAppRunnerConfig):
    SERVICE_NAME: str = "{stack}-api"
    CPU: str = "1 vCPU"
    MEMORY: str = "2 GB"
    APP_PORT: str = "8000"

    # Application environment variables
    DEBUG: str = "False"
    ALLOWED_HOSTS: str = "{stack}-api.myapp.com"
    DATABASE_NAME: str = "${services.api.database.name}"
    DATABASE_PORT: str = "${services.api.database.port}"
    REDIS_PORT: str = "${services.redis.port}"

    # Secrets (resolved from Pulumi encrypted config at runtime)
    DJANGO_SECRET_KEY: Secret = secret()
    DATABASE_PASSWORD: Secret = secret("${services.api.database.password}")

    _NON_ENV_FIELDS: FrozenSet[str] = frozenset(["CPU", "MEMORY"])


@dataclass(kw_only=True)
class MyAPIServiceConfig:
    """Top-level API service config."""
    URL: str = "https://api.{stack}.myapp.com"
    DATABASE: MyAPIDatabaseConfig = field(default_factory=MyAPIDatabaseConfig)
    APP_RUNNER: MyAPIAppRunnerConfig = field(default_factory=MyAPIAppRunnerConfig)
