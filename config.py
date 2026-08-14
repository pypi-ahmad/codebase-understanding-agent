"""Environment-driven settings and LLM factory. No hardcoded keys."""

from __future__ import annotations

import os
import urllib.request
from dataclasses import dataclass, field

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel

load_dotenv()

DEFAULT_STRONG_MODEL = os.environ.get("OPENAI_STRONG_MODEL", "gpt-4o")
DEFAULT_FAST_MODEL = os.environ.get("OPENAI_FAST_MODEL", "gpt-4o-mini")
DEFAULT_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
DEFAULT_OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

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
    fast_provider: str = "openai"  # "openai" or "ollama"
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


def build_strong_llm(settings: Settings) -> BaseChatModel:
    """Stronger model for architecture explanation and hard questions."""
    from langchain_openai import ChatOpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
    base_url = os.environ.get("OPENAI_BASE_URL") or None
    return ChatOpenAI(
        model=settings.strong_model,
        temperature=settings.temperature_strong,
        api_key=api_key,
        base_url=base_url,
    )


def build_fast_llm(settings: Settings) -> BaseChatModel:
    """Faster/cheaper model for file summaries and simple Q&A. Ollama if selected."""
    if settings.fast_provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.ollama_model,
            temperature=settings.temperature_fast,
            base_url=settings.ollama_base_url,
        )

    from langchain_openai import ChatOpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
    base_url = os.environ.get("OPENAI_BASE_URL") or None
    return ChatOpenAI(
        model=settings.fast_model,
        temperature=settings.temperature_fast,
        api_key=api_key,
        base_url=base_url,
    )
