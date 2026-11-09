import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import json

    import economics
    import guide
    import marimo as mo

    PROVIDER = "anthropic"
    return PROVIDER, economics, guide, json, mo


@app.cell
def _(guide, mo):
    mo.vstack(
        [
            mo.md(
                """
                # Lesson 4 (Anthropic): when caching pays and when it bites back

                A cache write costs **more** than a normal input token. A cache read costs **much less**.
                So caching is a bet that you will reuse the prefix before it expires. This lesson does the
                arithmetic on real recorded calls, then on usage patterns where the bet wins and where it loses.

                No API calls here. Everything is computed from the token counts the provider returned and the
                dated prices below.
                """
            ),
            mo.Html(guide.diagram("break-even")),
            mo.md("_Diagram drawn with write 1.25x and read 0.10x. Anthropic's read multiplier on this model is 0.05x, which only helps more._"),
        ]
    )
    return


@app.cell
def _(PROVIDER, economics, mo):
    _p = economics.PRICES[PROVIDER]
    _age = economics.price_age_days()
    _writes = ", ".join(f"{k}: {v}x" for k, v in _p["write"].items())
    _stale = (
        mo.callout(mo.md(f"These prices are **{_age} days old**. Recheck them before you trust any dollar figure."), kind="warn")
        if _age > economics.STALE_AFTER_DAYS
        else mo.md("")
    )
    mo.vstack(
        [
            mo.md(
                f"""
                ## Prices used

                | | |
                |---|---|
                | Model | `{_p['model']}` |
                | Input | ${_p['input']:.2f} per million tokens |
                | Output | ${_p['output']:.2f} per million tokens |
                | Cache read | {_p['read']}x the input price |
                | Cache write | {_writes} the input price |
                | Checked | {economics.PRICES_CHECKED}, {_age} days ago |
                | Source | {_p['source']} |

                Prices and multipliers change often and differ by model. Treat the dollar amounts as
                illustrations, and the **ratios** as the lesson.
                """
            ),
            _stale,
        ]
    )
    return


@app.cell
def _(PROVIDER, economics, guide, mo):
    _cold = guide.load_recording(PROVIDER, "cold")
    _exact = guide.load_recording(PROVIDER, "exact")
    _rows = []
    _tot_c = _tot_u = 0.0
    for _name, _rec in (("Call 1: first time (write)", _cold), ("Call 2: same prefix (read)", _exact)):
        _c = economics.cost_of_usage(PROVIDER, _rec["provider_usage"])
        _u = economics.uncached_cost_of_usage(PROVIDER, _rec["provider_usage"])
        _tot_c += _c
        _tot_u += _u
        _rows.append(f"| {_name} | ${_c:.6f} | ${_u:.6f} | {(_c / _u - 1):+.0%} |")
    mo.md(
        "## Part A: two real calls, costed\n\n"
        f"_REPLAY: recorded {_cold['captured_at']} on {_cold['model']}. Costs are computed from the raw usage._\n\n"
        "| Call | With caching | Same call, no caching | Difference |\n|---|---|---|---|\n"
        + "\n".join(_rows)
        + f"\n| **Both calls** | **${_tot_c:.6f}** | **${_tot_u:.6f}** | **{(_tot_c / _tot_u - 1):+.0%}** |\n\n"
        "The first call costs more than not caching. The second costs far less. After two calls you are already ahead. "
        "That only holds because the second call happened in time."
    )
    return


@app.cell
def _(mo):
    pasted = mo.ui.text_area(
        placeholder='Paste a "usage" JSON block from lesson 1, 2 or 3 here',
        label="Cost one of your own calls",
        full_width=True,
        rows=6,
    )
    pasted
    return (pasted,)


@app.cell
def _(PROVIDER, economics, json, mo, pasted):
    mo.stop(not pasted.value.strip())
    try:
        _usage = json.loads(pasted.value)
        _c = economics.cost_of_usage(PROVIDER, _usage)
        _u = economics.uncached_cost_of_usage(PROVIDER, _usage)
        _out = mo.md(f"Your call cost **${_c:.6f}** with caching. Without caching it would have cost **${_u:.6f}** ({(_c / _u - 1):+.0%}).")
    except (ValueError, AttributeError):
        _out = mo.md("That is not a usage JSON block. Paste the whole `{ ... }` from a lesson.")
    _out
    return


