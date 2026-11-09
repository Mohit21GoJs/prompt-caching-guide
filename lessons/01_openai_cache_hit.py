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
                # Lesson 1 (OpenAI): send the same prefix twice

                OpenAI caches automatically. You do not mark anything: any prompt over
                1,024 tokens whose **start** matches an earlier request can be served from
                cache. A stable `prompt_cache_key` helps similar requests land on the same
                cache. The second call reports the hit in `input_tokens_details.cached_tokens`.

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
                "Live needs `OPENAI_API_KEY` in your environment or in `.env` "
                f"(found: **{guide.api_key_present('openai')}**)."
            ),
        ]
    )
    return (mode,)


@app.cell
def _(mo):
    mo.md("## The request\n\nNothing in it asks for caching. The only caching hint is `prompt_cache_key`.")
    return


@app.cell
def _():
    def build_request(model: str, prefix: str, question: str, cache_key: str) -> dict:
        return {
            "model": model,
            "max_output_tokens": 64,
            "prompt_cache_key": cache_key,  # <- optional routing hint, keep it the same across calls
            "input": [
                {"role": "developer", "content": prefix},  # the long, stable part goes first
                {"role": "user", "content": question},  # the part that changes goes last
            ],
        }

    return (build_request,)


@app.cell
def _(guide, mo, mode):
    run = mo.ui.run_button(label="Run two live requests", disabled=mode.value != "live" or not guide.api_key_present("openai"))
    mo.hstack([run, mo.md("Each request sends about 2,500 prompt tokens and asks for at most 64 output tokens.")], justify="start")
    return (run,)


@app.cell
def _(build_request, guide, mo, mode, run):
    runs = []
    _note = ""
    if mode.value == "replay":
        for _step in ("cold", "exact"):
            _rec = guide.load_recording("openai", _step)
            runs.append((_step, _rec["provider_usage"], guide.label("replay", _rec)))
    elif run.value:
        import openai

        _client = openai.OpenAI()
        _model = guide.model_for("openai")
        _prefix = guide.make_prefix()
        _question = "In one short sentence, what is rule 1?"
        _cache_key = "lesson-1-" + _prefix.split("Salt ")[1][:12]
        try:
            for _step in ("cold", "exact"):
                _response = _client.responses.create(**build_request(_model, _prefix, _question, _cache_key))
                runs.append((_step, _response.usage.model_dump(mode="json"), guide.label("live", model=_model, sdk=openai.__version__)))
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
    _read = (_second.get("input_tokens_details") or {}).get("cached_tokens", 0)
    _seen = (_first.get("input_tokens_details") or {}).get("cached_tokens", 0)
    _total = _second.get("input_tokens", 0)
    if _read:
        _verdict = (
            f"Call 2 read **{_read}** of its **{_total}** input tokens from cache "
            f"(`input_tokens_details.cached_tokens`). Call 1 read **{_seen}**. That read is the saving."
        )
    else:
        _verdict = (
            "Call 2 read nothing. Caching is automatic and best-effort: the prefix may be under 1,024 tokens, "
            "the two calls may have been routed to different machines, or the prefix changed. "
            "This is normal sometimes. Try again with the same `prompt_cache_key`."
        )
    mo.callout(mo.md(_verdict), kind="info")
    return


@app.cell
def _(mo):
    mo.md(
        """
        ## What to try next

        - Break the hit: edit the first line of the prefix between the two calls and run live again.
        - Put the changing question first and the handbook last. The hit disappears, because only a matching start is cached.
        - Compare with `01_anthropic_cache_hit.py`, where you must opt in with `cache_control`.
        """
    )
    return


if __name__ == "__main__":
    app.run()
