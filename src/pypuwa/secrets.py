"""
Secret management for Pulumi configuration.

Provides the Secret type marker and secret() function for declaring
fields that should be loaded from Pulumi encrypted config at runtime.
"""

import inspect
from typing import NewType, Optional

Secret = NewType("Secret", str)


def secret(key: Optional[str] = None) -> Secret:
    """
    Mark a field as a secret that should be loaded from Pulumi config at runtime.

    Args:
        key: The Pulumi config key for this secret. If None, auto-infers
             from the field name (converted to UPPER_SNAKE_CASE).

    Returns:
        A Secret marker string that will be resolved at runtime by SecretResolver.

    Examples:
        # Explicit key
        password: Secret = secret("DATABASE_PASSWORD")

        # Auto-inferred from field name
        jwt_secret: Secret = secret()  # -> "JWT_SECRET"

        # Cross-service reference
        redis_password: Secret = secret("${services.redis.AUTH_TOKEN}")
    """
    if key is not None:
        return Secret(f"secret:{key}")

    frame = inspect.currentframe()
    try:
        if frame and frame.f_back:
            caller_frame = frame.f_back
            caller_locals = caller_frame.f_locals

            if "__annotations__" in caller_locals:
                filename = caller_frame.f_code.co_filename
                lineno = caller_frame.f_lineno

                try:
                    with open(filename, "r") as f:
                        lines = f.readlines()
                        if lineno <= len(lines):
                            line = lines[lineno - 1].strip()
                            if ":" in line and "=" in line and "secret()" in line:
                                field_part = line.split(":")[0].strip()
                                field_name = field_part.split()[-1]
                                inferred_key = field_name.upper()
                                return Secret(f"secret:{inferred_key}")
                except (IOError, IndexError, OSError):
                    pass
    except Exception:
        pass
    finally:
        del frame

    raise ValueError(
        "Could not auto-infer secret key. Please provide an explicit key: secret('YOUR_KEY'). "
        "Auto-inference requires the secret() call to be on a single line in the format: "
        "'field_name: Secret = secret()'"
    )


def is_secret(value: object) -> bool:
    """Check if a value is a secret marker."""
    return isinstance(value, str) and value.startswith("secret:")


def get_secret_key(value: str) -> str:
    """Extract the secret key from a secret marker string."""
    return value[7:]  # Remove "secret:" prefix


def is_interpolation_reference(value: object) -> bool:
    """Check if a value is an interpolation reference like ${path.to.value}."""
    return isinstance(value, str) and value.startswith("${") and value.endswith("}")
