"""
Azure Container App wrapper.

Demonstrates how env_dict_with_outputs() feeds directly into container config.
"""

import pulumi
import pulumi_azure_native as azure_native

from pypuwa import BaseAppRunnerConfig


class ContainerApp:
    """Creates an Azure Container App from config."""

    def __init__(
        self,
        config: BaseAppRunnerConfig,
        resource_group_name: str,
        environment_id: str,
        container_image: str,
    ):
        self.config = config

        # env_dict_with_outputs() returns a dict or Output[dict]
        # that automatically excludes CPU, MEMORY, and other _NON_ENV_FIELDS
        env_vars = config.env_dict_with_outputs()

        def build_env_list(env_dict):
            return [
                azure_native.app.EnvironmentVarArgs(name=k, value=v)
                for k, v in env_dict.items()
            ]

        # Handle both plain dict and Output[dict]
        if isinstance(env_vars, dict):
            environment = build_env_list(env_vars)
        else:
            environment = env_vars.apply(build_env_list)

        self.app = azure_native.app.ContainerApp(
            config.SERVICE_NAME,
            resource_group_name=resource_group_name,
            managed_environment_id=environment_id,
            configuration=azure_native.app.ConfigurationArgs(
                ingress=azure_native.app.IngressArgs(
                    external=True,
                    target_port=int(config.APP_PORT) if config.APP_PORT else 8000,
                ),
            ),
            template=azure_native.app.TemplateArgs(
                containers=[
                    azure_native.app.ContainerArgs(
                        name=config.SERVICE_NAME,
                        image=container_image,
                        env=environment,
                        resources=azure_native.app.ContainerResourcesArgs(
                            cpu=float(config.CPU.replace(" vCPU", "")),
                            memory=config.MEMORY.replace(" GB", "Gi"),
                        ),
                    ),
                ],
            ),
        )

    @property
    def url(self) -> pulumi.Output[str]:
        return self.app.latest_revision_fqdn.apply(lambda fqdn: f"https://{fqdn}")
