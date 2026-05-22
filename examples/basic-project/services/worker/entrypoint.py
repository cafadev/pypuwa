"""Worker service deployment — shares database with API."""

from components.container_app import ContainerApp


def deploy_worker(config):
    """
    Deploy the background worker.

    Demonstrates cross-service config sharing:
    - Worker's DATABASE_PASSWORD references ${services.api.database.password}
    - Resolved automatically by pypuwa's interpolation + secret system
    """
    worker_config = config.services.worker
    infra_config = config.infrastructure

    app = ContainerApp(
        config=worker_config.APP_RUNNER,
        resource_group_name=f"{infra_config.RESOURCE_GROUP_PREFIX}-rg",
        environment_id="placeholder-env-id",
        container_image="myregistry.azurecr.io/worker:latest",
    )

    return {"worker_app": app}
