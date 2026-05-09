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
