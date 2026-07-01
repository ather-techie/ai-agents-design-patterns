"""Runtime configuration, resolved from the environment.

The single most important decision here is **mock vs live**: when no
``ANTHROPIC_API_KEY`` is present (or ``USE_MOCK=1`` is set), the framework runs
against the deterministic offline client so demos, tests, and the benchmark
harness need no network and no key — exactly what the README promises.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Default model for live calls. Adaptive thinking is configured in the client.
DEFAULT_MODEL = "claude-opus-4-8"


def _load_dotenv(path: Path) -> None:
    """Minimal ``.env`` loader (no dependency on python-dotenv).

    Only sets keys that aren't already in the environment, so real env vars win.
    """
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        os.environ.setdefault(key, value)


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Config:
    """Resolved settings for a run."""

    model: str = DEFAULT_MODEL
    use_mock: bool = True
    api_key: str | None = None
    max_steps: int = 6
    timeout_seconds: float = 60.0
    max_tokens: int = 1024

    @classmethod
    def from_env(cls, *, dotenv: bool = True) -> "Config":
        """Build a config from environment variables (and an optional ``.env``).

        Mock mode is selected when ``USE_MOCK`` is truthy or no API key is set —
        this is the default path, so the framework works out of the box offline.
        """
        if dotenv:
            _load_dotenv(Path.cwd() / ".env")

        api_key = os.environ.get("ANTHROPIC_API_KEY") or None
        forced_mock = _truthy(os.environ.get("USE_MOCK"))
        use_mock = forced_mock or api_key is None

        return cls(
            model=os.environ.get("AGENT_MODEL", DEFAULT_MODEL),
            use_mock=use_mock,
            api_key=api_key,
            max_steps=int(os.environ.get("AGENT_MAX_STEPS", "6")),
            timeout_seconds=float(os.environ.get("AGENT_TIMEOUT", "60")),
            max_tokens=int(os.environ.get("AGENT_MAX_TOKENS", "1024")),
        )
