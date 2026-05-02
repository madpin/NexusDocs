"""Process-wide configuration via pydantic-settings."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NEXUSDOCS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Repository selection
    repository_backend: str = Field(default="memory", description="memory | neo4j")

    # Neo4j
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="neo4j")
    neo4j_database: str = Field(default="neo4j")

    # LLM
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str | None = Field(
        default=None,
        description=(
            "Optional base URL for OpenAI-compatible providers "
            "(Azure, Ollama, vLLM, LM Studio, etc.). "
            "Defaults to the official OpenAI endpoint when unset."
        ),
    )

    @field_validator("openai_api_key", "openai_base_url", mode="before")
    @classmethod
    def _empty_string_is_none(cls, v):
        # Docker env vars often pass through as "" when unset; treat blank
        # values as missing instead of so-many-empty-strings.
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    api_cors_origins: list[str] = ["*"]


def get_settings() -> Settings:
    return Settings()
