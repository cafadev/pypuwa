"""
Cloud-agnostic base component dataclasses.

These provide common fields for infrastructure resources without
tying you to any specific cloud provider. Extend them with your
cloud-specific fields in your project.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional

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
class BaseComputeConfig(EnvironmentVariableMixin):
    """
    Generic compute/application configuration.

    Covers any containerized or serverless compute: AWS App Runner,
    Azure Container Apps, GCP Cloud Run, ECS Fargate, etc.

    Fields in _NON_ENV_FIELDS are excluded from env_dict() output,
    since they're infrastructure settings, not application env vars.
    """
    SERVICE_NAME: str
    CPU: str = "1 vCPU"
    MEMORY: str = "2 GB"
    APP_PORT: Optional[str] = None

    _NON_ENV_FIELDS: FrozenSet[str] = frozenset(["CPU", "MEMORY"])


@dataclass(kw_only=True)
class BaseContainerRegistryConfig:
    """Generic container registry configuration (ECR, ACR, GCR, etc.)."""
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
class BaseCacheConfig:
    """Generic cache configuration (ElastiCache, Azure Cache for Redis, Memorystore, etc.)."""
    CLUSTER_ID: str
    ENGINE_VERSION: str = "7.0"
    PORT: int = 6379
    SNAPSHOT_RETENTION_LIMIT: int = 0
    MAINTENANCE_WINDOW: str = "sun:05:00-sun:06:00"
    AUTH_TOKEN: Optional[Secret] = None


@dataclass(kw_only=True)
class BaseStorageConfig:
    """Generic object storage configuration (S3, Azure Blob, GCS, etc.)."""
    BUCKET_NAME: str
    VERSIONING: bool = False
    ENCRYPTION: bool = True
    PUBLIC_ACCESS_BLOCK: bool = True
    FORCE_DESTROY: bool = False
    LIFECYCLE_RULES: Optional[List[Dict[str, Any]]] = None
    CORS_RULES: Optional[List[Dict[str, Any]]] = None


@dataclass(kw_only=True)
class BaseContainerTaskConfig:
    """Generic container task/job configuration (ECS tasks, Cloud Run Jobs, Azure Container Instances, etc.)."""
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
