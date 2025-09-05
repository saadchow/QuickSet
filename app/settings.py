from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class AppSettings(BaseSettings):
    db_url: str = Field(default="sqlite:///./data.sqlite3")
    toronto_tz: str = Field(default="America/Toronto")
    user_agent: str = Field(default="DropInBot/1.0 (+https://example.com)")
    request_timeout_seconds: int = Field(default=20)
    polite_delay_seconds_min: float = Field(default=1.0)
    polite_delay_seconds_max: float = 2.0
    log_level: str = Field(default="INFO")

class PathSettings(BaseSettings):
    facilities_file: str = Field(default="./facilities.json")

class Settings(BaseSettings):
    app: AppSettings = AppSettings()
    paths: PathSettings = PathSettings()

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_prefix="",
        env_file=None,
        case_sensitive=False,
        toml_file="settings.toml",
    )

settings = Settings()
