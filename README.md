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
| D: Ambiguous Request | Vague ask, over-delivery, non-acknowledgment | Warning |
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

Risk levels above reflect Condition A (Full PIC) cache output. Condition A distribution: **3 safe / 3 caution / 9 warning / 0 critical**.

## Architecture

The app runs in **three modes**, selected from the sidebar:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Sidebar radio: [🎭 Demo Mode | 📬 Inbox Simulator | 📊 Real Dashboard] │
└─────────────────────────────────────────────────────────────────────────┘

🎭 Demo Mode (default) — 15 synthetic threads, 5 tabs
    Overview │ Subtext │ Simulator │ Baseline Comparison │ Ablation

📬 Inbox Simulator Mode — Jeff Dasovich's 401-email Enron inbox
    Browse → Triage → PIC → Memory Recall → Draft Critique (full-screen)

📊 Real Data Dashboard — pipeline output browser
    Contacts │ Obligations │ Threads │ Triage results (full-screen)
```

### Sprint-by-sprint data flow

```
Sprint 1 — Demo UI (synthetic data)
    15 hardcoded threads → app.py → 5-tab PIC visualization
        │
        ▼
Sprint 2 — Enron Inbox Memory Pipeline (real data at scale)
    enron_load.py     →  emails.json (401) + sent_emails.json (5,099)
        │
        ▼
    build_index.py    →  index.pkl (all-MiniLM-L6-v2, 400×384-d vectors)
        │
        ▼
    triage_pass.py    →  triage_results.json (401 single-call classifications)
                         cascade ratio: 91 flagged / 401 = 22.7%
        │
        ▼ (non-safe emails only)
    deep_analysis.py  →  memory-augmented 4-layer PIC
                         (anti-leakage: evidence-only context block)
        │
        ▼
Sprint 3 — Reply Drafting A/B
    draft_reply.py           →  COLD vs SCAFFOLDED drafts per email
    ablation_reply_judge.py  →  blind LLM-as-judge (N=8, randomized A/B)
        │
        ▼
Sprint 4 — Obligation Ledger
    build_ledger.py   →  ledger.json (229 obligations; 100 resolved
                         via sent-mail norm-subject matching)
    ledger_eval.py    →  12-entry spot-check harness
        │
        ▼
Sprint 5 — End-to-End CLI
    run_agent.py      →  .eml/.mbox/stdin → triage → PIC → drafts
                         → obligations → Markdown report
                         (offline-first; --live / --local-only / --redact
                         / --feedback flags; atomic writes; message_id-keyed
                         dedup; load-once + append-in-memory + full-state
                         atomic write-back per run)
