# pypuwa

**Python Pulumi Wrapper** — Dataclass-based configuration framework for Pulumi infrastructure as code.

Define your infrastructure config in Python dataclasses. Get interpolation, secret management, environment variable generation, and a deploy CLI for free.

## Install

```bash
pip install pypuwa
```

## Quick Start

```python
from dataclasses import dataclass, field
from typing import FrozenSet
from pypuwa import (
    BaseStackConfig,
    ProviderConfig,
    BaseDatabaseConfig,
    BaseAppRunnerConfig,
    Secret,
    secret,
    create_config,
)


# 1. Define your service configs
@dataclass(kw_only=True)
class MyDatabaseConfig(BaseDatabaseConfig):
    INSTANCE_ID: str = "{stack}-my-api-db"
    NAME: str = "my_api"
    USERNAME: str = "api_user"


@dataclass(kw_only=True)
class MyAppConfig(BaseAppRunnerConfig):
    SERVICE_NAME: str = "{stack}-my-api"
    CPU: str = "2 vCPU"
    MEMORY: str = "4 GB"

    # Application env vars
    DEBUG: str = "False"
    DATABASE_NAME: str = "${services.database.NAME}"
    API_SECRET: Secret = secret()

    _NON_ENV_FIELDS: FrozenSet[str] = frozenset(["CPU", "MEMORY"])


# 2. Compose into a stack config
@dataclass(kw_only=True)
class MyServicesConfig:
    database: MyDatabaseConfig = field(default_factory=MyDatabaseConfig)
    app: MyAppConfig = field(default_factory=MyAppConfig)


@dataclass(kw_only=True)
class MyStackConfig(BaseStackConfig):
    services: MyServicesConfig = field(default_factory=MyServicesConfig)


# 3. Define environments
staging_config = MyStackConfig(
    providers=ProviderConfig(aws={"region": "us-east-1"}),
)

production_config = MyStackConfig(
    providers=ProviderConfig(aws={"region": "us-west-2"}),
    services=MyServicesConfig(
        database=MyDatabaseConfig(MULTI_AZ=True, ALLOCATED_STORAGE=100),
        app=MyAppConfig(CPU="4 vCPU", MEMORY="8 GB"),
    ),
)

# 4. Create the config resolver (auto-detects environment from Pulumi stack)
config = create_config(
    environments={"staging": staging_config, "production": production_config}
)
```

## CLI

`pypuwa` includes a deploy orchestrator that syncs your Python config to Pulumi YAML, manages secrets interactively, and runs `pulumi up`.

```bash
# Full deploy: sync config → set new secrets → pulumi up
pypuwa deploy staging

# Preview only (sync + show changes, no deploy)
pypuwa preview production

# Sync config to Pulumi YAML without deploying
pypuwa sync staging

# With options
pypuwa deploy production --backup          # Backup existing YAML before sync
pypuwa deploy staging --dry-run            # Sync config, skip deploy
pypuwa deploy staging --runner "uv run pulumi"  # Custom Pulumi runner
pypuwa deploy staging --project-name my-infra   # Custom config prefix
```

### What `pypuwa deploy` does

1. **Sync** — Generates `Pulumi.<env>.yaml` from your Python config, preserving existing encrypted secrets
2. **New secrets** — Detects new `secret()` fields and prompts you to set values (arrow-key selection, all pre-selected)
3. **Existing secrets** — Offers to update existing secret values (arrow-key selection)
4. **Deploy** — Runs `pulumi up` on the selected stack

### Interactive secret management

New secrets are detected automatically and presented with arrow-key navigation:

```
? Select secrets to set now (space to toggle, enter to confirm):
  ❯ ◉ services.api.database.PASSWORD
    ◉ services.api.app_runner.DJANGO_SECRET_KEY
    ◉ services.redis.AUTH_TOKEN
```

All new secrets are pre-selected — just hit `enter` to set them all, or `space` to deselect ones you want to skip. Values are entered with hidden input.

## Features

### Interpolation

```python
SERVICE_NAME: str = "{stack}-my-service"        # -> "staging-my-service"
DB_NAME: str = "${services.database.NAME}"      # -> resolved from config tree
```

### Secrets

```python
# Auto-inferred from field name
PASSWORD: Secret = secret()                     # -> loaded from Pulumi encrypted config

# Explicit key
API_KEY: Secret = secret("EXTERNAL_API_KEY")

# Cross-service reference
REDIS_PASS: Secret = secret("${services.redis.AUTH_TOKEN}")
```

### Environment Variables

```python
@dataclass(kw_only=True)
class MyConfig(BaseAppRunnerConfig):
    DEBUG: str = "True"
    DATABASE_URL: str = "postgres://..."
    CPU: str = "2 vCPU"                         # Infrastructure, not an env var

    _NON_ENV_FIELDS: FrozenSet[str] = frozenset(["CPU", "MEMORY"])

config = MyConfig(SERVICE_NAME="api")
env_vars = config.env_dict()
# {"SERVICE_NAME": "api", "DEBUG": "True", "DATABASE_URL": "postgres://..."}
# CPU and MEMORY are excluded
```

### Configuration Manager

```python
from pypuwa import ConfigurationManager

manager = ConfigurationManager(
    environments={"staging": staging_config, "production": production_config}
)

# Generate resolved config
stack = manager.generate_stack_config("my-stack", "staging")

# Generate Pulumi YAML
yaml_config = manager.to_pulumi_yaml("my-stack", "production")

# Validate
issues = manager.validate("staging")
```

## Project Structure

A project using pypuwa looks like this:

```
my-infra/
├── __main__.py                     # Pulumi entry point
├── Pulumi.yaml                     # Pulumi project definition
├── Pulumi.staging.yaml             # Generated (secrets encrypted here)
├── Pulumi.production.yaml          # Generated
├── config/
│   ├── base/
│   │   ├── stack.py                # MyStackConfig(BaseStackConfig)
│   │   └── services/
│   │       ├── api.py              # Database + AppRunner configs
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
