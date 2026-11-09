"""Small helpers shared by the lessons. Nothing here touches a provider API.

The lessons show the real request code. This file only loads recordings,
reads keys from the environment, builds a throwaway prompt prefix, and
formats the raw provider usage for display.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIAGRAMS = ROOT / "diagrams"
RECORDINGS = ROOT / "recordings"

DEFAULT_MODELS = {"anthropic": "claude-sonnet-5-5", "openai": "gpt-5.6-sol"}
KEY_NAMES = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}


def _load_dotenv() -> None:
    """Read ROOT/.env into os.environ without overriding variables already set."""
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            if value.strip():
                os.environ.setdefault(key.strip(), value.strip().strip("'\""))


_load_dotenv()


def api_key_present(provider: str) -> bool:
    return bool(os.environ.get(KEY_NAMES[provider]))


def model_for(provider: str) -> str:
    return os.environ.get(f"{provider.upper()}_MODEL") or DEFAULT_MODELS[provider]


def load_recording(provider: str, step: str) -> dict:
    return json.loads((RECORDINGS / f"{provider}.{step}.json").read_text())


def make_prefix(approx_tokens: int = 2000) -> str:
    """A fake support handbook, long enough to pass the caching minimum.

    The first line holds a random salt, so your prefix is unique to this call
    and you can never hit another person's warm cache. Reuse the same string
    for both calls in a lesson, or the second call will not hit.
    """
    lines = [f"SYNTHETIC SUPPORT HANDBOOK. Salt {uuid.uuid4().hex}."]
    for i in range(1, approx_tokens // 25 + 1):
        lines.append(f"Rule {i}: for case type {i}, check the customer's plan, then the region, then reply politely.")
    return "\n".join(lines)


def diagram(name: str) -> str:
    return (DIAGRAMS / f"{name}.svg").read_text()


def label(source: str, rec: dict | None = None, model: str = "", sdk: str = "") -> str:
    """The badge that tells a learner whether they are looking at their own run."""
    if source == "replay" and rec:
        return f"REPLAY: recorded {rec['captured_at']} on {rec['model']} with SDK {rec['sdk_version']}. Not your run."
    return f"LIVE: your run just now on {model} with SDK {sdk}."


def flat_usage(usage: dict, prefix: str = "") -> dict:
    """Flatten nested usage to dotted keys. Keys and values are unchanged."""
    out: dict = {}
    for key, value in usage.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            out.update(flat_usage(value, path + "."))
        else:
            out[path] = value
    return out


def usage_json(usage: dict) -> str:
    return json.dumps(usage, indent=2, sort_keys=True)
