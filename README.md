# pypuwa

**Python Pulumi Wrapper** — Dataclass-based configuration framework for Pulumi infrastructure as code.

Define your infrastructure config in Python dataclasses. Get interpolation, secret management, environment variable generation, lifecycle hooks, and a deploy CLI for free.

## Install

```bash
pip install pypuwa
```

## Quick Start

```python
# config/base/services/api.py
from dataclasses import dataclass, field
from typing import FrozenSet
from pypuwa import BaseDatabaseConfig, BaseComputeConfig, Secret, secret


@dataclass(kw_only=True)
class MyDatabaseConfig(BaseDatabaseConfig):
    INSTANCE_ID: str = "{stack}-my-api-db"
    NAME: str = "my_api"
    USERNAME: str = "api_user"


@dataclass(kw_only=True)
class MyAppConfig(BaseComputeConfig):
    SERVICE_NAME: str = "{stack}-my-api"
    CPU: str = "2 vCPU"
    MEMORY: str = "4 GB"

    DEBUG: str = "False"
    DATABASE_NAME: str = "${services.database.NAME}"
    API_SECRET: Secret = secret()

    _NON_ENV_FIELDS: FrozenSet[str] = frozenset(["CPU", "MEMORY"])
```

```python
# config/environments/staging.py
from pypuwa import BaseStackConfig, ProviderConfig

staging_config = MyStackConfig(
    providers=ProviderConfig(aws={"region": "us-east-1"}),
)
```

```python
# pypuwaconf.py
from config.environments.staging import staging_config
from config.environments.production import production_config

PROJECT_NAME = "my-infra"

ENVIRONMENTS = {
    "staging": staging_config,
    "production": production_config,
}
```

Then deploy:

```bash
pypuwa deploy staging
```

## pypuwaconf.py

Every project has a `pypuwaconf.py` at the root. This is the entry point for the CLI.

```python
# pypuwaconf.py
import os
import subprocess
from config.environments.staging import staging_config
from config.environments.production import production_config

PROJECT_NAME = "my-infra"          # Pulumi config prefix
RUNNER = "uv run pulumi"           # Command to run Pulumi (optional, defaults to "pulumi")

ENVIRONMENTS = {
    "staging": staging_config,
    "production": production_config,
}


def _ensure_azure_tenant(environment: str) -> bool:
    result = subprocess.run(
        ["az", "account", "show", "--query", "tenantId", "-o", "tsv"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("ERROR: Run 'az login' first")
        return False  # Aborts pipeline
    os.environ["AZURE_TENANT_ID"] = result.stdout.strip()
    return True


def _confirm_production(environment: str) -> bool:
    if environment == "production":
        resp = input("Deploy to PRODUCTION? Type 'yes': ")
        return resp == "yes"
    return True


HOOKS = {
    "pre_deploy": _ensure_azure_tenant,
    "pre_deploy": _confirm_production,  # last one wins per key
}
```

## CLI

```bash
# Full deploy: hooks → sync → secrets → pulumi up
pypuwa deploy staging

# Preview only (sync + show changes, no deploy)
pypuwa preview production

# Sync config to Pulumi YAML without deploying
pypuwa sync staging

# Options (override pypuwaconf.py values)
pypuwa deploy production --backup
pypuwa deploy staging --dry-run
pypuwa deploy staging --runner "uv run pulumi"
pypuwa deploy staging --project-name my-infra
```

### What `pypuwa deploy` does

```
pre_sync → [sync config to YAML] → post_sync → pre_secrets → [detect & set secrets] → post_secrets → pre_deploy → [pulumi up] → post_deploy
```

1. **Sync** — Generates `Pulumi.<env>.yaml` from Python config, preserving existing encrypted secrets
2. **Secrets** — Detects new `secret()` fields and prompts with arrow-key selection (all pre-selected)
3. **Deploy** — Runs `pulumi up` on the selected stack

### Lifecycle Hooks