```

**Dependency flow is strictly one-directional:** UI → prompts → LLM clients. No reverse dependencies.

## Sprint 2–5: Inbox-Scale Pipeline

Beyond the 15 synthetic demo threads, the project runs end-to-end on a real Enron mailbox (Jeff Dasovich, Aug–Dec 2001).

### Enron triage cascade (401 inbound emails)

Every incoming email gets one cheap triage LLM call (`prompts/triage.py`) classifying `{intent, urgency, risk_level, tone_label, key_signals, open_asks}`. Only non-safe emails (risk ≥ caution) cascade to the expensive 4-layer PIC.

| Risk level | Count | % | Cascades to PIC? |
|---|---|---|---|
| safe | 310 | 77.3% | no |
| caution | 66 | 16.5% | yes |
| warning | 24 | 6.0% | yes |
| critical | 1 | 0.2% | yes |
| **total flagged** | **91** | **22.7%** | — |

### Memory retrieval (MiniLM-L6-v2, 384-d)

`build_index.py` embeds head+tail ~1000 chars of every email into a 400×384 matrix using `all-MiniLM-L6-v2` (`sentence-transformers`). At analysis time, cosine similarity over the matrix retrieves the top-k semantically related prior emails.

The memory context block (`prompts/memory_context.py`) is **evidence-only**: dated snippets, prior per-email triage labels (clearly marked as cheap-pass observations), unanswered asks accumulated per sender, thread activity metadata. No pre-baked trajectory verdicts — the model must derive escalation/cooling conclusions itself. This anti-leakage design is required for the A/B ablation to be non-circular.

### Cold vs Scaffolded reply A/B (N=8, blind judge)

For each of 8 target emails spanning `request_with_asks` and `face_sensitive` categories, two drafts are generated:
- **COLD** — only the incoming email
- **SCAFFOLDED** — incoming email + 4-layer PIC + memory context block

`ablation_reply_judge.py` randomizes the labels (Draft A / Draft B) and asks a separate LLM call to score both on open-ask coverage, tone/face calibration, subtext engagement, and overall preference. Judge is unaware which is COLD vs SCAFFOLDED. Result: scaffolded wins 5, cold wins 2, tie 1.

Self-consistency check (`self_consistency.py`): scaffolded drafts have **lower spread** across temperatures 0.5/0.7/0.9 than cold drafts (mean 0.227 vs 0.343, Δ = 0.116) — adding PIC context stabilizes output.

### Obligation ledger (229 obligations, 100 resolved)

`build_ledger.py` extracts `{direction, canonical_ask, obligor, implied_deadline}` from every ask-bearing email via `prompts/obligation.py`. Resolution is heuristic: Jeff's outbound sent mail is scanned for later messages on the same `norm_subject` after the ask date. Ages are computed against the corpus "today" (2001-12-14), not wall-clock — important so the demo doesn't drift.

| Bucket | Count |
|---|---|
| you_owe (open) | 102 |
| you_promised (open) | 27 |
| resolved | 100 |
| **total** | **229** |

Resolution rate: 100/229 = 43.7% (heuristic, not yet hand-verified — `ledger_eval.py` exposes 12 spot-check entries with `hand_check` fields for manual precision auditing).

### End-to-end CLI (`run_agent.py`)

Single command runs the full chain on `.eml` / `.mbox` / pasted text input:

```bash
python run_agent.py email.eml                 # offline-first (cache only)
python run_agent.py email.eml --live          # allow live LLM on cache miss
python run_agent.py email.eml --local-only    # hard-disable any network call
python run_agent.py email.eml --redact        # PII-scrubbed report
python run_agent.py email.eml --feedback "…"  # persist user correction
```

Emits a Markdown report to stdout and `out/<id>.md`. Memory is loaded once per run from disk into RAM; new emails are appended in-memory via `message_id`-keyed dedup (with body+date fallback), then the full state is written back atomically (tempfile + `os.replace`). The corpus is never rebuilt via `enron_load.py` for incremental updates. A truly incremental on-disk format (append-only log, partial reads) is future work.

## Quick Start

```bash
cd email-agent
pip install -r requirements.txt
echo "DEEPSEEK_API_KEY=sk-xxx" > .env   # Required for live analysis
streamlit run app.py
```

Cached demo responses are included — the app works for demo purposes without an API key.

To run the inbox-scale pipeline end-to-end on a single email:

```bash
cd email-agent
python run_agent.py /path/to/email.eml --local-only
```

## Project Structure

```
email-agent/
├── app.py                       # Streamlit entry (3 modes: Demo / Inbox Simulator / Dashboard)
├── requirements.txt             # Pinned dependencies
│
├── ── Sprint 5: end-to-end CLI ──
├── run_agent.py                 # Single-command pipeline (.eml/.mbox/stdin → Markdown report)
│
├── ── Sprint 2: Enron inbox pipeline ──
├── enron_load.py                # Parse Enron tarball → emails.json + sent_emails.json
├── build_index.py               # Build all-MiniLM-L6-v2 embedding index → index.pkl
├── triage_pass.py               # Cheap per-email triage (cascade gate)
├── deep_analysis.py             # Memory-augmented 4-layer PIC on flagged emails
│
├── ── Sprint 3: reply drafting A/B ──
├── draft_reply.py               # COLD vs SCAFFOLDED draft generation
├── ablation_reply_judge.py      # Blind LLM-as-judge (N=8, randomized A/B)
├── report_reply.py              # Reply ablation report renderer
│
├── ── Sprint 4: obligation ledger ──
├── build_ledger.py              # Extract obligations + resolve via sent-mail match
├── ledger_eval.py               # 12-entry spot-check harness (hand_check fields)
├── report_ledger.py             # Ledger summary printer
│
├── ── Cross-sprint: ablation + reporting + cache warming ──
├── ablation_memory.py           # Memory-augmented PIC vs no-memory A/B
├── self_consistency.py          # Cold vs scaffolded spread across temperatures
├── report.py                    # Full pipeline summary (triage funnel, costs, ledger)
├── batch_cache_fill.py          # Simulator cache warmer (--fill-gaps mode)
├── warm_cache.py                # DeepSeek cache warmer (Sprint 1 demos)
├── warm_cache_v2.py             # GPT-OSS baseline cache warmer
├── warm_cache_ablation.py       # 3-condition × 15-thread ablation warmer
├── view_ablation.py             # Ablation results side-by-side viewer
│
├── data/
│   ├── threads.py               # 15 demo threads + THREAD_MAP + display-name accessors
│   └── cache/                   # MD5-keyed LLM response cache (gitignored)
│
├── llm/
│   ├── client.py                # DeepSeek API (deepseek-chat → V4-Flash, OpenAI SDK)
│   ├── baseline_client.py       # OpenRouter baseline (GPT-OSS 20B)
│   └── cache.py                 # cached_call_llm() with model-aware MD5 cache keys
│
├── prompts/                     # SYSTEM_PROMPT + format_*_user_prompt() per module
│   ├── subtext.py               # 4-layer PIC analysis (core innovation)
│   ├── ablation.py              # Ablation conditions B (generic) and C (no framing)
│   ├── classify.py              # Intent & urgency classification
│   ├── summarize.py             # Thread summarization
│   ├── decompose.py             # Task/action item extraction
│   ├── simulate.py              # 3-strategy reply simulator
│   ├── draft.py                 # Naive vs. smart draft comparison
│   ├── reply.py                 # COLD vs SCAFFOLDED reply draft generation
│   ├── triage.py                # Cheap per-email triage (cascade gate)
│   ├── obligation.py            # Obligation extraction (direction/ask/deadline/obligor)
│   ├── memory_context.py        # Evidence-only memory block builder (anti-leakage)
│   └── baseline_gptoss.py       # Minimal GPT-OSS baseline prompt
│
├── memory/                      # Pipeline state (Enron corpus)
│   ├── emails.json              # 401 inbound emails (dasovich-j)
│   ├── sent_emails.json         # 5,099 Jeff's outbound emails
│   ├── contacts.json            # Per-sender: n_interactions, tone_labels, risk_history, open_asks
│   ├── threads.json             # Per-thread: status, n_emails, pending_reply_from
│   ├── triage_results.json      # Per-email triage with _email_idx and _cached flags
│   ├── index.pkl                # Embedding index: {model_name, vectors[400,384], metadata[400]}
│   ├── ledger.json              # {corpus_today, counts, you_owe[], you_promised[], resolved[]}
│   ├── ledger_spotcheck.json    # 12 entries for hand-verification
│   ├── ablation_result.json     # Single-email memory A/B comparison
│   ├── reply_ablation_targets.json   # 8 target emails for COLD vs SCAFFOLDED A/B
│   ├── reply_judge_results.json # 8 blind-judge verdicts with mapped_preference
│   ├── self_consistency_results.json # Cold/scaffolded spread + aggregate (Δ=0.116)
│   ├── id_map.json              # message_id ↔ email_idx lookup
│   └── simulator_cache.json    # Pre-warmed Inbox Simulator cache: triage + PIC + memory + COLD/SCAFFOLDED drafts (Enron 401-email corpus)
│
└── ui/
    ├── components.py            # Shared UI components (cards, badges, risk styling)
    ├── styles.py                # CSS injection (theme-aware variables)
    ├── overview_tab.py          # Demo Mode Tab 1: Thread overview
    ├── subtext_tab.py           # Demo Mode Tab 2: PIC analysis with tone trajectory
    ├── simulator_tab.py         # Demo Mode Tab 3: 3-strategy reply simulator
    ├── draft_tab.py             # Demo Mode Tab 4: Naive vs. smart draft comparison
    ├── ablation_tab.py          # Demo Mode Tab 5: 3-condition ablation comparison
    ├── inbox_simulator.py       # Inbox Simulator mode (full-screen, 401 Enron emails)
    └── real_data_tab.py         # Real Data Dashboard mode (full-screen pipeline browser)
```

## Tech Stack

- **Frontend:** Streamlit
- **LLM:** DeepSeek V4-Flash via `deepseek-chat` endpoint (OpenAI-compatible SDK). Note: `deepseek-chat` routed to V3/V3.2 prior to 2026-04-24; existing cached responses were generated under those earlier models.
- **Baseline LLM:** GPT-OSS 20B via OpenRouter
- **Embeddings:** `sentence-transformers` (`all-MiniLM-L6-v2`, 384-d)
- **Vector ops:** `numpy` (cosine similarity over the 400×384 matrix)
- **Caching:** File-based MD5-keyed JSON cache with model-aware keys — works offline
- **Pragmatic Frameworks:** Grice, Brown & Levinson, Spencer-Oatey

## License

MIT License
