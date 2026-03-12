"""Configuration management for yesitsme."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv


@dataclass
class Config:
    """Configuration container for yesitsme."""

    session_id: str = ""
    timeout: int = 10
    proxy: Optional[str] = None
    max_retries: int = 3
    retry_delay: float = 1.0
    export_format: str = "json"
    output_dir: str = "output"
    log_level: str = "INFO"
    verbose: bool = False

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """
        Load configuration from file and environment variables.

        Priority (highest to lowest):
        1. Environment variables
        2. config.yaml file
        3. Default values

        Args:
            config_path: Path to config.yaml file. Defaults to ./config.yaml

        Returns:
            Config instance with loaded values
        """
        load_dotenv()

        config = cls()

        if config_path is None:
            config_path = "config.yaml"

        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, "r") as f:
                file_config = yaml.safe_load(f) or {}
                for key, value in file_config.items():
                    if hasattr(config, key) and value is not None:
                        setattr(config, key, value)

        config.session_id = os.getenv("INSTAGRAM_SESSION_ID", config.session_id)
        env_timeout = os.getenv("YESITSME_TIMEOUT")
        if env_timeout:
            config.timeout = int(env_timeout)

        env_proxy = os.getenv("YESITSME_PROXY")
        if env_proxy:
            config.proxy = env_proxy

        env_retries = os.getenv("YESITSME_MAX_RETRIES")
        if env_retries:
            config.max_retries = int(env_retries)

        env_verbose = os.getenv("YESITSME_VERBOSE")
        if env_verbose:
            config.verbose = env_verbose.lower() == "true"

        return config

    def save(self, config_path: str = "config.yaml") -> None:
        """
        Save current configuration to a YAML file.

        Args:
            config_path: Path to save the config file
        """
        config_dict = {
            k: v for k, v in self.__dict__.items() if k != "session_id"
        }
        with open(config_path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False)
