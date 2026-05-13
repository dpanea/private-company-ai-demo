from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path


logger = logging.getLogger(__name__)


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _env_optional(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return None
    return value


def _env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str
    openrouter_api_key: str | None
    openrouter_base_url: str
    llm_model: str
    llm_reasoning_effort: str
    embedding_model: str
    embedding_dimensions: int
    app_title: str
    http_referer: str | None
    log_level: str
    log_color: bool
    session_cookie_name: str
    session_ttl_days: int
    session_secret: str
    rate_limit_per_ip_per_minute: int
    rate_limit_per_session_per_hour: int
    daily_token_budget: int
    context_token_budget: int = 6000
    agent_generation_max_attempts: int = 3

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        settings = cls(
            database_url=os.environ.get("DATABASE_URL", "postgresql://pcad:pcad@localhost:5432/pcad"),
            openrouter_api_key=_env_optional("OPENROUTER_API_KEY"),
            openrouter_base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            llm_model=os.environ.get("LLM_MODEL", "qwen/qwen-2.5-7b-instruct"),
            llm_reasoning_effort=os.environ.get("LLM_REASONING_EFFORT", "low"),
            embedding_model=os.environ.get("EMBEDDING_MODEL", "qwen/qwen3-embedding-8b"),
            embedding_dimensions=_env_int("EMBEDDING_DIMENSIONS", 1536),
            app_title=os.environ.get("APP_TITLE", "Private Company Memory Demo"),
            http_referer=_env_optional("HTTP_REFERER"),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
            log_color=_env_bool("LOG_COLOR", False),
            session_cookie_name=os.environ.get("SESSION_COOKIE_NAME", "pcad_session"),
            session_ttl_days=_env_int("SESSION_TTL_DAYS", 7),
            session_secret=os.environ.get("SESSION_SECRET", "change-me-to-a-long-random-string"),
            rate_limit_per_ip_per_minute=_env_int("RATE_LIMIT_PER_IP_PER_MINUTE", 20),
            rate_limit_per_session_per_hour=_env_int("RATE_LIMIT_PER_SESSION_PER_HOUR", 50),
            daily_token_budget=_env_int("DAILY_TOKEN_BUDGET", 1_500_000),
            context_token_budget=_env_int("CONTEXT_TOKEN_BUDGET", 6000),
            agent_generation_max_attempts=_env_int("AGENT_GENERATION_MAX_ATTEMPTS", 3),
        )
        if settings.llm_reasoning_effort not in {"low", "medium", "high"}:
            raise ValueError("LLM_REASONING_EFFORT must be one of: low, medium, high")
        logger.debug(
            "settings.loaded database_url_configured=%s openrouter_key_configured=%s embedding_model=%s llm_model=%s embedding_dimensions=%s reasoning_effort=%s context_token_budget=%s generation_max_attempts=%s log_level=%s log_color=%s",
            bool(settings.database_url),
            bool(settings.openrouter_api_key),
            settings.embedding_model,
            settings.llm_model,
            settings.embedding_dimensions,
            settings.llm_reasoning_effort,
            settings.context_token_budget,
            settings.agent_generation_max_attempts,
            settings.log_level,
            settings.log_color,
        )
        return settings

    def require_openrouter_key(self) -> None:
        if not self.openrouter_api_key:
            logger.error("openrouter.api_key_missing")
            raise RuntimeError("OPENROUTER_API_KEY is required. Add it to local .env.")
