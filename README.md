# SemanticMail — Context-Aware Email Agent with Social Intelligence

> **Beyond what is said, understanding what is meant.**

## Problem Statement

Current email assistants treat communication as **literal text**. They miss the gap between *what is said* and *what is meant* — the domain of **pragmatic meaning** that humans navigate effortlessly.

When a professor writes to a student who requested a recommendation letter:

> *"Li Wei — I will review when I get a chance."*

- A **literal-reading AI** sees: a reasonable acknowledgement
- A **pragmatic-reading human** sees: the greeting shifted from "Hi Li Wei" to just "Li Wei", the 5-day reply gap signals deprioritization, and "when I get a chance" is an off-record face-saving strategy that likely means reluctance or refusal

This gap is where careers are made or broken, deals are won or lost, and relationships are built or destroyed.

## Key Innovation: Pragmatic Inference Chain (PIC)

Our core analysis is a 4-layer **Pragmatic Inference Chain** grounded in three foundational frameworks from linguistic pragmatics:

| Framework | What It Detects |
|---|---|
| **Grice's Cooperative Principle** | Conversational implicature through maxim violations |
| **Brown & Levinson's Politeness Theory** | Face-threatening acts and politeness strategies |
| **Spencer-Oatey's Rapport Management** | Relational dynamics and interactional rapport across turns |

The PIC chains together four analysis layers per email:
1. **Literal Content** — what was explicitly said
2. **Pragmatic Inference** — Gricean violations, indirect speech acts, implicature
3. **Social Dynamics** — power relationships, face threats, politeness strategies, tone
4. **Risk Assessment** — communication risk level (safe / caution / warning / critical)

## Ablation Study: Does PIC Structure Help?

We tested whether the structured PIC prompt adds value over unstructured prompts on DeepSeek V4-Flash (`deepseek-chat`). Three conditions, 15 email threads, 45 total evaluations:

| Condition | Prompt | Model |
|---|---|---|
| **A (Full PIC)** | 4-layer PIC with Grice, Brown & Levinson, Spencer-Oatey | V4-Flash |
| **B (Generic)** | "Analyze subtext and social dynamics" (same JSON schema) | V4-Flash |
| **C (No framing)** | "Review this thread" (same JSON schema) | V4-Flash |

### Key Findings

**PIC calibrates risk more accurately.** Condition A rated 9/15 threads "warning" vs Condition C's 2/15 — catching social pressure (Thread F), audience manipulation (Thread G), and strategic silence (Thread M) that the no-framing condition missed.

**PIC reduces false positives.** On Thread O (a straightforward VPN address Q&A with zero subtext), Condition A produced 0 spurious pragmatic signals. Condition B hallucinated 5 signals on the same thread. The structured schema constrains the model from over-reading.

**Reframing:** PIC does not give LLMs pragmatic ability they lack — it **calibrates their pragmatic sensitivity**, reducing both false negatives (missed risks) and false positives (hallucinated signals).

**Known limitation:** Audience-level pragmatics (CC manipulation, reply-all dynamics) are not reliably detected even with PIC. The model treats recipient metadata as routing information rather than social signals.

## Demo Scenarios

15 email threads covering diverse pragmatic phenomena in Chinese and English workplace contexts:

| Thread | Phenomenon | Risk |
|---|---|---|
| A: Recommendation Letter | Power asymmetry, tone cooling, reply gap | Warning |
| B: Internship Follow-up | Urgency escalation, indirect refusal | Warning |
| C: Cross-cultural Collaboration | EN/ZH code-switching, face-saving | Caution |
| D: Ambiguous Request | Vague ask, over-delivery, non-acknowledgment | Caution |
| E: Public Praise | CC to VP, embedded corrections in praise | Safe |
| F: Peer Pressure | Social obligation escalation, no authority | Warning |
| G: CC Escalation | Audience manipulation via CC, manager override | Caution |
| H: Ironic Politeness | Hedge accumulation as passive resistance | Warning |
| I: Terse Replies | Brevity as power marker ("Fine.", "Proceed.") | Warning |
| J: Apology Deflection | Non-apology + blame shifting | Warning |
| K: Guanxi Request | Cross-department favor via relational capital | Safe |
| L: Corporate Euphemism | Positive framing masking negative reality | Caution |
| M: Strategic Silence | Response delay correlated with ask magnitude | Warning |
| N: Formality Shift | Address form change after disagreement | Warning |
| O: VPN Address Q&A | True negative — no subtext (false positive control) | Safe |

## Architecture

```
app.py (Streamlit entry, 4 tabs)
  -> ui/ (tab modules + shared components)
    -> prompts/ (system prompts + user prompt formatters)
      -> llm/ (API clients + cache layer)
        -> data/ (15 demo threads + cached JSON responses)
```

**Dependency flow is strictly one-directional:** UI calls prompts, prompts call LLM clients. No reverse dependencies.

## Quick Start

```bash
cd email-agent
pip install -r requirements.txt
echo "DEEPSEEK_API_KEY=sk-xxx" > .env   # Required for live analysis
streamlit run app.py
```

Cached demo responses are included — the app works for demo purposes without an API key.

## Project Structure

```
email-agent/
├── app.py                       # Streamlit app (4 tabs)
├── requirements.txt             # Pinned dependencies
├── warm_cache.py                # Cache warmer (DeepSeek)
├── warm_cache_ablation.py       # Ablation warmer (3 conditions x 15 threads)
├── view_ablation.py             # Ablation results viewer (side-by-side comparison)
├── data/
│   ├── threads.py               # 15 demo threads
│   └── cache/                   # MD5-keyed LLM response cache (gitignored)
├── llm/
│   ├── client.py                # DeepSeek API (deepseek-chat -> V4-Flash)
│   ├── baseline_client.py       # OpenRouter baseline (GPT-OSS 20B)
│   └── cache.py                 # cached_call_llm() with model-aware cache keys
├── prompts/
│   ├── subtext.py               # 4-layer PIC analysis (core innovation)
│   ├── ablation.py              # Ablation conditions B (generic) and C (no framing)
│   ├── classify.py              # Intent & urgency classification
│   ├── summarize.py             # Thread summarization
│   ├── decompose.py             # Task/action item extraction
│   ├── simulate.py              # 3-strategy reply simulator
│   ├── draft.py                 # Naive vs. smart draft comparison
│   └── baseline_gptoss.py       # Minimal baseline prompt
└── ui/
    ├── components.py            # Shared UI components
    ├── styles.py                # CSS injection
    ├── overview_tab.py          # Tab 1: Thread overview
    ├── subtext_tab.py           # Tab 2: PIC analysis with tone trajectory
    ├── simulator_tab.py         # Tab 3: 3 strategy columns
    └── draft_tab.py             # Tab 4: Naive vs. smart comparison
```

## Tech Stack

- **Frontend:** Streamlit
- **LLM:** DeepSeek V4-Flash via `deepseek-chat` endpoint (OpenAI-compatible SDK). Note: `deepseek-chat` routed to V3/V3.2 prior to 2026-04-24; existing cached responses were generated under those earlier models.
- **Caching:** File-based MD5-keyed JSON cache with model-aware keys — works offline
- **Pragmatic Frameworks:** Grice, Brown & Levinson, Spencer-Oatey

## License

MIT License