Six hooks available: `pre_sync`, `post_sync`, `pre_secrets`, `post_secrets`, `pre_deploy`, `post_deploy`.

Each hook receives the environment name and can:
- Return `True` or `None` to continue
- Return `False` to abort the pipeline
- Raise an exception to abort with error

### Interactive Secret Management

```
? Select secrets to set now (space to toggle, enter to confirm):
  ❯ ◉ services.api.database.PASSWORD
    ◉ services.api.app_runner.DJANGO_SECRET_KEY
    ◉ services.redis.AUTH_TOKEN
```

All new secrets are pre-selected. Hit `enter` to set all, or `space` to deselect. Values entered with hidden input.

## Features

### Interpolation

```python
SERVICE_NAME: str = "{stack}-my-service"        # -> "staging-my-service"
DB_NAME: str = "${services.database.NAME}"      # -> resolved from config tree
```

### Secrets

```python
PASSWORD: Secret = secret()                     # Auto-inferred from field name
API_KEY: Secret = secret("EXTERNAL_API_KEY")    # Explicit key
REDIS_PASS: Secret = secret("${services.redis.AUTH_TOKEN}")  # Cross-service
```

### Environment Variables

```python
@dataclass(kw_only=True)
class MyConfig(BaseComputeConfig):
    DEBUG: str = "True"
    DATABASE_URL: str = "postgres://..."
    CPU: str = "2 vCPU"                         # Infrastructure, excluded from env

    _NON_ENV_FIELDS: FrozenSet[str] = frozenset(["CPU", "MEMORY"])

config = MyConfig(SERVICE_NAME="api")
env_vars = config.env_dict()
# {"SERVICE_NAME": "api", "DEBUG": "True", "DATABASE_URL": "postgres://..."}
```

### Base Components (cloud-agnostic)

| Class | Purpose |
|-------|---------|
| `BaseDatabaseConfig` | Any database (RDS, Azure PostgreSQL, Cloud SQL) |
| `BaseComputeConfig` | Any compute (App Runner, Container Apps, Cloud Run) |
| `BaseContainerRegistryConfig` | Any registry (ECR, ACR, GCR) |
| `BaseCacheConfig` | Any cache (ElastiCache, Azure Cache, Memorystore) |
| `BaseStorageConfig` | Any object storage (S3, Blob, GCS) |
| `BaseContainerTaskConfig` | Any container task (ECS, Cloud Run Jobs) |
| `BaseServiceConfig` | Base service with URL |
| `BaseRepositoryConfig` | Source code repository reference |

Extend these with cloud-specific fields in your project:

```python
@dataclass(kw_only=True)
class MyDatabaseConfig(BaseDatabaseConfig):
    INSTANCE_TYPE: str = "db.t3.micro"   # AWS-specific
    SKIP_FINAL_SNAPSHOT: bool = True     # AWS-specific
```

## Project Structure

```
my-infra/
├── pypuwaconf.py                   # Project config (environments, hooks, runner)
├── __main__.py                     # Pulumi entry point
├── Pulumi.yaml                     # Pulumi project definition
├── Pulumi.staging.yaml             # Generated (secrets encrypted here)
├── Pulumi.production.yaml          # Generated
├── config/
│   ├── base/
│   │   ├── stack.py                # MyStackConfig(BaseStackConfig)
│   │   └── services/
│   │       ├── api.py              # Database + Compute configs
│   │       ├── worker.py           # Worker config
│   │       └── redis.py            # Cache config
│   └── environments/
│       ├── staging.py              # staging_config = MyStackConfig(...)
│       └── production.py           # production_config = MyStackConfig(...)
├── components/                     # Your cloud-specific Pulumi wrappers
│   ├── database.py
│   ├── container_app.py
│   └── redis.py
└── services/                       # Deployment orchestration
    ├── api/entrypoint.py
    └── worker/entrypoint.py
```

See [examples/basic-project](examples/basic-project) for a complete working example.

## Requirements

- Python >= 3.11
- Pulumi >= 3.0

## License

MIT
