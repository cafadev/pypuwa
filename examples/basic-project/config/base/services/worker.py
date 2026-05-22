"""Background worker service configuration (e.g., Celery)."""

from dataclasses import dataclass, field
from typing import FrozenSet

from pypuwa import BaseComputeConfig, Secret, secret


@dataclass(kw_only=True)
class MyWorkerAppRunnerConfig(BaseComputeConfig):
    SERVICE_NAME: str = "{stack}-worker"
    CPU: str = "0.5 vCPU"
    MEMORY: str = "1 GB"

    # Reuses the same database and redis as the API
    DATABASE_NAME: str = "${services.api.database.name}"
    DATABASE_PASSWORD: Secret = secret("${services.api.database.password}")
    REDIS_PORT: str = "${services.redis.port}"
    CELERY_BROKER_URL: str = "redis://redis:{stack}-cache:${services.redis.port}/0"

    _NON_ENV_FIELDS: FrozenSet[str] = frozenset(["CPU", "MEMORY"])


@dataclass(kw_only=True)
class MyWorkerServiceConfig:
    """Top-level worker service config."""
    APP_RUNNER: MyWorkerAppRunnerConfig = field(default_factory=MyWorkerAppRunnerConfig)
