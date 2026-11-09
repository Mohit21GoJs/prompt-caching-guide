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


def cache_read(provider: str, usage: dict) -> int:
    """Tokens served from cache, using each provider's own field name."""
    if provider == "anthropic":
        return usage.get("cache_read_input_tokens", 0)
    return (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)


CHANGES = {
    "question": "Change only the final question",
    "handbook": "Change one byte in the handbook",
    "tools": "Reverse the order of the tools",
}


def turn_numbers(provider: str, usage: dict) -> dict:
    """Read, write and plain input tokens for one call, from each provider's own fields."""
    if provider == "anthropic":
        read = usage.get("cache_read_input_tokens", 0)
        write = usage.get("cache_creation_input_tokens", 0)
        plain = usage.get("input_tokens", 0)
        return {"plain": plain, "read": read, "write": write, "total": plain + read + write}
    details = usage.get("input_tokens_details") or {}
    read = details.get("cached_tokens", 0)
    write = details.get("cache_write_tokens", 0)
    total = usage.get("input_tokens", 0)
    return {"plain": max(0, total - read - write), "read": read, "write": write, "total": total}


def turns_table(provider: str, usages: list[dict]) -> str:
    """Markdown table, one row per turn, with a bar for the share read from cache."""
    names = (
        ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
        if provider == "anthropic"
        else ("input_tokens (total)", "cached_tokens", "cache_write_tokens")
    )
    head = f"| Turn | {names[0]} | `{names[1]}` | `{names[2]}` | Share read from cache |\n|---|---|---|---|---|"
    rows = []
    for i, usage in enumerate(usages, 1):
        n = turn_numbers(provider, usage)
        shown_first = n["plain"] if provider == "anthropic" else n["total"]
        share = n["read"] / n["total"] if n["total"] else 0
        rows.append(f"| {i} | {shown_first} | {n['read']} | {n['write']} | `{'█' * round(share * 20):<20}` {share:.0%} |")
    return head.replace(f"| {names[0]} |", f"| `{names[0]}` |", 1) + "\n" + "\n".join(rows)


REWRITES = {
    "first": "Edit the first message",
    "middle": "Edit a message in the middle",
    "drop": "Drop the oldest turn (sliding window)",
    "summarize": "Replace old turns with a summary",
}


def explain_error(error: Exception, provider: str, where: str = "") -> str:
    """A plain message for a failed live call, with the likeliest fix for each kind of failure."""
    name = type(error).__name__
    key = KEY_NAMES[provider]
    if "Authentication" in name or "PermissionDenied" in name:
        hint = f"The provider rejected the key. A `{key}` set in your shell overrides `.env`, so check that one first. Keys can also expire."
    elif "NotFound" in name:
        hint = f"The model name was not found. Set `{provider.upper()}_MODEL` in `.env` to a model your key can use."
    elif "RateLimit" in name:
        hint = "You hit a rate or spend limit. Wait a minute or check your account."
    elif "Connection" in name or "Timeout" in name:
        hint = "The request never reached the provider. Check your network."
    else:
        hint = "Check the key, the model name and your network."
    return f"The live call failed{where}: `{name}`. {hint} Or switch to Replay."