@app.cell
def _(PROVIDER, economics, mo):
    _p = economics.PRICES[PROVIDER]
    _lines = []
    for _ttl, _w in _p["write"].items():
        _n = economics.break_even_reuses(PROVIDER, _ttl)
        _lines.append(
            f"| {_ttl} | {_w}x | {_n} | write {_w} + {_n} x {_p['read']} = {_w + _n * _p['read']:.2f} "
            f"is at most 1 + {_n} = {1 + _n} |"
        )
    mo.md(
        "## Part B: how many reuses until it breaks even\n\n"
        "Count the prefix only, in units of one input-token price. Caching costs `write + n x read`. "
        "Not caching costs `1 + n`. Caching wins when `write + n x read` is at most `1 + n`.\n\n"
        "| Cache lifetime | Write | Reuses needed (n) | Check |\n|---|---|---|---|\n"
        + "\n".join(_lines)
        + "\n\nOne reuse is enough for the short lifetime. The longer, pricier write needs more. "
        "The catch: a reuse only counts if it arrives **before the cache expires**."
    )
    return


@app.cell
def _(PROVIDER, economics, mo):
    scenario = mo.ui.dropdown(list(economics.SCENARIOS), value="Sparse traffic: 6 calls, 10 minutes apart", label="Usage pattern")
    lifetime = mo.ui.dropdown(list(economics.PRICES[PROVIDER]["write"]), value="5m", label="Cache lifetime")
    prefix_tokens = mo.ui.slider(1000, 20000, step=500, value=8000, label="Prefix tokens")
    mo.vstack([mo.md("## Part C: try a usage pattern"), mo.hstack([scenario, lifetime], justify="start", gap=2), prefix_tokens])
    return lifetime, prefix_tokens, scenario


@app.cell
def _(PROVIDER, economics, lifetime, mo, prefix_tokens, scenario):
    _gaps, _stable = economics.SCENARIOS[scenario.value]
    _r = economics.simulate(PROVIDER, prefix_tokens.value, _gaps, lifetime.value, _stable)
    _kind = {"Pays": "success", "Bites": "danger", "About even": "neutral"}[_r["verdict"]]
    _why = {
        "Pays": "Most calls hit a warm cache, so the cheap reads outweigh the one expensive write.",
        "Bites": (
            "Every call writes. The gap is longer than the cache lifetime, or the prefix changes, or there is only one call, "
            "so you pay the write premium and never collect the discount."
            if _r["reads"] == 0
            else "Reads exist but the write premium is not recovered."
        ),
        "About even": "The savings and the premium roughly cancel.",
    }[_r["verdict"]]
    mo.callout(
        mo.md(
            f"**{_r['verdict']}**: {_r['calls']} calls, {_r['writes']} write(s), {_r['reads']} read(s).\n\n"
            f"With caching **${_r['cached']:.4f}**, without **${_r['uncached']:.4f}** ({-_r['saving']:+.0%}).\n\n{_why}"
        ),
        kind=_kind,
    )
    return


@app.cell
def _(PROVIDER, economics, mo, prefix_tokens):
    _ttls = list(economics.PRICES[PROVIDER]["write"])
    _head = "| Pattern | " + " | ".join(f"{t} cache" for t in _ttls) + " |\n|---|" + "---|" * len(_ttls)
    _rows = []
    for _name, (_gaps, _stable) in economics.SCENARIOS.items():
        _cells = []
        for _t in _ttls:
            _r = economics.simulate(PROVIDER, prefix_tokens.value, _gaps, _t, _stable)
            _cells.append(f"{_r['verdict']} ({-_r['saving']:+.0%})")
        _rows.append(f"| {_name} | " + " | ".join(_cells) + " |")
    mo.md(
        f"## Part D: every pattern at {prefix_tokens.value:,} prefix tokens\n\n"
        "Percent is cost change versus not caching. Negative is cheaper.\n\n" + _head + "\n" + "\n".join(_rows)
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## When to use it, and when to skip it

    **Use it** when the same long prefix is sent again within the lifetime: chat and agent loops,
    a shared system prompt under steady traffic, repeated questions over one big document.

    **It bites** when the prefix is used once or rarely, when the gap between calls is longer than the
    lifetime (you pay a write every time), when the prefix changes every call (a timestamp or ID near
    the start, lesson 2), and when you pay for the longer lifetime but reuse happens within minutes anyway.

    **Check before you ship:** log the usage fields for real traffic. If `cache_read_input_tokens` is mostly
    zero while `cache_creation_input_tokens` keeps appearing, you are paying the premium for nothing.

    Next: `04_openai_break_even.py` runs the same experiments with OpenAI's prices.
    """)
    return


if __name__ == "__main__":
    app.run()
