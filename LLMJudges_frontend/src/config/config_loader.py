"""
Configuration loader for LLMJudges.

This module loads configuration from .env file and environment variables.
"""

import os
from pathlib import Path


def load_env_file(env_path: Path | str | None = None) -> dict[str, str]:
    """
    Load environment variables from .env file.

    Args:
        env_path: Path to .env file. If None, looks in src/config/.env

    Returns:
        Dictionary of environment variables loaded from file
    """
    if env_path is None:
        # Default to src/config/.env
        config_dir = Path(__file__).parent
        env_path = config_dir / ".env"
    else:
        env_path = Path(env_path)

    env_vars = {}

    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                # Parse KEY=VALUE
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]

                    env_vars[key] = value

    return env_vars


def get_config_path() -> Path:
    """Get the path to the config directory."""
    return Path(__file__).parent


def env_file_exists() -> bool:
    """Check if .env file exists in config directory."""
    config_dir = get_config_path()
    env_path = config_dir / ".env"
    return env_path.exists()


def create_env_file_from_example() -> bool:
    """
    Create .env file from .env.example if it doesn't exist.

    Returns:
        True if file was created, False if it already exists
    """
    config_dir = get_config_path()
    env_path = config_dir / ".env"

    if env_path.exists():
        return False

    return True


def set_default_file_env_vars() -> None:
    """Set environment variables from .env file. If the environment variable is already set, it will not be overridden."""
    env_from_file = load_env_file()
    for k, v in env_from_file.items():
        if k not in os.environ:
            os.environ[k] = v
