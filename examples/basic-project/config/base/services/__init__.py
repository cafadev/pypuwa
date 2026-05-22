"""Service configurations — each service gets its own module."""

from dataclasses import dataclass, field
from typing import Optional

from config.base.services.api import MyAPIServiceConfig
from config.base.services.worker import MyWorkerServiceConfig
from config.base.services.redis import MyRedisServiceConfig


@dataclass(kw_only=True)
class MyServicesConfig:
    """All services available in this stack."""
    api: Optional[MyAPIServiceConfig] = field(default_factory=MyAPIServiceConfig)
    worker: Optional[MyWorkerServiceConfig] = field(default_factory=MyWorkerServiceConfig)
    redis: Optional[MyRedisServiceConfig] = field(default_factory=MyRedisServiceConfig)
