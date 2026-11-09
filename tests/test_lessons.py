"""Every lesson must run top to bottom in replay mode with no key and no network."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LESSONS = sorted((ROOT / "lessons").glob("[0-9][0-9]_*.py"))


@pytest.mark.parametrize("lesson", LESSONS, ids=lambda p: p.name)
def test_lesson_runs_in_replay(lesson, tmp_path):
    out = tmp_path / "out.html"
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}  # no API keys in the environment
    result = subprocess.run(
        [sys.executable, "-m", "marimo", "export", "html", str(lesson), "-o", str(out), "--no-include-code"],
        capture_output=True, text=True, env={**env, "PYTHONPATH": ":".join(sys.path)}, cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
    html = out.read_text()
    assert "REPLAY" in html
    assert "cache_read" in html or "cached_tokens" in html


@pytest.mark.parametrize("path", sorted((ROOT / "recordings").glob("*.json")), ids=lambda p: p.name)
def test_recordings_are_trimmed_and_clean(path):
    data = json.loads(path.read_text())
    assert {"provider", "model", "sdk_version", "captured_at"} <= data.keys()
    assert "provider_usage" in data or all("provider_usage" in t for t in data["turns"])
    text = path.read_text().lower()
    assert "api_key" not in text and "bearer" not in text and "sk-" not in text
    assert path.stat().st_size < (9000 if "turns" in data else 4000)
