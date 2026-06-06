from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict, TomlConfigSettingsSource, YamlConfigSettingsSource


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt: str = "%Y-%m-%d %H:%M:%S"
    json_format: bool = False
    log_file: Optional[str] = None
    max_mb: int = 10
    backup_count: int = 5
    correlation_id: bool = True
    # Time-based rotation
    rotation_when: str = "midnight"  # 'S', 'M', 'H', 'D', 'midnight', 'W0'-'W6'
    rotation_interval: int = 1

    model_config = SettingsConfigDict(env_prefix="NGD_LOG_")


class Config(BaseSettings):
    """NVIDIA Gratitude Driver configuration.

    Supports configuration via (in precedence order):
    1. CLI arguments (handled explicitly in driver.py/diagnostics.py)
    2. Environment variables (prefixed with NGD_)
    3. Config file (YAML or TOML at ~/.config/ngd/config.yaml or ./ngd.yaml)
    4. Defaults below
    """

    # GPU settings
    gpu_index: int = Field(default=0, description="GPU index to monitor")
    sampling_interval_seconds: float = Field(default=1.0, description="Sampling interval in seconds")

    # VRAM thresholds (model-aware)
    model_vram_mb: float = Field(default=4500, description="VRAM footprint of local model (MB)")
    safety_margin_mb: float = Field(default=512, description="Safety margin above model VRAM for CLEAR threshold (MB)")

    # Cooldown
    cooldown_seconds: float = Field(default=90, description="Cooldown after breach in seconds")

    # Log rotation
    max_log_mb: float = Field(default=10, description="Rotate telemetry log at this size (MB)")

    # Browser telemetry
    browser_telemetry_enabled: bool = Field(default=True, description="Enable aggregate Chrome process telemetry")

    # Runtime/cache paths
    runtime_dir: str = Field(default="runtime/nvidia_gratitude_driver", description="Runtime output directory")
    cache_dir: Optional[str] = Field(default=None, description="Cache directory (defaults to runtime_dir/cache)")

    # Logging
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # Smoothing
    ewma_alpha: float = Field(default=0.22, description="EWMA smoothing alpha (0, 1]")

    model_config = SettingsConfigDict(
        env_prefix="NGD_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        file_secret_settings: Any,
    ) -> tuple[Any, ...]:
        """Define config file sources with precedence: TOML > YAML."""
        return (
            init_settings,
            env_settings,
            TomlConfigSettingsSource(settings_cls),
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )

    def get_cache_path(self) -> Path:
        """Get the cache directory path."""
        if self.cache_dir:
            return Path(self.cache_dir).expanduser().resolve()
        return Path(self.runtime_dir).expanduser().resolve() / "cache"

    def get_runtime_path(self) -> Path:
        """Get the runtime directory path."""
        return Path(self.runtime_dir).expanduser().resolve()

    def get_status_path(self) -> Path:
        return self.get_runtime_path() / "status.json"

    def get_log_path(self) -> Path:
        return self.get_runtime_path() / "telemetry.jsonl"

    def get_driver_log_path(self) -> Path:
        return self.get_runtime_path() / "driver.log"


def load_config(
    config_file: Optional[str] = None,
    **overrides: Any,
) -> Config:
    """Load configuration with optional file and CLI overrides.

    Args:
        config_file: Optional path to config file (YAML or TOML)
        **overrides: CLI argument overrides (highest precedence)

    Returns:
        Config instance with merged settings
    """
    # Determine config file paths to check
    config_paths: list[Path] = []
    if config_file:
        config_paths.append(Path(config_file).expanduser().resolve())
    else:
        # Default locations
        config_paths.append(Path.home() / ".config" / "ngd" / "config.yaml")
        config_paths.append(Path.home() / ".config" / "ngd" / "config.toml")
        config_paths.append(Path.cwd() / "ngd.yaml")
        config_paths.append(Path.cwd() / "ngd.toml")

    # Find first existing config file
    found_config: Optional[Path] = None
    for p in config_paths:
        if p.exists():
            found_config = p
            break

    # Prepare init kwargs with overrides
    init_kwargs = dict(overrides)
    if found_config:
        init_kwargs["_env_file"] = str(found_config)
        init_kwargs["_env_file_encoding"] = "utf-8"

    return Config(**init_kwargs)