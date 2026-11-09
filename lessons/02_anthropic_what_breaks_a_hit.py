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
    mo.md(
        """
        # Lesson 2 (Anthropic): what breaks a cache hit

        A hit needs the **start** of the request to match an earlier request exactly. Anthropic
        builds the request in this order: tools, then system, then messages. The cache covers
        everything up to your `cache_control` mark.

        So a change near the end keeps the hit. A change before the mark breaks it, and you pay
        to write the cache again. Pick a change, then compare.
        """
    )
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
            mo.md(f"Live needs `ANTHROPIC_API_KEY` (found: **{guide.api_key_present('anthropic')}**)."),
        ]
    )
    return change, mode


@app.cell
def _(mo):
    mo.md("## The request, and the three changes")
    return


@app.cell
def _():
    TOOLS = [
        {
            "name": "lookup_customer",
            "description": "Look up a fabricated customer record.",
            "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}}},
        },
        {
            "name": "lookup_order",
            "description": "Look up a fabricated order.",
            "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}},
        },
    ]


    def build_request(model: str, prefix: str, tools: list, question: str) -> dict:
        return {
            "model": model,
            "max_tokens": 64,
            "tools": tools,  # part of the cached prefix
            "system": [
                {"type": "text", "text": prefix, "cache_control": {"type": "ephemeral"}}  # cached up to here
            ],
            "messages": [{"role": "user", "content": question}],  # after the mark, free to change
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
        disabled=mode.value != "live" or not guide.api_key_present("anthropic"),
    )
    run
    return (run,)


@app.cell
def _(CHANGE_FUNCTIONS, TOOLS, build_request, change, guide, mo, mode, run):
    runs = []
    _note = ""
    if mode.value == "replay":
        _base = guide.load_recording("anthropic", "cold")
        _changed = guide.load_recording("anthropic", {"question": "suffix"}.get(change.value, change.value))
        runs.append(("Call 1: baseline", _base["provider_usage"], guide.label("replay", _base)))
        runs.append(("Call 2: after the change", _changed["provider_usage"], guide.label("replay", _changed)))
    elif run.value:
        import anthropic

        _client = anthropic.Anthropic()
        _model = guide.model_for("anthropic")
        _prefix = guide.make_prefix()
        _question = "In one short sentence, what is rule 1?"
        _p2, _t2, _q2 = CHANGE_FUNCTIONS[change.value](_prefix, TOOLS, _question)
        try:
            _first = _client.messages.create(**build_request(_model, _prefix, TOOLS, _question))
            _second = _client.messages.create(**build_request(_model, _p2, _t2, _q2))
            _badge = guide.label("live", model=_model, sdk=anthropic.__version__)
            runs.append(("Call 1: baseline", _first.usage.model_dump(mode="json"), _badge))
            runs.append(("Call 2: after the change", _second.usage.model_dump(mode="json"), _badge))
        except Exception as _error:
            _note = guide.explain_error(_error, "anthropic")
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
    _read = guide.cache_read("anthropic", runs[1][1])
    _wrote = runs[1][1].get("cache_creation_input_tokens", 0)
    _expect_hit = change.value == "question"
    if _read and _expect_hit:
        _text = f"**Hit, as expected.** Call 2 read **{_read}** tokens. Only the question changed, and it sits after the cache mark."
    elif not _read and not _expect_hit:
        _text = (
            f"**Miss, as expected.** Call 2 read **0** and wrote **{_wrote}** tokens again. "
            "The change is before the cache mark, so the start no longer matches and you paid the write price a second time."
        )
    else:
        _text = (
            f"**Not what the lesson predicts** (read {_read}, wrote {_wrote}). "
            "Another request may have warmed or cooled the cache, or more than five minutes passed. Run it again."
        )
    mo.callout(mo.md(_text), kind="info")
    return


@app.cell
def _(guide, mo):
    _rows = []
    for _key, _label in guide.CHANGES.items():
        _name = "suffix" if _key == "question" else _key
        _rec = guide.load_recording("anthropic", _name)
        _u = _rec["provider_usage"]
        _rows.append(
            f"| {_label} | {_u.get('cache_read_input_tokens', 0)} | {_u.get('cache_creation_input_tokens', 0)} | "
            f"{'hit' if _u.get('cache_read_input_tokens', 0) else 'miss'} |"
        )
    mo.md(
        "## All three, recorded\n\n"
        f"_Recorded {_rec['captured_at']} on {_rec['model']}. Not your run._\n\n"
        "| Change | `cache_read_input_tokens` | `cache_creation_input_tokens` | Result |\n|---|---|---|---|\n"
        + "\n".join(_rows)
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
        ## The rule to take away

        Put what stays the same first and what changes last. Anything that changes before the
        cache mark, including tool definitions and a timestamp or ID inside the system text,
        turns every request into a fresh write.

        Next: `02_openai_what_breaks_a_hit.py` runs the same three changes where caching is automatic.
        """
    )
    return


if __name__ == "__main__":
    app.run()
