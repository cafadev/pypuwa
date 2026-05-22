"""
Cloud-agnostic base component dataclasses.

These provide common fields for infrastructure resources without
tying you to any specific cloud provider. Extend them with your
cloud-specific fields in your project.
"""

from dataclasses import dataclass, field
from typing import FrozenSet, List, Optional

from pypuwa.env import EnvironmentVariableMixin
from pypuwa.secrets import Secret, secret


@dataclass(kw_only=True)
class BaseServiceConfig:
    """Base service configuration."""
    URL: str


@dataclass(kw_only=True)
class BaseDatabaseConfig:
    """
    Generic database configuration.

    Extend with cloud-specific fields (e.g., INSTANCE_TYPE for RDS,
    SKU for Azure PostgreSQL Flexible Server).
    """
    NAME: str
    USERNAME: str
    INSTANCE_ID: str
    ENGINE: str = "postgres"
    ENGINE_VERSION: str = "17"
    PORT: str = "5432"
    ALLOCATED_STORAGE: int = 20
    MULTI_AZ: bool = False
    STORAGE_ENCRYPTION: bool = True
    PUBLIC_ACCESS: bool = False
    PASSWORD: Secret = secret()


@dataclass(kw_only=True)
class BaseAppRunnerConfig(EnvironmentVariableMixin):
    """
    Generic compute/application configuration.

    Fields in _NON_ENV_FIELDS are excluded from env_dict() output,
    since they're infrastructure settings, not application env vars.
    """
    SERVICE_NAME: str
    CPU: str = "1 vCPU"
    MEMORY: str = "2 GB"
    APP_PORT: Optional[str] = None

    _NON_ENV_FIELDS: FrozenSet[str] = frozenset(["CPU", "MEMORY"])


@dataclass(kw_only=True)
class BaseECRConfig:
    """Generic container registry configuration."""
    REPOSITORY_NAME: str
    SERVICE_NAME: str
    REMOTE_IMAGE_TAG: Optional[str] = "latest"


@dataclass(kw_only=True)
class BaseRepositoryConfig:
    """Generic source code repository reference."""
    URL: str
    BRANCH: str = "main"
    REPOSITORY_NAME: str


@dataclass(kw_only=True)
class BaseRedisConfig:
    """Generic Redis/cache configuration."""
    CLUSTER_ID: str
    NODE_TYPE: str = "cache.t3.micro"
    NUM_CACHE_NODES: int = 1
    ENGINE_VERSION: str = "7.0"
    PORT: int = 6379
    PARAMETER_GROUP_FAMILY: str = "redis7"
    SNAPSHOT_RETENTION_LIMIT: int = 0
    MAINTENANCE_WINDOW: str = "sun:05:00-sun:06:00"
    AUTH_TOKEN: Optional[Secret] = None


@dataclass(kw_only=True)
class BaseStorageConfig:
    """Generic object storage configuration."""
    BUCKET_NAME: str
    VERSIONING: bool = False
    ENCRYPTION: bool = True
    PUBLIC_ACCESS_BLOCK: bool = True
    FORCE_DESTROY: bool = False
    LIFECYCLE_RULES: Optional[List[dict]] = None
    CORS_RULES: Optional[List[dict]] = None


@dataclass(kw_only=True)
class BaseECSConfig:
    """Generic container orchestration task configuration."""
    CLUSTER_NAME: str
    SERVICE_NAME: str
    TASK_FAMILY: str
    CONTAINER_NAME: str
    COMMAND: List[str] = field(default_factory=list)
    CPU: str = "512"
    MEMORY: str = "1024"
    DESIRED_COUNT: int = 1
    ASSIGN_PUBLIC_IP: bool = False
    LOG_RETENTION_DAYS: int = 7
