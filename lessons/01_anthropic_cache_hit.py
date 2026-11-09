import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import guide

    return guide, mo


@app.cell
def _(guide, mo):
    mo.vstack(
        [
            mo.md(
                """
                # Lesson 1 (Anthropic): send the same prefix twice

                Anthropic caches only what you ask it to cache. You mark the end of the
                reusable part with `cache_control`. The first call **writes** the cache.
                The second call, with the same prefix, **reads** it.

                Replay needs no key and costs nothing. Live sends two real requests.
                """
            ),
            mo.Html(guide.diagram("prefix-anatomy")),
        ]
    )
    return


@app.cell
def _(guide, mo):
    mode = mo.ui.radio(
        {"Replay (free, no key)": "replay", "Live (your key, two small requests)": "live"},
        value="Replay (free, no key)",
        label="Run mode",
    )
    mo.vstack(
        [
            mode,
            mo.md(
                "Live needs `ANTHROPIC_API_KEY` in your environment or in `.env` "
                f"(found: **{guide.api_key_present('anthropic')}**)."
            ),
        ]
    )
    return (mode,)


@app.cell
def _(mo):
    mo.md("""
    ## The request

    The one line that asks for caching is marked below.
    """)
    return


@app.function
def build_request(model: str, prefix: str, question: str) -> dict:
    return {
        "model": model,
        "max_tokens": 64,
        "system": [
            {
                "type": "text",
                "text": prefix,
                "cache_control": {"type": "ephemeral"},  # <- ask Anthropic to cache up to here
            }
        ],
        "messages": [{"role": "user", "content": question}],
    }


@app.cell
def _(guide, mo, mode):
    run = mo.ui.run_button(label="Run two live requests", disabled=mode.value != "live" or not guide.api_key_present("anthropic"))
    mo.hstack([run, mo.md("Each request sends about 2,500 prompt tokens and asks for at most 64 output tokens.")], justify="start")
    return (run,)


@app.cell
def _(guide, mo, mode, run):
    runs = []
    _note = ""
    if mode.value == "replay":
        for _step in ("cold", "exact"):
            _rec = guide.load_recording("anthropic", _step)
            runs.append((_step, _rec["provider_usage"], guide.label("replay", _rec)))
    elif run.value:
        import anthropic

        _client = anthropic.Anthropic()
        _model = guide.model_for("anthropic")
        _prefix = guide.make_prefix()
        _question = "In one short sentence, what is rule 1?"
        try:
            for _step in ("cold", "exact"):
                _response = _client.messages.create(**build_request(_model, _prefix, _question))
                runs.append((_step, _response.usage.model_dump(mode="json"), guide.label("live", model=_model, sdk=anthropic.__version__)))
        except Exception as _error:  # show a readable reason and a way out
            _note = f"The live call failed: `{type(_error).__name__}`. Check the key, the model name and your network, or switch to Replay."
    else:
        _note = "Press **Run two live requests**."
    mo.md(_note) if _note else None
    return (runs,)


@app.cell
def _(guide, mo, runs):
    mo.stop(not runs)
    _blocks = []
    for _step, _usage, _badge in runs:
        _title = "Call 1: first time (cold)" if _step == "cold" else "Call 2: same prefix again"
        _blocks.append(mo.md(f"**{_title}**\n\n_{_badge}_\n\n```json\n{guide.usage_json(_usage)}\n```"))
    mo.hstack(_blocks, align="start")
    return


@app.cell
def _(mo, runs):
    mo.stop(len(runs) < 2)
    _first, _second = runs[0][1], runs[1][1]
    _wrote = _first.get("cache_creation_input_tokens", 0)
    _read = _second.get("cache_read_input_tokens", 0)
    if _wrote and _read:
        _verdict = (
            f"Call 1 wrote **{_wrote}** tokens (`cache_creation_input_tokens`). "
            f"Call 2 read **{_read}** tokens (`cache_read_input_tokens`). That read is the saving."
        )
    elif not _wrote:
        _verdict = (
            "Call 1 wrote nothing. The prefix is probably below the model's minimum cacheable length. "
            "Nothing is cached and the API returns no error."
        )
    else:
        _verdict = (
            "Call 1 wrote but call 2 read nothing. Common causes: the prefix changed between calls, "
            "more than five minutes passed, or the request landed on a different cache."
        )
    mo.callout(mo.md(_verdict), kind="info")
    return


@app.cell
def _(mo):
    mo.md("""
    ## What to try next

    - Break the hit: edit the first line of the prefix between the two calls and run live again.
    - Delete the `cache_control` line and confirm nothing is written.
    - Next: `01_openai_cache_hit.py` does the same experiment where caching is automatic.
    """)
    return


if __name__ == "__main__":
    app.run()
