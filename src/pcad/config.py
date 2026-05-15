from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv as _dotenv_load


logger = logging.getLogger(__name__)


def load_dotenv(path: Path = Path(".env")) -> None:
    """Populate environment variables from a .env file if present.

    Thin wrapper around python-dotenv. Existing environment variables take
    precedence (matches the previous behavior).
    """
    if path.exists():
        _dotenv_load(dotenv_path=path, override=False)


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


def _resolve_database_url() -> str:
    """Return DATABASE_URL, stitching one from POSTGRES_* if it is not set.

    The demo's .env.example only ships POSTGRES_USER / PASSWORD / DB so users do
    not have to keep the credentials in sync across two variables. POSTGRES_HOST
    defaults to ``localhost``; inside Docker Compose it should be ``postgres``.
    """
    url = _env_optional("DATABASE_URL")
    if url:
        return url
    user = _env_optional("POSTGRES_USER") or "pcad"
    password = _env_optional("POSTGRES_PASSWORD") or "pcad"
    database = _env_optional("POSTGRES_DB") or "pcad"
    host = _env_optional("POSTGRES_HOST") or "localhost"
    port = _env_optional("POSTGRES_PORT") or "5432"
    from urllib.parse import quote

    return f"postgresql://{quote(user, safe='')}:{quote(password, safe='')}@{host}:{port}/{quote(database, safe='')}"


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
    session_ttl_hours: int
    session_secret: str
    rate_limit_per_ip_per_minute: int
    rate_limit_per_session_per_hour: int
    daily_token_budget: int
    context_token_budget: int = 6000
    agent_generation_max_attempts: int = 3
    db_pool_min_size: int = 1
    db_pool_max_size: int = 10
    llm_timeout_seconds: float = 120.0
    llm_max_retries: int = 3
    conversation_history_turns: int = 6

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        settings = cls(
            database_url=_resolve_database_url(),
            openrouter_api_key=_env_optional("LLM_API_KEY") or _env_optional("OPENROUTER_API_KEY"),
            openrouter_base_url=os.environ.get("LLM_BASE_URL", os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")),
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
            session_ttl_hours=_env_int("SESSION_TTL_HOURS", 4),
            session_secret=os.environ.get("SESSION_SECRET", "change-me-to-a-long-random-string"),
            rate_limit_per_ip_per_minute=_env_int("RATE_LIMIT_PER_IP_PER_MINUTE", 20),
            rate_limit_per_session_per_hour=_env_int("RATE_LIMIT_PER_SESSION_PER_HOUR", 50),
            daily_token_budget=_env_int("DAILY_TOKEN_BUDGET", 1_500_000),
            context_token_budget=_env_int("CONTEXT_TOKEN_BUDGET", 6000),
            agent_generation_max_attempts=_env_int("AGENT_GENERATION_MAX_ATTEMPTS", 3),
            db_pool_min_size=_env_int("DB_POOL_MIN_SIZE", 1),
            db_pool_max_size=_env_int("DB_POOL_MAX_SIZE", 10),
            llm_timeout_seconds=float(os.environ.get("LLM_TIMEOUT_SECONDS", "120")),
            llm_max_retries=_env_int("LLM_MAX_RETRIES", 3),
            conversation_history_turns=_env_int("CONVERSATION_HISTORY_TURNS", 6),
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
