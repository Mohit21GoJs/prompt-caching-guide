"""Prices and a small cost simulator for the break-even lesson. No network, no API calls.

Prices are a dated snapshot, checked against the vendors' pricing pages on the date
below. They change often. Recheck before you rely on any number here.
"""

from __future__ import annotations

from datetime import date

PRICES_CHECKED = date(2026, 10, 19)
STALE_AFTER_DAYS = 60

# Dollars per million tokens, and multipliers on the input price.
PRICES = {
    "anthropic": {
        "model": "claude-sonnet-5-5",
        "input": 2.00,
        "output": 10.00,
        "read": 0.05,
        "write": {"5m": 1.25, "1h": 2.00},
        "ttl_minutes": {"5m": 5, "1h": 60},
        "source": "https://platform.claude.com/docs/en/about-claude/pricing",
    },
    "openai": {
        "model": "gpt-5.6-sol",
        "input": 4.00,
        "output": 20.00,
        "read": 0.10,
        "write": {"30m": 1.25},
        "ttl_minutes": {"30m": 30},
        "source": "https://developers.openai.com/api/docs/pricing",
    },
}

# name -> (gaps in minutes between consecutive calls, does the prefix stay identical?)
SCENARIOS = {
    "Support chatbot: 20 turns, 1 minute apart": ([1.0] * 19, True),
    "Agent loop: 8 calls, 10 seconds apart": ([1 / 6] * 7, True),
    "One-off job: a single call": ([], True),
    "Steady but spaced: 6 calls, 3 minutes apart": ([3.0] * 5, True),
    "Sparse traffic: 6 calls, 10 minutes apart": ([10.0] * 5, True),
    "Overnight batch: 3 calls, 90 minutes apart": ([90.0] * 2, True),
    "Timestamp at the start: 10 calls, prefix changes every call": ([1.0] * 9, False),
}


def price_age_days(today: date | None = None) -> int:
    return ((today or date.today()) - PRICES_CHECKED).days


def cost_of_usage(provider: str, usage: dict) -> float:
    """Dollar cost of one recorded call, from the provider's raw usage fields."""
    p = PRICES[provider]
    per_token = p["input"] / 1e6
    if provider == "anthropic":
        created = usage.get("cache_creation") or {}
        write_5m = created.get("ephemeral_5m_input_tokens", 0)
        write_1h = created.get("ephemeral_1h_input_tokens", 0)
        cost = usage.get("input_tokens", 0) * per_token
        cost += usage.get("cache_read_input_tokens", 0) * per_token * p["read"]
        cost += write_5m * per_token * p["write"]["5m"] + write_1h * per_token * p["write"]["1h"]
    else:
        details = usage.get("input_tokens_details") or {}
        read, write = details.get("cached_tokens", 0), details.get("cache_write_tokens", 0)
        plain = max(0, usage.get("input_tokens", 0) - read - write)
        cost = plain * per_token + read * per_token * p["read"] + write * per_token * p["write"]["30m"]
    return cost + usage.get("output_tokens", 0) * p["output"] / 1e6


def uncached_cost_of_usage(provider: str, usage: dict) -> float:
    """The same call with every input token billed at the plain input price."""
    p = PRICES[provider]
    if provider == "anthropic":
        total_in = sum(usage.get(k, 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    else:
        total_in = usage.get("input_tokens", 0)
    return total_in * p["input"] / 1e6 + usage.get("output_tokens", 0) * p["output"] / 1e6


def simulate(
    provider: str,
    prefix_tokens: int,
    gaps_minutes: list[float],
    ttl: str,
    stable: bool = True,
    tail_tokens: int = 60,
    output_tokens: int = 100,
) -> dict:
    """Cost of a series of calls with and without caching.

    Assumption: a hit refreshes the cache lifetime. Anthropic documents that. For OpenAI
    it is an assumption, so treat the OpenAI sparse-traffic rows as estimates.
    """
    p = PRICES[provider]
    per_token = p["input"] / 1e6
    ttl_minutes = p["ttl_minutes"][ttl]
    calls = len(gaps_minutes) + 1
    other = (tail_tokens * p["input"] + output_tokens * p["output"]) / 1e6
    cached = uncached = 0.0
    writes = reads = 0
    for i in range(calls):
        hit = i > 0 and stable and gaps_minutes[i - 1] <= ttl_minutes
        if hit:
            reads += 1
            cached += prefix_tokens * per_token * p["read"] + other
        else:
            writes += 1
            cached += prefix_tokens * per_token * p["write"][ttl] + other
        uncached += prefix_tokens * per_token + other
    saving = 1 - cached / uncached
    verdict = "Pays" if saving > 0.05 else "Bites" if saving < -0.01 else "About even"
    return {"calls": calls, "writes": writes, "reads": reads, "cached": cached, "uncached": uncached, "saving": saving, "verdict": verdict}


def break_even_reuses(provider: str, ttl: str) -> int:
    """Fewest reuses after the first write at which caching costs no more than not caching.

    Counts only the prefix, ignoring the changing tail and output. Needs w + n*r <= 1 + n.
    """
    p = PRICES[provider]
    w, r = p["write"][ttl], p["read"]
    n = 0
    while w + n * r > 1 + n:
        n += 1
    return n
