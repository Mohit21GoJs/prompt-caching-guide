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
    # Lesson 2 (OpenAI): what breaks a cache hit

    A hit needs the **start** of the request to match an earlier request exactly. OpenAI
    caches automatically, in order: tools, then your input items from the first to the last.
    There is no mark. The hit covers the longest matching start.

    So a change near the end keeps most of the hit. A change near the start breaks nearly all
    of it. Pick a change, then compare.
    """)
    return


@app.cell
def _(guide, mo):
    mode = mo.ui.radio(
        {"Replay (free, no key)": "replay", "Live (your key, two small requests)": "live"},
        value="Replay (free, no key)",
        label="Run mode",
    )
    change = mo.ui.dropdown(
        {label: key for key, label in guide.CHANGES.items()},
        value=guide.CHANGES["handbook"],
        label="Change between call 1 and call 2",
    )
    mo.vstack(
        [
            mo.hstack([mode, change], justify="start", gap=3),
            mo.md(f"Live needs `OPENAI_API_KEY` (found: **{guide.api_key_present('openai')}**)."),
        ]
    )
    return change, mode


@app.cell
def _(mo):
    mo.md("""
    ## The request, and the three changes
    """)
    return


@app.cell
def _():
    TOOLS = [
        {
            "type": "function",
            "name": "lookup_customer",
            "description": "Look up a fabricated customer record.",
            "parameters": {"type": "object", "properties": {"customer_id": {"type": "string"}}},
        },
        {
            "type": "function",
            "name": "lookup_order",
            "description": "Look up a fabricated order.",
            "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}},
        },
    ]


    def build_request(model: str, prefix: str, tools: list, question: str, cache_key: str) -> dict:
        return {
            "model": model,
            "max_output_tokens": 64,
            "prompt_cache_key": cache_key,  # same on both calls, so they route to the same cache
            "tools": tools,  # part of the matched start
            "input": [
                {"role": "developer", "content": prefix},  # long and stable
                {"role": "user", "content": question},  # changes last
            ],
        }


    CHANGE_FUNCTIONS = {
        "question": lambda p, t, q: (p, t, "A different question: what is rule 2?"),
        "handbook": lambda p, t, q: (p.replace("Rule 1:", "Rule 1!", 1), t, q),
        "tools": lambda p, t, q: (p, list(reversed(t)), q),
    }
    return CHANGE_FUNCTIONS, TOOLS, build_request


@app.cell
def _(guide, mo, mode):
    run = mo.ui.run_button(
        label="Run two live requests",
        disabled=mode.value != "live" or not guide.api_key_present("openai"),
    )
    run
    return (run,)


@app.cell
def _(CHANGE_FUNCTIONS, TOOLS, build_request, change, guide, mo, mode, run):
    runs = []
    _note = ""
    if mode.value == "replay":
        _base = guide.load_recording("openai", "cold")
        _changed = guide.load_recording("openai", {"question": "suffix"}.get(change.value, change.value))
        runs.append(("Call 1: baseline", _base["provider_usage"], guide.label("replay", _base)))
        runs.append(("Call 2: after the change", _changed["provider_usage"], guide.label("replay", _changed)))
    elif run.value:
        import openai

        _client = openai.OpenAI()
        _model = guide.model_for("openai")
        _prefix = guide.make_prefix()
        _question = "In one short sentence, what is rule 1?"
        _key = "lesson-2-" + _prefix.split("Salt ")[1][:12]
        _p2, _t2, _q2 = CHANGE_FUNCTIONS[change.value](_prefix, TOOLS, _question)
        try:
            _first = _client.responses.create(**build_request(_model, _prefix, TOOLS, _question, _key))
            _second = _client.responses.create(**build_request(_model, _p2, _t2, _q2, _key))
            _badge = guide.label("live", model=_model, sdk=openai.__version__)
            runs.append(("Call 1: baseline", _first.usage.model_dump(mode="json"), _badge))
            runs.append(("Call 2: after the change", _second.usage.model_dump(mode="json"), _badge))
        except Exception as _error:
            _note = guide.explain_error(_error, "openai")
    else:
        _note = "Press **Run two live requests**."
    mo.md(_note) if _note else None
    return (runs,)


@app.cell
def _(guide, mo, runs):
    mo.stop(not runs)
    _blocks = [
        mo.md(f"**{_title}**\n\n_{_badge}_\n\n```json\n{guide.usage_json(_usage)}\n```")
        for _title, _usage, _badge in runs
    ]
    mo.hstack(_blocks, align="start")
    return


@app.cell
def _(change, guide, mo, runs):
    mo.stop(len(runs) < 2)
    _usage = runs[1][1]
    _read = guide.cache_read("openai", _usage)
    _total = _usage.get("input_tokens", 0)
    _expect_hit = change.value == "question"
    if _read and _expect_hit:
        _text = f"**Mostly a hit, as expected.** Call 2 read **{_read}** of **{_total}** input tokens. Only the question changed, at the end."
    elif not _read and not _expect_hit:
        _text = (
            f"**Miss, as expected.** Call 2 read **0** of **{_total}** input tokens. "
            "The change is near the start, so almost nothing matched and the whole prompt was processed again."
        )
    else:
        _text = (
            f"**Not what the lesson predicts** (read {_read} of {_total}). "
            "OpenAI caching is best-effort and routing can differ between calls. Run it again."
        )
    mo.callout(mo.md(_text), kind="info")
    return


@app.cell
def _(guide, mo):
    _rows = []
    for _key, _label in guide.CHANGES.items():
        _name = "suffix" if _key == "question" else _key
        _rec = guide.load_recording("openai", _name)
        _u = _rec["provider_usage"]
        _read = guide.cache_read("openai", _u)
        _rows.append(f"| {_label} | {_read} | {_u.get('input_tokens', 0)} | {'hit' if _read else 'miss'} |")
    mo.md(
        "## All three, recorded\n\n"
        f"_Recorded {_rec['captured_at']} on {_rec['model']}. Not your run._\n\n"
        "| Change | `cached_tokens` | `input_tokens` | Result |\n|---|---|---|---|\n"
        + "\n".join(_rows)
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## The rule to take away

    Put what stays the same first and what changes last. Anything that changes near the start,
    including tool definitions and a timestamp or ID in the system text, throws away the hit.
    Unlike Anthropic, a miss here costs no extra write fee on older models, but you lose the
    discount on every token after the change. Newer models can also report `cache_write_tokens`.

    Compare with `02_anthropic_what_breaks_a_hit.py`, where the mark is explicit.
    """)
    return


if __name__ == "__main__":
    app.run()
