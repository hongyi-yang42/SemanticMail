# Incident: 2026-07 — Public-demo cost leak

## Summary

The public SemanticMail deployment on Streamlit Community Cloud was racking up
real DeepSeek API charges even with effectively zero real visitors. Two
compounding design flaws turned every page load — including bot crawls,
link previews, and sleeping-app wake-ups — into as many as ten paid LLM
calls.

## Impact

- **Cost**: real DeepSeek charges accrued over the public app's lifetime.
  Exact dollar figure sits in the DeepSeek billing dashboard; treat this
  incident as the trigger to pull those numbers and file them here.
- **Exposure window**: from initial public deployment until the fix shipped.
- **User impact**: none (no PII exposed; the only leak was the API key's
  quota budget).

## Root cause

Two compounding flaws:

1. **`st.tabs()` over-execution.** `app.py` used
   `st.tabs([Overview, Subtext, Simulator, Baseline, Ablation])`. Streamlit
   executes the body of every `with tabN:` block on every script rerun, not
   just the visible one. So a single page load fired the union of every
   tab's LLM-call path. Bots, crawlers, and Streamlit's own wake-on-traffic
   reruns all triggered it.
2. **No cache-miss guard.** `llm/cache.py` fell back to a live API call
   whenever the on-disk MD5 cache missed. Misses happened on Threads D–O
   (never warmed), on any pasted email (arbitrary `thread_data`), and on
   any prompt/temperature drift.

Combined, a single cold page load could fire up to 9 paid DeepSeek calls +
1 paid OpenRouter call, with no user action required.

## Mitigation

Shipped in this PR. Layered defense:

1. **Explicit fail-closed runtime mode** — `SEMANTICMAIL_RUNTIME =
   public_demo | local_dev | cli_warmer`. Unset or unknown value blocks
   live calls. Public deployment sets `public_demo`; cache misses raise
   `LiveCallBlockedError` instead of hitting the network.
2. **Single-branch dispatcher** — `app.py` replaces `st.tabs()` with a
   `st.radio` so only the selected section's render function runs.
3. **Button-gates on the two heavy tabs** — Simulator and Baseline
   Comparison render a placeholder + `Generate` button; no LLM call fires
   until the user clicks. Results cached in `st.session_state` keyed by
   `feature | thread_digest | prompt_version | model` so prompt bumps
   invalidate stale entries.
4. **Per-session runaway cap** — 20 live calls per browser session in
   `local_dev`. Not a global cost ceiling — only guards one runaway
   client. Documented as such.
5. **Paste mode local-dev only** — the public demo no longer exposes
   "Paste your own email"; that path is reachable only with
   `SEMANTICMAIL_RUNTIME=local_dev`.
6. **Auto-fire tabs catch `LiveCallBlockedError`** — Overview and Subtext
   keep their auto-fire-on-render pattern (cache hits are free for warmed
   Threads A/B/C), but blocked misses surface a friendly info card instead
   of erroring.
7. **Baseline Comparison renders partial results** — if one component is
   cached but another is blocked, the cached component still renders; the
   blocked ones show a placeholder card.
8. **CLI warmers opt-in inside `__main__`** — `warm_cache*.py`,
   `batch_cache_fill.py`, `run_agent.py` set
   `SEMANTICMAIL_RUNTIME=cli_warmer` inside their `if __name__ == "__main__":`
   block, so importing them as modules doesn't silently authorize live
   calls.

## Token revocation

**The DeepSeek API key embedded in `.streamlit/secrets.toml` is presumed
compromised** — anyone who hit the public demo could have triggered calls
billed to it, and the cache-miss path means the call patterns (prompts,
user inputs) were observable via the deployed app's behaviour.

Action: revoke the existing DeepSeek key in the DeepSeek dashboard and
issue a new one. Replace the value in Streamlit Community Cloud's secrets
manager. Add `SEMANTICMAIL_RUNTIME = "public_demo"` to the same secrets
file so the new key is protected by the runtime guard.

- [ ] Old DeepSeek key revoked on YYYY-MM-DD
- [ ] New DeepSeek key issued and rotated into Streamlit secrets
- [ ] `SEMANTICMAIL_RUNTIME = "public_demo"` added to deployed secrets
- [ ] Confirmed via cold-load test on the deployed URL that zero new API
      calls appear in the DeepSeek dashboard

## Verification

Automated tests in `email-agent/tests/`:

```
$ pytest email-agent/tests/ -v
============================= 11 passed in 0.51s ==============================
```

Cases covered: cache hit never touches network; public_demo and unset
runtime both block cache misses with `LiveCallBlockedError`; unknown
runtime value also blocks; local_dev calls network exactly once on miss
and zero on subsequent cache hit; cli_warmer bypasses the session limit;
baseline client goes through the same guard; rate limit fires after cap;
default app load dispatches only the Overview renderer; Simulator and
Baseline sections make zero calls before their Generate button is clicked.

End-to-end manual checks (run locally with `SEMANTICMAIL_RUNTIME` toggled)
are documented in `/Users/hongyi/.claude/plans/resilient-sprouting-crown.md`
under "Verification".

## Follow-ups

- Wire these tests into CI once a CI pipeline exists.
- Periodically audit the DeepSeek dashboard for unexpected spend.
- If BYOK is ever reintroduced, it must use session-scoped state or
  explicit key passing — never a module-level `_client` mutation. See
  the design principles in the plan doc.
