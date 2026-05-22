"""Staging environment — small instances, single-AZ, public access for debugging."""

from pypuwa import ProviderConfig

from config.base.stack import MyStackConfig, MyInfraConfig
from config.base.services import MyServicesConfig
from config.base.services.api import MyAPIServiceConfig, MyAPIDatabaseConfig, MyAPIAppRunnerConfig
from config.base.services.worker import MyWorkerServiceConfig, MyWorkerAppRunnerConfig
from config.base.services.redis import MyRedisServiceConfig


staging_config = MyStackConfig(
    providers=ProviderConfig(
        azure={
            "subscriptionId": "00000000-0000-0000-0000-000000000000",
            "tenantId": "00000000-0000-0000-0000-000000000000",
        },
    ),
    infrastructure=MyInfraConfig(
        LOCATION="eastus2",
        VNET_ADDRESS_SPACE=["10.1.0.0/16"],
        APP_SUBNET_PREFIX="10.1.0.0/23",
        DB_SUBNET_PREFIX="10.1.2.0/24",
    ),
    services=MyServicesConfig(
        api=MyAPIServiceConfig(
            URL="https://api.staging.myapp.com",
            DATABASE=MyAPIDatabaseConfig(
                PUBLIC_ACCESS=True,
            ),
            APP_RUNNER=MyAPIAppRunnerConfig(
                DEBUG="True",
                ALLOWED_HOSTS="api.staging.myapp.com,localhost",
            ),
        ),
        worker=MyWorkerServiceConfig(
            APP_RUNNER=MyWorkerAppRunnerConfig(
                CPU="0.25 vCPU",
                MEMORY="512 MB",
            ),
        ),
        redis=MyRedisServiceConfig(
            CLUSTER_ID="staging-cache",
        ),
    ),
)
