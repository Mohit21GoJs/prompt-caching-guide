# Prompt caching guide

Learn prompt caching by running small [marimo](https://marimo.io) notebooks against Anthropic and OpenAI. Each lesson has one idea, one diagram, and the real request code. You see the provider's raw `usage` fields, unmodified.

Lessons 1 to 3 and 5 run in two modes (lesson 4 is arithmetic only and needs no key):

- **Replay** (default): shows real responses recorded from the providers. Needs no key and costs nothing.
- **Live**: sends two small requests with your own key and shows what comes back.

## Try it in your browser

These open each lesson on [molab](https://molab.marimo.io) running in WebAssembly. Nothing to install.

| # | Lesson | Anthropic | OpenAI |
|---|--------|-----------|--------|
| 1 | Same prefix twice | [Anthropic](https://molab.marimo.io/github/Mohit21GoJs/prompt-caching-guide/blob/main/lessons/01_anthropic_cache_hit.py/wasm) | [OpenAI](https://molab.marimo.io/github/Mohit21GoJs/prompt-caching-guide/blob/main/lessons/01_openai_cache_hit.py/wasm) |
| 2 | What breaks a hit | [Anthropic](https://molab.marimo.io/github/Mohit21GoJs/prompt-caching-guide/blob/main/lessons/02_anthropic_what_breaks_a_hit.py/wasm) | [OpenAI](https://molab.marimo.io/github/Mohit21GoJs/prompt-caching-guide/blob/main/lessons/02_openai_what_breaks_a_hit.py/wasm) |
| 3 | A growing conversation | [Anthropic](https://molab.marimo.io/github/Mohit21GoJs/prompt-caching-guide/blob/main/lessons/03_anthropic_growing_conversation.py/wasm) | [OpenAI](https://molab.marimo.io/github/Mohit21GoJs/prompt-caching-guide/blob/main/lessons/03_openai_growing_conversation.py/wasm) |
| 4 | When caching pays and bites | [Anthropic](https://molab.marimo.io/github/Mohit21GoJs/prompt-caching-guide/blob/main/lessons/04_anthropic_break_even.py/wasm) | [OpenAI](https://molab.marimo.io/github/Mohit21GoJs/prompt-caching-guide/blob/main/lessons/04_openai_break_even.py/wasm) |
| 5 | Rewriting history | [Anthropic](https://molab.marimo.io/github/Mohit21GoJs/prompt-caching-guide/blob/main/lessons/05_anthropic_rewriting_history.py/wasm) | [OpenAI](https://molab.marimo.io/github/Mohit21GoJs/prompt-caching-guide/blob/main/lessons/05_openai_rewriting_history.py/wasm) |

In the browser a lesson runs in **replay** mode with the recorded provider responses. Live mode needs an API key in an environment variable or `.env`, which a browser page does not have, so the run button stays disabled there. To run live, use the local setup below.

Opened and checked on molab so far: lesson 1 (Anthropic) and lesson 4 (Anthropic). The other lessons use the same helper modules and recordings but have not been opened there yet. molab is a third-party service and may change how it handles these links.

## Run it locally

You need [uv](https://docs.astral.sh/uv/).

```bash
git clone <this repo>
cd prompt-caching-guide
uv sync
uv run marimo edit lessons/01_anthropic_cache_hit.py
```

Use `marimo run` instead of `marimo edit` to open a lesson as a plain app without the code editor.

### Live mode

```bash
cp .env.example .env     # then paste a key for the provider you want
uv run marimo edit lessons/01_openai_cache_hit.py
```

Switch **Run mode** to Live and press the run button. Each live lesson sends two requests of about 2,500 prompt tokens and asks for at most 64 output tokens, which costs a fraction of a cent. The key is read from your environment or `.env`. It is never typed into the page, saved, or printed. Use a key with a spend cap.

The model defaults to the one the recordings were captured with. Override it with `ANTHROPIC_MODEL` or `OPENAI_MODEL` in `.env`. Model names, prices and cache rules change, so if a live call fails, check the model name first.

## Lessons

| # | Lesson | What it shows |
|---|--------|---------------|
| 1 | `01_anthropic_cache_hit.py` | Opt in with `cache_control`. Call 1 writes, call 2 reads. |
| 1 | `01_openai_cache_hit.py` | Caching is automatic. Call 2 reports `cached_tokens`. |
| 2 | `02_anthropic_what_breaks_a_hit.py` | Change the question, one byte of the handbook, or the tool order. Which keeps the hit? |
| 2 | `02_openai_what_breaks_a_hit.py` | The same three changes where caching is automatic. |
| 3 | `03_anthropic_growing_conversation.py` | A chat that grows each turn: each call reads the past and writes only the new part. |
| 3 | `03_openai_growing_conversation.py` | The same conversation with automatic caching and `cached_tokens` in steps. |
| 4 | `04_anthropic_break_even.py` | When caching pays and when it costs more: real calls costed, break-even reuses, seven usage patterns, 5-minute vs 1-hour cache. |
| 4 | `04_openai_break_even.py` | The same experiments with OpenAI's prices. Paste your own usage JSON to cost it. |
| 5 | `05_anthropic_rewriting_history.py` | Edit, drop or summarize old messages. One rewrite recorded (+42% cost); three more live. |
| 5 | `05_openai_rewriting_history.py` | The same rewrites where caching is automatic (recorded rewrite: +71% cost). |

Ideas for later: other vendors (Gemini, Bedrock), a prompt linter for unstable prefixes, and a debugging flowchart for "both cache fields are 0".

## What has been verified

| | Replay | Live |
|---|---|---|
| Anthropic lessons 1, 2, 3, 5 | tested on every run (`uv run pytest`) | run on 2026-11-10 with `claude-sonnet-5-5`; every result matched what the lesson predicts |
| OpenAI lessons 1, 2, 3, 5 | tested on every run | **not yet run**: the one live check attempt hit an expired key |
| Lesson 4 (arithmetic) | tested against the costs stored with the real captures | no live mode |

A live OpenAI run was reported working by the author for lesson 1 before these checks, but it was not repeated here.

## Prices

Lesson 4 uses a dated price snapshot in `lessons/economics.py` (checked 2026-10-19, with source links). It warns when the prices are over 60 days old. Prices and cache rules change often, so recheck them before trusting a dollar figure. The tests check that the calculator reproduces the cost estimates stored with the real captures.

## How to read a result

Every result carries a badge. **REPLAY** means a recording from the date shown, not your run. **LIVE** means your request just now. A zero on call 2 is not always a bug. The lesson explains the likely causes: prefix too short, prefix changed, TTL expired, or best-effort routing on OpenAI.

## Check the repo

```bash
uv run pytest -q          # runs every lesson in replay mode with no key and no network
uv run marimo check lessons/
```

## Layout

```
lessons/        one notebook per lesson and provider, plus guide.py (small shared helpers)
recordings/     trimmed real provider responses, one JSON file each
diagrams/       SVG diagrams
tests/          replay smoke tests
```

The recordings were captured on 2026-10-22 and the prompt text is synthetic. They contain no keys or customer data.
