"""The calculator must reproduce the cost estimates stored with the real captures."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lessons"))

import economics
import guide


def rec(provider, step):
    return guide.load_recording(provider, step)["provider_usage"]


def test_matches_recorded_cost_estimates():
    assert round(economics.cost_of_usage("anthropic", rec("anthropic", "cold")), 6) == 0.023222
    assert round(economics.cost_of_usage("anthropic", rec("anthropic", "exact")), 7) == 0.0049596
    assert round(economics.cost_of_usage("openai", rec("openai", "cold")), 6) == 0.026077
    assert round(economics.cost_of_usage("openai", rec("openai", "exact")), 7) == 0.0048532


def test_break_even_reuses():
    assert economics.break_even_reuses("anthropic", "5m") == 1
    assert economics.break_even_reuses("anthropic", "1h") == 2
    assert economics.break_even_reuses("openai", "30m") == 1


def test_when_it_pays_and_when_it_bites():
    run = lambda name, ttl="5m", provider="anthropic": economics.simulate(provider, 8000, economics.SCENARIOS[name][0], ttl, economics.SCENARIOS[name][1])
    assert run("Support chatbot: 20 turns, 1 minute apart")["verdict"] == "Pays"
    assert run("One-off job: a single call")["verdict"] == "Bites"
    assert run("Sparse traffic: 6 calls, 10 minutes apart")["verdict"] == "Bites"
    assert run("Sparse traffic: 6 calls, 10 minutes apart", "1h")["verdict"] == "Pays"
    assert run("Steady but spaced: 6 calls, 3 minutes apart", "1h")["cached"] > run("Steady but spaced: 6 calls, 3 minutes apart", "5m")["cached"]
    assert run("Timestamp at the start: 10 calls, prefix changes every call")["verdict"] == "Bites"
