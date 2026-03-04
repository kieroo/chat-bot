from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_local_env(path: str = ".env") -> None:
    env_file = Path(path)
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_local_env()


@dataclass
class Settings:
    provider: str = os.getenv("AI_PROVIDER", "openai").strip().lower()
    model: str = os.getenv("AI_MODEL", "gpt-4o-mini").strip()
    timeout: float = float(os.getenv("AI_TIMEOUT", "60"))

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    anthropic_base_url: str = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")

    deepseek_api_key: str | None = os.getenv("DEEPSEEK_API_KEY")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")

    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")


settings = Settings()
