"""Azure Cache for Redis wrapper."""

import pulumi
import pulumi_azure_native as azure_native

from pypuwa import BaseCacheConfig


class RedisCache:
    """Creates an Azure Cache for Redis from config."""

    def __init__(self, config: BaseCacheConfig, resource_group_name: str, location: str):
        self.config = config

        self.cache = azure_native.cache.Redis(
            config.CLUSTER_ID,
            resource_group_name=resource_group_name,
            location=location,
            sku=azure_native.cache.SkuArgs(
                name="Basic",
                family="C",
                capacity=0,
            ),
            redis_version=config.ENGINE_VERSION,
            enable_non_ssl_port=False,
            minimum_tls_version="1.2",
        )

    @property
    def host(self) -> pulumi.Output[str]:
        return self.cache.host_name

    @property
    def port(self) -> pulumi.Output[int]:
        return self.cache.ssl_port
