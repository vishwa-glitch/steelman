"""Settings, read from the environment or backend/.env. Model names live here so swapping models is one line."""

import os
from dataclasses import dataclass
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str
    openrouter_base_url: str
    opponent_model: str
    judge_model: str
    judge_backup_model: str
    opponent_backup_model: str
    request_timeout_s: float
    database_url: str
    daily_ai_call_limit: int
    debates_per_ip_per_day: int
    ip_hash_salt: str
    cors_origins: tuple[str, ...]
    trust_proxy: bool


def normalize_db_url(url: str) -> str:
    """Hosts hand out URLs like postgresql://... or postgres://...; SQLAlchemy needs the driver named."""
    for prefix in ("postgresql+psycopg://", "postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def load_settings() -> Settings:
    file_values = _read_env_file(ENV_FILE)

    def get(name: str, default: str = "") -> str:
        return os.environ.get(name) or file_values.get(name) or default

    return Settings(
        openrouter_api_key=get("OPENROUTER_API_KEY"),
        openrouter_base_url=get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        opponent_model=get("OPPONENT_MODEL", "inclusionai/ling-3.2-flash:free"),
        judge_model=get("JUDGE_MODEL", "nvidia/nemotron-3.5-super-vl:free"),
        judge_backup_model=get("JUDGE_BACKUP_MODEL", "baidu/ernie-5.5-flash-preview:free"),
        # Used when the opponent's free model is rate-limited upstream. Not the judge's maker (NVIDIA).
        opponent_backup_model=get("OPPONENT_BACKUP_MODEL", "baidu/ernie-5.5-flash-preview:free"),
        request_timeout_s=float(get("REQUEST_TIMEOUT_S", "90")),
        database_url=normalize_db_url(
            get("DATABASE_URL", "postgresql+psycopg://steelman:steelman-local-only@localhost:5433/steelman")
        ),
        # The free cap is 50 requests a day for the whole account, shared with the evals (35 a day).
        daily_ai_call_limit=int(get("DAILY_AI_CALL_LIMIT", "12")),
        debates_per_ip_per_day=int(get("DEBATES_PER_IP_PER_DAY", "4")),
        ip_hash_salt=get("IP_HASH_SALT", "local-dev-salt"),
        cors_origins=tuple(  # browsers send the origin with no trailing slash, so drop any that was typed
            o.strip().rstrip("/") for o in get("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()
        ),
        # Only behind a proxy we control: X-Forwarded-For can be forged by anyone otherwise.
        trust_proxy=get("TRUST_PROXY", "0") == "1",
    )
