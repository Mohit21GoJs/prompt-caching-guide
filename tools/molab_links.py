#!/usr/bin/env python3
"""Generate the molab links table from the files in lessons/.

The README table is generated, never hand-edited, so a new lesson cannot be missing
a link and a renamed lesson cannot leave a dead one.

  python tools/molab_links.py --write README.md      rewrite the table in place
  python tools/molab_links.py --check README.md      exit 1 if the table is out of date
  python tools/molab_links.py --ref <commit> --print pinned links for a release

--ref defaults to "main", which always shows the latest push. A commit hash (or a tag)
shows exactly that version, so a release can publish links that never change.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPO = "Mohit21GoJs/prompt-caching-guide"
BADGE = "https://marimo.io/molab-shield.svg"
START, END = "<!-- molab-links:start -->", "<!-- molab-links:end -->"
LESSON = re.compile(r"^(\d\d)_(anthropic|openai)_(.+)\.py$")
PROVIDERS = (("anthropic", "Anthropic"), ("openai", "OpenAI"))


def lessons(root: Path = ROOT) -> dict[tuple[str, str], dict[str, str]]:
    """{(number, topic): {provider: filename}} for every lesson file, in order."""
    found: dict[tuple[str, str], dict[str, str]] = {}
    for path in sorted((root / "lessons").glob("[0-9][0-9]_*.py")):
        match = LESSON.match(path.name)
        if match:
            number, provider, topic = match.groups()
            found.setdefault((number, topic), {})[provider] = path.name
    return found


def url(repo: str, ref: str, filename: str) -> str:
    return f"https://molab.marimo.io/github/{repo}/blob/{ref}/lessons/{filename}/wasm"


def table(repo: str = DEFAULT_REPO, ref: str = "main", root: Path = ROOT) -> str:
    rows = ["| # | Lesson | Anthropic | OpenAI |", "|---|--------|-----------|--------|"]
    for (number, topic), files in lessons(root).items():
        title = topic.replace("_", " ").capitalize()
        cells = []
        for provider, label in PROVIDERS:
            name = files.get(provider)
            cells.append(f"[![Open {label} lesson {number} in molab]({BADGE})]({url(repo, ref, name)})" if name else "")
        rows.append(f"| {int(number)} | {title} | {cells[0]} | {cells[1]} |")
    return "\n".join(rows)


def render_block(repo: str, ref: str, root: Path = ROOT) -> str:
    return f"{START}\n{table(repo, ref, root)}\n{END}"


def replace_block(text: str, block: str) -> str:
    if START not in text or END not in text:
        raise SystemExit(f"README is missing the {START} and {END} markers")
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    return head + block + tail


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--ref", default="main")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", metavar="README")
    mode.add_argument("--check", metavar="README")
    mode.add_argument("--print", action="store_true")
    args = parser.parse_args()
    if args.print:
        print(f"Open each lesson in your browser, pinned to this release ({args.ref[:12]}):\n\n{table(args.repo, args.ref)}")
        return 0
    path = Path(args.write or args.check)
    current = path.read_text()
    updated = replace_block(current, render_block(args.repo, args.ref))
    if args.check:
        if current != updated:
            print(f"{path} is out of date. Run: python tools/molab_links.py --write {path}", file=sys.stderr)
            return 1
        return 0
    path.write_text(updated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
