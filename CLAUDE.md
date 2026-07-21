# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SemanticMail is a context-aware email agent that applies linguistic pragmatics to analyze email communication. The core innovation is a 4-layer Pragmatic Inference Chain (PIC) that detects what is *meant* beyond what is *said*, using frameworks from Grice, Brown & Levinson, and Spencer-Oatey. The app analyzes Chinese workplace email scenarios with English-language pragmatic analysis.

## Running the App

```bash
cd email-agent
pip install -r requirements.txt
streamlit run app.py
```

The app works for demo purposes without API keys thanks to pre-computed cached responses. For live analysis, set `DEEPSEEK_API_KEY` in `email-agent/.env`. Baseline comparison also requires `OPENROUTER_API_KEY`.

There is no test suite or CI/CD pipeline.

## Architecture

The app lives in `email-agent/` and follows a layered architecture:

```
app.py (Streamlit entry, 4 tabs)
  → ui/ (tab modules + shared components)
    → prompts/ (system prompts + user prompt formatters)
      → llm/ (API clients + cache layer)
        → data/ (demo threads + cached JSON responses)
```

**Dependency flow is strictly one-directional:** UI calls prompts, prompts call LLM clients. No reverse dependencies.

### Prompt Modules (`prompts/`)

Each module follows an identical pattern:
- A `*_SYSTEM_PROMPT` constant with detailed JSON-schema instructions
- A `format_*_user_prompt(thread)` function that serializes thread data
- The LLM is called with `json_object` response format; all responses are parsed as JSON

The core module is `prompts/subtext.py` — it implements the 4-layer PIC analysis (literal → pragmatic inference → social dynamics → risk assessment).

### LLM Caching (`llm/cache.py`)

All LLM calls go through `cached_call_llm()` which uses MD5(system_prompt + user_prompt + temperature) as a cache key. Cached responses are stored as JSON files in `data/cache/`. This enables offline demos and deterministic output during presentations.

Two cache warmers exist: `warm_cache.py` (DeepSeek) and `warm_cache_v2.py` (GPT-OSS baseline). Run these after modifying prompts to regenerate cached responses.

### Demo Data (`data/threads.py`)

Three hardcoded email threads in Chinese workplace contexts, each designed to demonstrate specific pragmatic phenomena: power asymmetry (Thread A), indirect refusal (Thread B), and cross-cultural face management (Thread C).

### UI Layer (`ui/`)

Four Streamlit tabs: Overview, Subtext Analysis (core PIC visualization), Reply Simulator (3 strategies), and Draft Comparison (baseline vs. smart). Shared components (cards, badges, risk-level styling) live in `ui/components.py` and `ui/styles.py`.

## Key Conventions

- All LLM responses must be valid JSON — prompt templates enforce structured output via `json_object` mode
- Temperature is kept low (0.3–0.5) for consistent analysis results
- Risk levels use a fixed vocabulary: safe, caution, warning, critical
- Demo emails are Chinese; analysis output is English
- The `baseline_client.py` uses OpenRouter; `client.py` uses DeepSeek directly — both use the OpenAI SDK interface

## Runtime Modes (live-call authorization)

Live (billable) LLM calls are gated by the `SEMANTICMAIL_RUNTIME` env var.
The system is **fail-closed**: unset or unknown values block live calls.

| Value | Behavior on cache miss |
|---|---|
| `public_demo` | Raises `LiveCallBlockedError` — cache-only operation |
| `local_dev` | Live call allowed, subject to per-session cap (default 20) |
| `cli_warmer` | Live call allowed, no cap (used by offline warmers) |
| **unset / unknown** | Same as `public_demo` — fail closed |

- The public deployment must set `SEMANTICMAIL_RUNTIME = "public_demo"` in `.streamlit/secrets.toml`.
- For local dev: `export SEMANTICMAIL_RUNTIME=local_dev` before `streamlit run`.
- CLI warmers (`warm_cache.py`, `warm_cache_v2.py`, `warm_cache_ablation.py`,
  `batch_cache_fill.py`, `run_agent.py`) set `SEMANTICMAIL_RUNTIME=cli_warmer`
  inside their `if __name__ == "__main__":` block — so importing them as
  modules does NOT authorize live calls.

### Per-session rate limit

`local_dev` mode enforces a per-browser-session cap of 20 live calls via
`st.session_state["_live_llm_calls"]`. Override with the
`SEMANTICMAIL_RATE_LIMIT` env var. This is **runaway protection for a single
session**, not a global cost ceiling — concurrent clients and new sessions
are not constrained.

### Paste mode

"✍️ Paste your own email..." is visible in the sidebar only when
`SEMANTICMAIL_RUNTIME=local_dev`. The public demo is cache-only and does
not expose ad-hoc email analysis.

### Tests

`email-agent/tests/` contains pytest tests (mocked at the `call_llm` /
`call_baseline_llm` boundary, NOT at the OpenAI client) covering: cache-hit
no-network, public_demo/unset/unknown block-on-miss, local_dev
calls-network-once, cli_warmer bypass, baseline routing, rate-limit cap,
default-load dispatch, and Simulator/Baseline zero-calls-before-Generate.

```
cd email-agent
pytest tests/ -v
```

See `docs/incidents/2026-07-public-demo-cost-leak.md` for the production
incident that motivated this layering.
