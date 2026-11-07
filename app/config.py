from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_BLOCKED_PHRASES = ",".join(
    (
        "how to make a bomb",
        "how to build a bomb",
        "instructions to make a bomb",
        "steps to make a bomb",
        "how to poison someone",
        "how to kill someone",
        "how to steal passwords",
        "how to make ransomware",
    )
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    openai_api_key: str = ""
    openai_model: str = "gpt-6-astra"
    openai_verifier_model: str = ""
    max_question_chars: int = Field(default=4000, ge=100, le=20000)
    max_output_tokens: int = Field(default=1400, ge=128, le=8000)
    request_timeout_seconds: float = Field(default=90, ge=5, le=300)
    max_requests_per_minute: int = Field(default=30, ge=1, le=1000)
    max_concurrent_research: int = Field(default=4, ge=1, le=100)
    blocked_phrases: str = DEFAULT_BLOCKED_PHRASES
    allowed_hosts: str = "*"

    @field_validator("openai_api_key", "openai_model", "openai_verifier_model", mode="before")
    @classmethod
    def trim_strings(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @property
    def deny_phrases(self) -> tuple[str, ...]:
        built_in = DEFAULT_BLOCKED_PHRASES.split(",")
        extra = self.blocked_phrases.split(",")
        return tuple(phrase.strip().casefold() for phrase in (*built_in, *extra) if phrase.strip())

    @property
    def hostnames(self) -> list[str]:
        hosts = [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]
        return hosts or ["*"]

    @property
    def verifier_model(self) -> str:
        return self.openai_verifier_model or self.openai_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
