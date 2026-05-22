"""Pulumi entry point — deploys services based on current stack environment."""

import pulumi
from pypuwa import create_config

from config.environments.staging import staging_config
from config.environments.production import production_config
from services.api.entrypoint import deploy_api
from services.worker.entrypoint import deploy_worker

config = create_config(
    environments={"staging": staging_config, "production": production_config}
)

outputs = {}

if config.services.api is not None:
    api_result = deploy_api(config)
    outputs["api_url"] = api_result.get("url")

if config.services.worker is not None:
    deploy_worker(config)

for key, value in outputs.items():
    if value is not None:
        pulumi.export(key, value)
