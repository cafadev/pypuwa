# Example: Basic pypuwa Project

This shows a complete infrastructure project using `pypuwa` to manage
configuration for a Django API + Celery worker + Redis stack on Azure.

## Structure

```
.
├── __main__.py                     # Pulumi entry point
├── config/
│   ├── base/
│   │   ├── stack.py                # MyStackConfig (extends BaseStackConfig)
│   │   └── services/
│   │       ├── api.py              # Database + AppRunner configs
│   │       ├── worker.py           # Worker config (shares API's database)
│   │       └── redis.py            # Cache config
│   └── environments/
│       ├── staging.py              # Small instances, debug enabled
│       └── production.py           # Multi-AZ, large instances
├── components/                     # Cloud-specific Pulumi wrappers (YOUR code)
│   ├── database.py                 # Azure PostgreSQL Flexible Server
│   ├── container_app.py            # Azure Container Apps
│   └── redis.py                    # Azure Cache for Redis
└── services/                       # Deployment orchestration
    ├── api/entrypoint.py
    └── worker/entrypoint.py
```

## Key Patterns Demonstrated

### 1. Interpolation
```python
SERVICE_NAME: str = "{stack}-api"              # "staging-api" or "production-api"
DATABASE_NAME: str = "${services.api.database.name}"  # Resolved from config tree
```

### 2. Secrets
```python
DJANGO_SECRET_KEY: Secret = secret()                          # Auto-inferred key
DATABASE_PASSWORD: Secret = secret("${services.api.database.password}")  # Cross-service
```

### 3. Environment Variable Generation
```python
env_vars = config.services.api.APP_RUNNER.env_dict_with_outputs()
# Returns only app env vars (CPU, MEMORY excluded via _NON_ENV_FIELDS)
# Secrets are Pulumi Outputs, resolved at deploy time
```

### 4. Environment Overrides
```python
# Base defaults: CPU="1 vCPU", MULTI_AZ=False
# Production overrides: CPU="4 vCPU", MULTI_AZ=True
# No duplication — only override what differs
```

## Usage

```bash
# Install dependencies
pip install -e .

# Preview staging
pulumi stack select staging
pulumi preview

# Deploy production
pulumi stack select production
pulumi up
```
