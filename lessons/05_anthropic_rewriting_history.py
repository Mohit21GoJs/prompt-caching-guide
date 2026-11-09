import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import economics
    import guide
    import marimo as mo

    PROVIDER = "anthropic"
    return PROVIDER, economics, guide, mo


@app.cell
def _(mo):
    mo.md(
        """
        # Lesson 5 (Anthropic): rewriting history

        Lesson 3 appended to a conversation, which is the cheap case. Real apps also **change** old
        messages: they fix a typo, drop the oldest turns to stay inside a context window, or swap old
        turns for a summary.

        Each of those changes text near the start of the conversation. A cache hit needs an exact match
        from the start (lesson 2), so everything after the first changed message is processed and
        written again, at the write price.
        """
    )
    return


@app.cell
def _(PROVIDER, economics, guide, mo):
    _model = guide.load_recording(PROVIDER, "rewrite")["model"]
    _app = guide.load_recording(PROVIDER, "multiturn")
    _rw = guide.load_recording(PROVIDER, "rewrite")
    _a_use = _app["turns"][-1]["provider_usage"]
    _r_use = _rw["provider_usage"]
    _a, _r = guide.turn_numbers(PROVIDER, _a_use), guide.turn_numbers(PROVIDER, _r_use)
    _ca, _cr = economics.cost_of_usage(PROVIDER, _a_use), economics.cost_of_usage(PROVIDER, _r_use)
    mo.md(
        f"""
        ## Part A: one real rewrite, recorded

        _REPLAY: recorded {_rw['captured_at']} on {_model}. Costs use the lesson 4 price snapshot._

        Same conversation, same length ({_rw['messages_sent']} messages). In the second row, the **first** user message was edited.

        | Call | Read from cache | Written to cache | Normal input | Cost |
        |---|---|---|---|---|
        | Append only (last turn of lesson 3) | {_a['read']} | {_a['write']} | {_a['plain']} | ${_ca:.6f} |
        | After editing the first message | {_r['read']} | {_r['write']} | {_r['plain']} | ${_cr:.6f} |

        The read fell by **{_a['read'] - _r['read']}** tokens and the write grew by **{_r['write'] - _a['write']}**.
        The edit cost **{(_cr / _ca - 1):+.0%}** more for the same question.
        The {_r['read']} tokens still read are the tools and the handbook, which sit before the conversation and did not change.
        """
    )
    return


@app.cell
def _(guide, mo):
    mode = mo.ui.radio(
        {"Replay (free, no key)": "replay", "Live (your key, five small requests)": "live"},
        value="Replay (free, no key)",
        label="Run mode",
    )
    edit = mo.ui.dropdown(
        {label: key for key, label in guide.REWRITES.items()},
        value=guide.REWRITES["first"],
        label="How to rewrite the history",
    )
    mo.vstack(
        [
            mo.md("## Part B: try other rewrites"),
            mo.hstack([mode, edit], justify="start", gap=3),
            mo.md(f"Live needs `ANTHROPIC_API_KEY` (found: **{guide.api_key_present('anthropic')}**). Only the first rewrite was recorded."),
        ]
    )
    return edit, mode


@app.cell
def _():
    def build_request(model: str, prefix: str, messages: list) -> dict:
        return {
            "model": model,
            "max_tokens": 64,
            "cache_control": {"type": "ephemeral"},  # mark at the end of the conversation, moves every call
            "system": [
                {
                    "type": "text",
                    "text": prefix,
                    "cache_control": {"type": "ephemeral"},  # <- keeps the handbook cached even if history is rewritten
                }
            ],
            "messages": messages,
        }


    REWRITE_FUNCTIONS = {
        "first": lambda m: [{**m[0], "content": m[0]["content"] + " (edited)"}, *m[1:]],
        "middle": lambda m: [*m[:4], {**m[4], "content": m[4]["content"] + " (edited)"}, *m[5:]],
        "drop": lambda m: m[2:],
        "summarize": lambda m: [
            {"role": "user", "content": "Summary so far: rules 1 to 3 were discussed."},
            {"role": "assistant", "content": "Understood."},
            *m[6:],
        ],
    }
    return REWRITE_FUNCTIONS, build_request


@app.cell
def _(guide, mo, mode):
    run = mo.ui.run_button(
        label="Run 4 turns, then the rewrite",
        disabled=mode.value != "live" or not guide.api_key_present("anthropic"),
    )
    run
    return (run,)


