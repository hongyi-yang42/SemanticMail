# SemanticMail — Context-Aware Email Agent with Social Intelligence

> **Beyond what is said, understanding what is meant.**

## 🎯 Problem Statement

Current email assistants — even large-scale models like GPT-OSS 20B — treat communication as **literal text**. They completely miss the gap between *what is said* and *what is meant*, the entire domain of **pragmatic meaning** that humans navigate effortlessly.

**The GPT-OSS 20B Failure Case:**

When a professor writes to a student who requested a recommendation letter:

> *"Li Wei — I will review when I get a chance."*

- A **literal-reading AI** sees: a reasonable acknowledgement ✅
- A **pragmatic-reading human** sees: the greeting shifted from "Hi Li Wei" to just "Li Wei", the 5-day reply gap signals deprioritization, and "when I get a chance" is an off-record face-saving strategy that likely means reluctance or refusal ⚠️

This gap is where careers are made or broken, deals are won or lost, and relationships are built or destroyed.

## 💡 Key Innovation: Pragmatic Inference Chain (PIC)

Our core analysis is a 4-layer **Pragmatic Inference Chain** grounded in three foundational frameworks from linguistic pragmatics:

| Framework | What It Detects |
|---|---|
| **Grice's Cooperative Principle** | Conversational implicature through maxim violations (quantity, quality, relevance, manner) |
| **Brown & Levinson's Politeness Theory** | Face-threatening acts (positive/negative face) and politeness strategies |
| **Spencer-Oatey's Rapport Management** | Relational dynamics, sociality rights, and interactional rapport across turns |

The PIC chains together four analysis layers per email:
1. **Literal Content** → What was explicitly said
2. **Pragmatic Inference** → Gricean violations, indirect speech acts, implicature
3. **Social Dynamics** → Power relationships, face threats, politeness strategies, tone
4. **Risk Assessment** → Communication risk level (safe → caution → warning → critical)

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Streamlit Frontend                      │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌────────────┐  │
│  │ Overview   │ │ Subtext   │ │ Reply     │ │ Smart      │  │
│  │ Tab 1      │ │ Analysis  │ │ Simulator │ │ Draft      │  │
│  │            │ │ Tab 2 ⭐  │ │ Tab 3     │ │ Tab 4      │  │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └──────┬─────┘  │
│  ┌─────▼─────────────▼─────────────▼──────────────▼──────┐  │
│  │                  Prompt Module Layer                    │  │
│  │  classify │ summarize │ decompose │ subtext ⭐ │       │  │
│  │  simulate │ draft     │           │            │       │  │
│  └──────────────────────┬────────────────────────────────┘  │
│  ┌──────────────────────▼────────────────────────────────┐  │
│  │     LLM Cache Layer (MD5-keyed JSON, works offline)    │  │
│  └──────────────────────┬────────────────────────────────┘  │
│  ┌──────────────────────▼────────────────────────────────┐  │
│  │         DeepSeek V3 API (OpenAI-compatible SDK)        │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

```bash
cd email-agent
pip install -r requirements.txt
echo "DEEPSEEK_API_KEY=sk-xxx" > .env   # Required for live analysis
streamlit run app.py
```

Cached demo responses are included — the app works for demo purposes without an API key.

## 📧 Demo Scenarios

| Scenario | Key Dynamics | Risk |
|---|---|---|
| **Thread A: 师生推荐信** (Recommendation Letter) | Power asymmetry, greeting shift, tone cooling, 5-day reply gap | ⚠️ Warning |
| **Thread B: 实习跟进** (Internship Follow-up) | Urgency escalation, timeline vagueness, indirect refusal | 🔴 Critical |
| **Thread C: 跨文化合作** (Cross-cultural Collaboration) | EN/ZH code-switching, face-saving, deferential disagreement | 🟡 Caution |

## 📦 Project Structure

```
email-agent/
├── app.py                    # Streamlit app (4 tabs)
├── requirements.txt          # Pinned dependencies
├── .env.example              # API key template
├── data/
│   ├── threads.py            # 3 demo threads (Chinese workplace scenarios)
│   └── cache/                # MD5-keyed LLM response cache (JSON)
├── llm/
│   ├── client.py             # DeepSeek V3 via OpenAI SDK
│   └── cache.py              # cached_call_llm() with file-based cache
├── prompts/
│   ├── classify.py           # Intent & urgency classification
│   ├── summarize.py          # Thread summarization
│   ├── decompose.py          # Task/action item extraction
│   ├── subtext.py            # ⭐ 4-layer PIC analysis (core innovation)
│   ├── simulate.py           # 3-strategy reply simulator
│   └── draft.py              # Naive vs. smart draft comparison
└── ui/
    ├── components.py         # Shared UI components (cards, badges, emojis)
    ├── styles.py             # CSS injection
    ├── overview_tab.py       # Tab 1: Thread overview + baseline analysis
    ├── subtext_tab.py        # Tab 2: ⭐ PIC analysis with tone trajectory
    ├── simulator_tab.py      # Tab 3: 3 strategy columns with risk badges
    └── draft_tab.py          # Tab 4: Naive vs. smart side-by-side comparison
```

## 🛠️ Tech Stack

- **Frontend:** Streamlit — interactive data app with wide layout
- **LLM:** DeepSeek V3 via OpenAI-compatible SDK (json_object response format)
- **Caching:** File-based MD5-keyed JSON cache (offline demo support)
- **Language:** Python 3.10+
- **Pragmatic Frameworks:** Grice, Brown & Levinson, Spencer-Oatey

## 🚢 Deployment

### Streamlit Cloud
1. Push to GitHub → Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect repo → Main file: `email-agent/app.py`
3. Add `DEEPSEEK_API_KEY` secret (optional — cached demos work without it)

### HuggingFace Spaces
1. Create Streamlit Space → Upload files
2. Set `DEEPSEEK_API_KEY` in Space secrets (optional)

## 📄 License

MIT License
