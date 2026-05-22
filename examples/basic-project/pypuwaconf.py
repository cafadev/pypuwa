"""
pypuwa project configuration.

This file is the entry point for the pypuwa CLI.
It declares environments, project settings, and lifecycle hooks.
"""

import os
import subprocess

from config.environments.staging import staging_config
from config.environments.production import production_config

PROJECT_NAME = "my-infra"
RUNNER = "pulumi"

ENVIRONMENTS = {
    "staging": staging_config,
    "production": production_config,
}


def _ensure_azure_tenant(environment: str) -> bool:
    """Set AZURE_TENANT_ID from Azure CLI before deploying."""
    if os.environ.get("AZURE_TENANT_ID"):
        return True
    result = subprocess.run(
        ["az", "account", "show", "--query", "tenantId", "-o", "tsv"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("ERROR: Run 'az login' first")
        return False
    os.environ["AZURE_TENANT_ID"] = result.stdout.strip()
    return True


def _confirm_production(environment: str) -> bool:
    """Gate production deploys behind confirmation."""
    if environment == "production":
        resp = input("Deploy to PRODUCTION? Type 'yes' to confirm: ")
        return resp == "yes"
    return True


HOOKS = {
    "pre_deploy": _ensure_azure_tenant,
}
