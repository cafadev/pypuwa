"""
Azure PostgreSQL Flexible Server wrapper.

This is YOUR cloud-specific code — pypuwa provides the config dataclass,
you write the Pulumi resource creation.
"""

import pulumi
import pulumi_azure_native as azure_native

from pypuwa import BaseDatabaseConfig


class PostgresDatabase:
    """Creates an Azure PostgreSQL Flexible Server from config."""

    def __init__(self, config: BaseDatabaseConfig, resource_group_name: str, location: str):
        self.config = config

        self.server = azure_native.dbforpostgresql.Server(
            config.INSTANCE_ID,
            resource_group_name=resource_group_name,
            location=location,
            version=azure_native.dbforpostgresql.ServerVersion(f"_{config.ENGINE_VERSION}"),
            storage=azure_native.dbforpostgresql.StorageArgs(
                storage_size_gb=config.ALLOCATED_STORAGE,
            ),
            administrator_login=config.USERNAME,
            administrator_login_password=config.PASSWORD,
            high_availability=azure_native.dbforpostgresql.HighAvailabilityArgs(
                mode="ZoneRedundant" if config.MULTI_AZ else "Disabled",
            ),
        )

        self.database = azure_native.dbforpostgresql.Database(
            f"{config.INSTANCE_ID}-db",
            resource_group_name=resource_group_name,
            server_name=self.server.name,
            database_name=config.NAME,
        )

    @property
    def host(self) -> pulumi.Output[str]:
        return self.server.fully_qualified_domain_name

    @property
    def connection_string(self) -> pulumi.Output[str]:
        return pulumi.Output.all(self.host, self.config.PASSWORD).apply(
            lambda args: f"postgresql://{self.config.USERNAME}:{args[1]}@{args[0]}:{self.config.PORT}/{self.config.NAME}"
        )
