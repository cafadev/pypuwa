"""Root stack configuration that composes infrastructure + services."""

from dataclasses import dataclass, field
from typing import List, Optional

from pypuwa import BaseStackConfig, ProviderConfig

from config.base.services import MyServicesConfig


@dataclass(kw_only=True)
class MyInfraConfig:
    """Infrastructure-level settings (networking, registry, etc.)."""
    LOCATION: str = "eastus2"
    RESOURCE_GROUP_PREFIX: str = "{stack}"
    VNET_ADDRESS_SPACE: List[str] = field(default_factory=lambda: ["10.0.0.0/16"])
    APP_SUBNET_PREFIX: str = "10.0.0.0/23"
    DB_SUBNET_PREFIX: str = "10.0.2.0/24"
    REGISTRY_SKU: str = "Basic"


@dataclass(kw_only=True)
class MyStackConfig(BaseStackConfig):
    """Complete stack config with infrastructure + services."""
    infrastructure: MyInfraConfig = field(default_factory=MyInfraConfig)
    services: MyServicesConfig = field(default_factory=MyServicesConfig)
