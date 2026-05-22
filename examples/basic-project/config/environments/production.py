"""Production environment — multi-AZ, larger instances, no public access."""

from pypuwa import ProviderConfig

from config.base.stack import MyStackConfig, MyInfraConfig
from config.base.services import MyServicesConfig
from config.base.services.api import MyAPIServiceConfig, MyAPIDatabaseConfig, MyAPIAppRunnerConfig
from config.base.services.worker import MyWorkerServiceConfig, MyWorkerAppRunnerConfig
from config.base.services.redis import MyRedisServiceConfig


production_config = MyStackConfig(
    providers=ProviderConfig(
        azure={
            "subscriptionId": "11111111-1111-1111-1111-111111111111",
            "tenantId": "11111111-1111-1111-1111-111111111111",
        },
    ),
    infrastructure=MyInfraConfig(
        LOCATION="eastus2",
        VNET_ADDRESS_SPACE=["10.2.0.0/16"],
        APP_SUBNET_PREFIX="10.2.0.0/23",
        DB_SUBNET_PREFIX="10.2.2.0/24",
        REGISTRY_SKU="Standard",
    ),
    services=MyServicesConfig(
        api=MyAPIServiceConfig(
            URL="https://api.myapp.com",
            DATABASE=MyAPIDatabaseConfig(
                MULTI_AZ=True,
                ALLOCATED_STORAGE=100,
                STORAGE_ENCRYPTION=True,
            ),
            APP_RUNNER=MyAPIAppRunnerConfig(
                CPU="4 vCPU",
                MEMORY="8 GB",
                DEBUG="False",
                ALLOWED_HOSTS="api.myapp.com",
            ),
        ),
        worker=MyWorkerServiceConfig(
            APP_RUNNER=MyWorkerAppRunnerConfig(
                CPU="2 vCPU",
                MEMORY="4 GB",
            ),
        ),
        redis=MyRedisServiceConfig(
            CLUSTER_ID="production-cache",
            NODE_TYPE="cache.r6g.large",
            SNAPSHOT_RETENTION_LIMIT=7,
        ),
    ),
)
