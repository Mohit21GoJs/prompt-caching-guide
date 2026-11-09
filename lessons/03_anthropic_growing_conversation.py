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
        # Lesson 3 (Anthropic): a conversation that keeps growing

        In a chat or an agent loop, every call resends the whole conversation plus one new
        message. That is the best case for caching: each call can **read** everything from the
        previous call and only **write** the new part.

        With one top-level `cache_control` field, Anthropic moves the cache mark to the end of
        the request on every call. You do not manage breakpoints yourself.

        The recording starts with the handbook already cached, so its turn 1 reads it. A live run
        starts cold, so your turn 1 writes the whole prefix and the rest follow the same pattern.
        """
    )
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
            mo.md(f"Live needs `ANTHROPIC_API_KEY` (found: **{guide.api_key_present('anthropic')}**)."),
        ]
    )
    return mode, turns


@app.cell
def _(mo):
    mo.md("## The request")
    return


@app.cell
def _():
    def build_request(model: str, prefix: str, messages: list) -> dict:
        return {
            "model": model,
            "max_tokens": 64,
            "cache_control": {"type": "ephemeral"},  # <- the only caching line: mark moves to the end each call
            "system": prefix,
            "messages": messages,  # grows by two items per turn
        }

    return (build_request,)


@app.cell
def _(guide, mo, mode, turns):
    run = mo.ui.run_button(
        label=f"Run {turns.value} live turns",
        disabled=mode.value != "live" or not guide.api_key_present("anthropic"),
    )
    run
    return (run,)


@app.cell
def _(build_request, guide, mo, mode, run, turns):
    usages = []
    badge = ""
    _note = ""
    if mode.value == "replay":
        _rec = guide.load_recording("anthropic", "multiturn")
        usages = [t["provider_usage"] for t in _rec["turns"]]
        badge = guide.label("replay", _rec)
    elif run.value:
        import anthropic

        _client = anthropic.Anthropic()
        _model = guide.model_for("anthropic")
        _prefix = guide.make_prefix()
        _messages = []
        try:
            for _i in range(1, turns.value + 1):
                _messages.append({"role": "user", "content": f"In one short sentence, what is rule {_i}?"})
                _response = _client.messages.create(**build_request(_model, _prefix, _messages))
                _text = "".join(b.text for b in _response.content if b.type == "text") or "OK"
                _messages.append({"role": "assistant", "content": _text})
                usages.append(_response.usage.model_dump(mode="json"))
            badge = guide.label("live", model=_model, sdk=anthropic.__version__)
        except Exception as _error:
            _note = f"The live call failed on turn {len(usages) + 1}: `{type(_error).__name__}`. Check the key, the model name and your network, or switch to Replay."
    else:
        _note = "Press the run button."
    mo.md(_note) if _note else None
    return badge, usages


@app.cell
def _(badge, guide, mo, usages):
    mo.stop(not usages)
    mo.md(f"_{badge}_\n\n" + guide.turns_table("anthropic", usages))
    return


@app.cell
def _(guide, mo, usages):
    mo.stop(not usages)
    mo.accordion({f"Raw usage, turn {_i}": mo.md(f"```json\n{guide.usage_json(_u)}\n```") for _i, _u in enumerate(usages, 1)})
    return


@app.cell
def _(guide, mo, usages):
    mo.stop(len(usages) < 2)
    _n = [guide.turn_numbers("anthropic", u) for u in usages]
    _later_reads = all(x["read"] > 0 for x in _n[1:])
    _growing = all(b["read"] >= a["read"] for a, b in zip(_n, _n[1:]))
    if _later_reads and _growing:
        _text = (
            f"**As expected.** Every turn after the first read from cache, and the read grew from {_n[0]['read']} "
            f"to {_n[-1]['read']} tokens. Each turn wrote only the new messages ({_n[-1]['write']} on the last turn)."
        )
    else:
        _text = (
            "**Not the clean pattern.** A turn read nothing or the read shrank. The usual causes are the prefix being "
            "below the model's minimum, more than five minutes between turns, or the conversation being edited. Run it again."
        )
    mo.callout(mo.md(_text), kind="info")
    return


@app.cell
def _(mo):
    mo.md(
        """
        ## What to take away

        - Cost per turn is roughly **new tokens at the write price + everything before at the read price**,
          not the whole conversation at the full price.
        - The pattern only holds while you **append**. If you edit, trim or summarize earlier messages,
          everything after the edit becomes a write again. Lesson 2 showed why.
        - Each hit refreshes the five-minute lifetime, so a steady conversation keeps its cache alive.

        Next: `03_openai_growing_conversation.py` shows the same conversation where caching is automatic.
        """
    )
    return


if __name__ == "__main__":
    app.run()
