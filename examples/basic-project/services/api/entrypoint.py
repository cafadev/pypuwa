"""API service deployment — orchestrates database + container app."""

from typing import Any, Dict

from components.database import PostgresDatabase
from components.container_app import ContainerApp


def deploy_api(config) -> Dict[str, Any]:
    """
    Deploy the API service.

    Demonstrates:
    - Accessing nested config with dot notation
    - Database creation from BaseDatabaseConfig
    - Container app with auto-generated env vars
    - Cross-service secret resolution (DATABASE_PASSWORD)
    """
    api_config = config.services.api
    infra_config = config.infrastructure

    # 1. Create the database
    db = PostgresDatabase(
        config=api_config.DATABASE,
        resource_group_name=f"{infra_config.RESOURCE_GROUP_PREFIX}-rg",
        location=infra_config.LOCATION,
    )

    # 2. Create the container app
    # env_dict_with_outputs() automatically:
    #   - Excludes CPU, MEMORY (in _NON_ENV_FIELDS)
    #   - Resolves secrets as Pulumi Outputs
    #   - Resolves interpolations like ${services.api.database.name}
    app = ContainerApp(
        config=api_config.APP_RUNNER,
        resource_group_name=f"{infra_config.RESOURCE_GROUP_PREFIX}-rg",
        environment_id="placeholder-env-id",
        container_image="myregistry.azurecr.io/api:latest",
    )

    return {
        "url": app.url,
        "database_host": db.host,
    }
