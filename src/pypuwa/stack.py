"""
Root stack configuration classes.

BaseStackConfig is the top-level config object that users extend
with their own cloud-specific and service-specific sections.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(kw_only=True)
class ProviderConfig:
    """
    Provider-level configuration mapping to Pulumi provider settings.

    Example:
        ProviderConfig(
            aws={"region": "us-east-1", "profile": "default"},
            azure={"subscriptionId": "...", "tenantId": "..."},
        )
    """
    aws: Dict[str, Any] = field(default_factory=dict)
    azure: Dict[str, Any] = field(default_factory=dict)
    azure_native: Dict[str, Any] = field(default_factory=dict)
    gcp: Dict[str, Any] = field(default_factory=dict)


@dataclass(kw_only=True)
class BaseStackConfig:
    """
    Root configuration that users extend with their own structure.

    Usage:
        @dataclass(kw_only=True)
        class MyStackConfig(BaseStackConfig):
            services: MyServicesConfig = field(default_factory=MyServicesConfig)
            infrastructure: MyInfraConfig = field(default_factory=MyInfraConfig)

        production_config = MyStackConfig(
            providers=ProviderConfig(aws={"region": "us-east-1"}),
            services=MyServicesConfig(...),
        )
    """
    providers: Optional[ProviderConfig] = None
