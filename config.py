"""Environment-driven settings and LLM factory. No hardcoded keys."""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass, field

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel

load_dotenv()

# OpenAI models are fixed to these two reasoning-effort presets (selectable in the UI).
OPENAI_MODEL_OPTIONS = {
    "GPT-5.6 Luna (medium effort)": "gpt-5.6-luna",
    "GPT-5.6 Terra (medium effort)": "gpt-5.6-terra",
}
OPENAI_REASONING_EFFORT = "medium"
DEFAULT_STRONG_MODEL = next(iter(OPENAI_MODEL_OPTIONS.values()))
DEFAULT_FAST_MODEL = next(iter(OPENAI_MODEL_OPTIONS.values()))

DEFAULT_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
DEFAULT_OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

# Agnes AI is fixed to this model — not user-configurable.
AGNES_MODEL = "agnes-2.5-flash"
DEFAULT_AGNES_BASE_URL = os.environ.get("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1")

IGNORED_DIR_NAMES = {
    ".git", "node_modules", ".venv", "venv", "env", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build",
    ".next", "target", ".idea", ".vscode", ".tox", "coverage",
    ".terraform", "vendor",
}

KEY_FILE_PRIORITY = [
    "readme.md", "readme.rst", "readme.txt", "readme",
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "package.json", "cargo.toml", "go.mod", "pom.xml", "build.gradle",
    "dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "makefile", "main.py", "app.py", "server.py", "manage.py",
    "index.js", "index.ts", "index.tsx",
]


@dataclass
class Settings:
    strong_model: str = DEFAULT_STRONG_MODEL
    strong_provider: str = "openai"  # "openai" or "agnes"
    fast_provider: str = "openai"  # "openai", "ollama", or "agnes"
    fast_model: str = DEFAULT_FAST_MODEL
    ollama_model: str = DEFAULT_OLLAMA_MODEL
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL
    temperature_strong: float = 0.2
    temperature_fast: float = 0.1
    max_files: int = 12
    max_file_chars: int = 6000
    keep_after: bool = False
    error: str | None = field(default=None, repr=False)


def ollama_available(base_url: str = DEFAULT_OLLAMA_BASE_URL, timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(base_url, timeout=timeout):
            return True
    except Exception:
        return False


def list_ollama_models(base_url: str = DEFAULT_OLLAMA_BASE_URL, timeout: float = 2.0) -> list[str]:
    """Return the names of models the user has pulled into their local Ollama server."""
    try:
        url = f"{base_url.rstrip('/')}/api/tags"
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def _build_openai_compatible_llm(
    model: str,
    temperature: float,
    api_key_env: str,
    base_url: str | None,
    reasoning_effort: str | None = None,
) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise RuntimeError(f"{api_key_env} environment variable is not set.")
    kwargs = {"reasoning_effort": reasoning_effort} if reasoning_effort else {}
    return ChatOpenAI(model=model, temperature=temperature, api_key=api_key, base_url=base_url, **kwargs)


def build_strong_llm(settings: Settings) -> BaseChatModel:
    """Stronger model for architecture explanation and hard questions."""
    if settings.strong_provider == "agnes":
        return _build_openai_compatible_llm(
            settings.strong_model, settings.temperature_strong, "AGNES_API_KEY", DEFAULT_AGNES_BASE_URL
        )
    return _build_openai_compatible_llm(
        settings.strong_model,
        settings.temperature_strong,
        "OPENAI_API_KEY",
        os.environ.get("OPENAI_BASE_URL") or None,
        reasoning_effort=OPENAI_REASONING_EFFORT,
    )


def build_fast_llm(settings: Settings) -> BaseChatModel:
    """Faster/cheaper model for file summaries and simple Q&A. Ollama or Agnes AI if selected."""
    if settings.fast_provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.ollama_model,
            temperature=settings.temperature_fast,
            base_url=settings.ollama_base_url,
        )
    if settings.fast_provider == "agnes":
        return _build_openai_compatible_llm(
            settings.fast_model, settings.temperature_fast, "AGNES_API_KEY", DEFAULT_AGNES_BASE_URL
        )
    return _build_openai_compatible_llm(
        settings.fast_model,
        settings.temperature_fast,
        "OPENAI_API_KEY",
        os.environ.get("OPENAI_BASE_URL") or None,
        reasoning_effort=OPENAI_REASONING_EFFORT,
    )
