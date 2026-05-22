"""Redis cache service configuration."""

from dataclasses import dataclass

from pypuwa import BaseCacheConfig, Secret, secret


@dataclass(kw_only=True)
class MyRedisServiceConfig(BaseCacheConfig):
    CLUSTER_ID: str = "{stack}-cache"
    NODE_TYPE: str = "cache.t3.micro"
    PORT: int = 6379
    AUTH_TOKEN: Secret = secret()
