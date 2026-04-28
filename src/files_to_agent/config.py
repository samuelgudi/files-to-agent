from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, EnvSettingsSource, SettingsConfigDict


class _CommaSepEnvSource(EnvSettingsSource):
    """Custom env source that does NOT JSON-decode BOT_ALLOWED_USER_IDS.

    pydantic-settings v2 tries json.loads() on all complex (list/dict) fields.
    For a comma-separated env var like '111,222,333' that raises JSONDecodeError.
    We intercept and return the raw string so the BeforeValidator can parse it.
    """

    PASSTHROUGH = {"BOT_ALLOWED_USER_IDS", "bot_allowed_user_ids"}

    def decode_complex_value(
        self, field_name: str, field_info: Any, value: Any
    ) -> Any:
        if field_name in self.PASSTHROUGH or (
            hasattr(field_info, "alias") and field_info.alias in self.PASSTHROUGH
        ):
            return value
        return super().decode_complex_value(field_name, field_info, value)


def _parse_int_list(v: object) -> list[int]:
    """Accept comma-separated string, JSON array, bare int, or list."""
    if isinstance(v, str):
        stripped = v.strip()
        if stripped.startswith("["):
            import json
            return [int(x) for x in json.loads(stripped)]
        return [int(x.strip()) for x in stripped.split(",") if x.strip()]
    if isinstance(v, (list, tuple)):
        return [int(x) for x in v]
    if isinstance(v, int):
        return [v]
    raise ValueError("BOT_ALLOWED_USER_IDS must be a comma-separated list of ints")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(..., alias="BOT_TOKEN")
    bot_allowed_user_ids: list[int] = Field(..., alias="BOT_ALLOWED_USER_IDS")

    staging_dir: Path = Field(Path("/data/staging"), alias="STAGING_DIR")
    db_path: Path = Field(Path("/data/files-to-agent.db"), alias="DB_PATH")

    resolver_host: str = Field("0.0.0.0", alias="RESOLVER_HOST")
    resolver_port: int = Field(8080, alias="RESOLVER_PORT")
    resolver_auth: Literal["none", "apikey"] = Field("none", alias="RESOLVER_AUTH")
    resolver_api_key: str | None = Field(None, alias="RESOLVER_API_KEY")

    max_disk_bytes: int = Field(16_106_127_360, alias="MAX_DISK_BYTES")
    max_upload_size_bytes: int = Field(2_147_483_648, alias="MAX_UPLOAD_SIZE_BYTES")

    log_level: str = Field("INFO", alias="LOG_LEVEL")

    @classmethod
    def settings_customise_sources(cls, settings_cls: type, **kwargs: Any) -> tuple:  # type: ignore[override]
        init_settings = kwargs.get("init_settings")
        env_settings = kwargs.get("env_settings")
        dotenv_settings = kwargs.get("dotenv_settings")
        secrets_settings = kwargs.get("secrets_settings")
        # Replace default env source with our comma-aware subclass.
        custom_env = _CommaSepEnvSource(settings_cls)
        sources = []
        if init_settings is not None:
            sources.append(init_settings)
        sources.append(custom_env)
        if dotenv_settings is not None:
            sources.append(dotenv_settings)
        if secrets_settings is not None:
            sources.append(secrets_settings)
        return tuple(sources)

    @model_validator(mode="before")
    @classmethod
    def _parse_ids(cls, values: Any) -> Any:
        if isinstance(values, dict):
            raw = values.get("BOT_ALLOWED_USER_IDS") or values.get("bot_allowed_user_ids")
            if raw is not None:
                values["BOT_ALLOWED_USER_IDS"] = _parse_int_list(raw)
        return values

    @model_validator(mode="after")
    def _check_auth_pairing(self) -> "Settings":
        if self.resolver_auth == "apikey" and not self.resolver_api_key:
            raise ValueError("RESOLVER_API_KEY is required when RESOLVER_AUTH=apikey")
        return self
