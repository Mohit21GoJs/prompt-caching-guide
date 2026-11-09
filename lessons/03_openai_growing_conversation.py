import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import guide

    return guide, mo


@app.cell
def _(mo):
    mo.md("""
    # Lesson 3 (OpenAI): a conversation that keeps growing

    In a chat or an agent loop, every call resends the whole conversation plus one new
    message. That is the best case for caching: each call can **read** everything from the
    previous call and only **write** the new part.

    OpenAI caches automatically, so there is nothing to mark. Keep the conversation in order,
    append new items at the end, and send the same `prompt_cache_key` each time.

    The recording starts with the handbook already cached, so its turn 1 reads it. A live run
    starts cold, so your turn 1 reads little and the following turns read more. OpenAI reports
    hits in chunks, so the read grows in steps, not by exact token counts.
    """)
    return


@app.cell
def _(guide, mo):
    mode = mo.ui.radio(
        {"Replay (free, no key)": "replay", "Live (your key, several small requests)": "live"},
        value="Replay (free, no key)",
        label="Run mode",
    )
    turns = mo.ui.slider(2, 5, value=4, label="Live turns")
    mo.vstack(
        [
            mo.hstack([mode, turns], justify="start", gap=3),
            mo.md(f"Live needs `OPENAI_API_KEY` (found: **{guide.api_key_present('openai')}**)."),
        ]
    )
    return mode, turns


@app.cell
def _(mo):
    mo.md("""
    ## The request
    """)
    return


@app.function
def build_request(model: str, prefix: str, items: list, cache_key: str) -> dict:
    return {
        "model": model,
        "max_output_tokens": 64,
        "prompt_cache_key": cache_key,  # <- the only caching hint, same on every turn
        "input": [{"role": "developer", "content": prefix}, *items],  # grows by two items per turn
    }


@app.cell
def _(guide, mo, mode, turns):
    run = mo.ui.run_button(
        label=f"Run {turns.value} live turns",
        disabled=mode.value != "live" or not guide.api_key_present("openai"),
    )
    run
    return (run,)


@app.cell
def _(guide, mo, mode, run, turns):
    usages = []
    badge = ""
    _note = ""
    if mode.value == "replay":
        _rec = guide.load_recording("openai", "multiturn")
        usages = [t["provider_usage"] for t in _rec["turns"]]
        badge = guide.label("replay", _rec)
    elif run.value:
        import openai

        _client = openai.OpenAI()
        _model = guide.model_for("openai")
        _prefix = guide.make_prefix()
        _messages = []
        _key = "lesson-3-" + _prefix.split("Salt ")[1][:12]
        try:
            for _i in range(1, turns.value + 1):
                _messages.append({"role": "user", "content": f"In one short sentence, what is rule {_i}?"})
                _response = _client.responses.create(**build_request(_model, _prefix, _messages, _key))
                _messages.append({"role": "assistant", "content": _response.output_text or "OK"})
                usages.append(_response.usage.model_dump(mode="json"))
            badge = guide.label("live", model=_model, sdk=openai.__version__)
        except Exception as _error:
            _note = guide.explain_error(_error, "openai", f" on turn {len(usages) + 1}")
    else:
        _note = "Press the run button."
    mo.md(_note) if _note else None
    return badge, usages


@app.cell
def _(badge, guide, mo, usages):
    mo.stop(not usages)
    mo.md(f"_{badge}_\n\n" + guide.turns_table("openai", usages))
    return


@app.cell
def _(guide, mo, usages):
    mo.stop(not usages)
    mo.accordion({f"Raw usage, turn {_i}": mo.md(f"```json\n{guide.usage_json(_u)}\n```") for _i, _u in enumerate(usages, 1)})
    return


@app.cell
def _(guide, mo, usages):
    mo.stop(len(usages) < 2)
    _n = [guide.turn_numbers("openai", u) for u in usages]
    _later_reads = all(x["read"] > 0 for x in _n[1:])
    _growing = all(b["read"] >= a["read"] for a, b in zip(_n, _n[1:]))
    if _later_reads and _growing:
        _text = (
            f"**As expected.** Every turn after the first read from cache, and the read grew from {_n[0]['read']} "
            f"to {_n[-1]['read']} tokens, out of {_n[-1]['total']} input tokens on the last turn."
        )
    else:
        _text = (
            "**Not the clean pattern.** A turn read nothing or the read shrank. OpenAI caching is best-effort: the prefix may be "
            "under 1,024 tokens, calls may be routed differently, or the conversation was edited. Run it again."
        )
    mo.callout(mo.md(_text), kind="info")
    return


@app.cell
def _(mo):
    mo.md("""
    ## What to take away

    - Each call is billed as **uncached input at full price + cached input at the discount**. The
      cached share is what you see in the bar, and it stays high as long as you only append.
    - The pattern breaks if you edit, trim or reorder earlier items. Lesson 2 showed why.
    - Caches expire after a period of inactivity, so a long pause between turns resets the pattern.

    Compare with `03_anthropic_growing_conversation.py`, where one field moves the mark.
    """)
    return


if __name__ == "__main__":
    app.run()
