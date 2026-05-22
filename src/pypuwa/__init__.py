"""
pypuwa - Python Pulumi Wrapper

Dataclass-based configuration framework for Pulumi infrastructure as code.
Define your infrastructure config in Python dataclasses, get interpolation,
secret management, and environment variable generation for free.
"""

from pypuwa.secrets import Secret, secret
from pypuwa.env import EnvironmentVariableMixin
from pypuwa.components import (
    BaseDatabaseConfig,
    BaseComputeConfig,
    BaseContainerRegistryConfig,
    BaseRepositoryConfig,
    BaseCacheConfig,
    BaseServiceConfig,
    BaseStorageConfig,
    BaseContainerTaskConfig,
)
from pypuwa.stack import BaseStackConfig, ProviderConfig
from pypuwa.config import ConfigResolver, create_config
from pypuwa.interpolation import InterpolationResolver
from pypuwa.manager import ConfigurationManager

__version__ = "0.2.0"

__all__ = [
    "Secret",
    "secret",
    "EnvironmentVariableMixin",
    "BaseDatabaseConfig",
    "BaseComputeConfig",
    "BaseContainerRegistryConfig",
    "BaseRepositoryConfig",
    "BaseCacheConfig",
    "BaseServiceConfig",
    "BaseStorageConfig",
    "BaseContainerTaskConfig",
    "BaseStackConfig",
    "ProviderConfig",
    "ConfigResolver",
    "create_config",
    "InterpolationResolver",
    "ConfigurationManager",
]
