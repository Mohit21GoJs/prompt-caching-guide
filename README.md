# Prompt caching guide

Learn prompt caching by running small [marimo](https://marimo.io) notebooks against Anthropic and OpenAI. Each lesson has one idea, one diagram, and the real request code. You see the provider's raw `usage` fields, unmodified.

Every lesson runs in two modes:

- **Replay** (default): shows real responses recorded from the providers. Needs no key and costs nothing.
- **Live**: sends two small requests with your own key and shows what comes back.

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

More lessons are planned: multi-turn, rewriting history, and a break-even lesson on when caching saves money and when it costs more.

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
