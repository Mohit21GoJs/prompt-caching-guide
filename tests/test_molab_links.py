"""The molab links in the README are generated from lessons/. These tests keep them honest."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("molab_links", ROOT / "tools" / "molab_links.py")
molab_links = importlib.util.module_from_spec(spec)
spec.loader.exec_module(molab_links)

README = (ROOT / "README.md").read_text()
SHA = "7e46d4e61e5f1bb0156a8fc2916f181f4c3d284d"


def test_readme_table_is_up_to_date():
    expected = molab_links.replace_block(README, molab_links.render_block(molab_links.DEFAULT_REPO, "main"))
    assert README == expected, "run: uv run python tools/molab_links.py --write README.md"


def test_every_lesson_has_a_link_for_each_provider():
    found = molab_links.lessons()
    assert found, "no lessons found"
    for key, files in found.items():
        assert set(files) == {"anthropic", "openai"}, f"lesson {key} is missing a provider"
    table = molab_links.table()
    for files in found.values():
        for name in files.values():
            assert f"lessons/{name}/wasm" in table


def test_pinned_links_use_the_commit_and_never_main():
    pinned = molab_links.table(ref=SHA)
    assert f"/blob/{SHA}/lessons/" in pinned
    assert "/blob/main/" not in pinned


def test_urls_follow_the_molab_pattern():
    assert molab_links.url("o/r", "abc", "01_x.py") == "https://molab.marimo.io/github/o/r/blob/abc/lessons/01_x.py/wasm"