@app.cell
def _(PROVIDER, REWRITE_FUNCTIONS, build_request, edit, guide, mo, mode, run):
    result = None
    _note = ""
    if mode.value == "replay":
        if edit.value == "first":
            _app = guide.load_recording(PROVIDER, "multiturn")
            _rw = guide.load_recording(PROVIDER, "rewrite")
            result = (_app["turns"][-1]["provider_usage"], _rw["provider_usage"], guide.label("replay", _rw))
        else:
            _note = "That rewrite was not recorded. Switch to **Live**, or pick \"Edit the first message\"."
    elif run.value:
        import anthropic

        _client = anthropic.Anthropic()
        _model = guide.model_for(PROVIDER)
        _prefix = guide.make_prefix()
        _history = []
        try:
            for _i in range(1, 5):
                _history.append({"role": "user", "content": f"In one short sentence, what is rule {_i}?"})
                _resp = _client.messages.create(**build_request(_model, _prefix, _history))
                _history.append({"role": "assistant", "content": "".join(b.text for b in _resp.content if b.type == "text") or "OK"})
                _last_append = _resp.usage.model_dump(mode="json")
            _rewritten = [*REWRITE_FUNCTIONS[edit.value](_history), {"role": "user", "content": "In one short sentence, what is rule 5?"}]
            _after = _client.messages.create(**build_request(_model, _prefix, _rewritten)).usage.model_dump(mode="json")
            result = (_last_append, _after, guide.label("live", model=_model, sdk=anthropic.__version__))
        except Exception as _error:
            _note = guide.explain_error(_error, "anthropic")
    else:
        _note = "Press the run button."
    mo.md(_note) if _note else None
    return (result,)


@app.cell
def _(PROVIDER, economics, guide, mo, result):
    mo.stop(result is None)
    _before, _after, _badge = result
    _b, _a = guide.turn_numbers(PROVIDER, _before), guide.turn_numbers(PROVIDER, _after)
    _cb, _ca = economics.cost_of_usage(PROVIDER, _before), economics.cost_of_usage(PROVIDER, _after)
    _lost = _b["read"] - _a["read"]
    _text = (
        f"The read fell by **{_lost}** tokens, from {_b['read']} to {_a['read']}, and the write went from {_b['write']} to {_a['write']}."
        if _lost > 0
        else f"The read did not fall (read {_a['read']}, wrote {_a['write']}). Another request may have warmed the cache, or the rewrite touched only the end. Run it again."
    )
    mo.vstack(
        [
            mo.md(f"_{_badge}_"),
            mo.md(
                "| Call | Read | Written | Normal input | Cost |\n|---|---|---|---|---|\n"
                f"| Last normal turn | {_b['read']} | {_b['write']} | {_b['plain']} | ${_cb:.6f} |\n"
                f"| After the rewrite | {_a['read']} | {_a['write']} | {_a['plain']} | ${_ca:.6f} |"
            ),
            mo.callout(mo.md(_text), kind="info"),
            mo.accordion(
                {
                    "Raw usage, last normal turn": mo.md(f"```json\n{guide.usage_json(_before)}\n```"),
                    "Raw usage, after the rewrite": mo.md(f"```json\n{guide.usage_json(_after)}\n```"),
                }
            ),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
        ## What to take away

        - **A rewrite throws away the cache from the first changed message onward.** The earlier the change,
          the more you lose. Editing the oldest message loses nearly everything after the handbook.
        - **Mark the long fixed part separately.** The live request above puts a second `cache_control` on the
          handbook, so it keeps its own cache entry and survives a rewrite of the conversation. Without that mark,
          whether the handbook survives depends on which earlier entries exist. The recording above was captured
          with an earlier cache entry in place, so it shows the handbook surviving.
        - **Dropping the oldest turn every call is a rewrite every call.** A sliding window moves the start of the
          conversation each time, so it never reads the conversation part. Dropping a big chunk now and then, then
          appending for a while, rewrites far less often. This follows from the matching rule. This lesson does not measure it.
        - **A summary is a rewrite once**, then appending works again. It pays if the summary replaces enough tokens
          and you keep appending afterwards.

        Next: `05_openai_rewriting_history.py` runs the same rewrites where caching is automatic.
        """
    )
    return


if __name__ == "__main__":
    app.run()
