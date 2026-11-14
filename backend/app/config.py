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
    request_timeout_s: float


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
        request_timeout_s=float(get("REQUEST_TIMEOUT_S", "90")),
    )
