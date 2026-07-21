import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from data.threads import THREAD_MAP, get_thread_by_name, get_thread_display_names
from llm.cache import cached_call_llm
from prompts.classify import CLASSIFY_SYSTEM_PROMPT, CLASSIFY_USER_PROMPT_TEMPLATE
from prompts.decompose import DECOMPOSE_SYSTEM_PROMPT, DECOMPOSE_USER_PROMPT_TEMPLATE
from prompts.summarize import SUMMARIZE_SYSTEM_PROMPT, SUMMARIZE_USER_PROMPT_TEMPLATE
from prompts.subtext import SUBTEXT_SYSTEM_PROMPT, format_subtext_user_prompt
from prompts.simulate import SIMULATE_SYSTEM_PROMPT, format_simulate_user_prompt
from prompts.draft import DRAFT_SYSTEM_PROMPT, format_draft_user_prompt
from dotenv import load_dotenv
load_dotenv()
if not os.environ.get('DEEPSEEK_API_KEY'):
    print('ERROR: DEEPSEEK_API_KEY not set.')
    sys.exit(1)


def _format_messages(messages):
    """Format messages into a readable string for prompt templates."""
    parts = []
    for i, msg in enumerate(messages):
        parts.append(
            f"[Email {i + 1}] From: {msg['from']}\n"
            f"To: {msg['to']}\n"
            f"Date: {msg['date']}\n"
            f"Subject: {msg['subject']}\n\n"
            f"{msg['body']}"
        )
    return "\n\n---\n\n".join(parts)


def fmt_classify(thread):
    subject = thread['messages'][0].get('subject', '') if thread['messages'] else ''
    messages = _format_messages(thread['messages'])
    return CLASSIFY_USER_PROMPT_TEMPLATE.format(subject=subject, messages=messages)


def fmt_decompose(thread):
    subject = thread['messages'][0].get('subject', '') if thread['messages'] else ''
    messages = _format_messages(thread['messages'])
    return DECOMPOSE_USER_PROMPT_TEMPLATE.format(subject=subject, messages=messages)


def fmt_summarize(thread):
    subject = thread['messages'][0].get('subject', '') if thread['messages'] else ''
    messages = _format_messages(thread['messages'])
    return SUMMARIZE_USER_PROMPT_TEMPLATE.format(subject=subject, messages=messages)


MODULES = [
    ('classify',   CLASSIFY_SYSTEM_PROMPT,   fmt_classify),
    ('decompose',  DECOMPOSE_SYSTEM_PROMPT,  fmt_decompose),
    ('summarize',  SUMMARIZE_SYSTEM_PROMPT,  fmt_summarize),
    ('subtext',    SUBTEXT_SYSTEM_PROMPT,    format_subtext_user_prompt),
    ('simulate',   SIMULATE_SYSTEM_PROMPT,   format_simulate_user_prompt),
    ('draft',      DRAFT_SYSTEM_PROMPT,      format_draft_user_prompt),
]


def main():
    print(f'Warming cache for {len(get_thread_display_names())} threads x {len(MODULES)} modules...')
    for name in get_thread_display_names():
        thread = get_thread_by_name(name)
        print(f'\n=== {name} ===')
        for mod_name, sys_prompt, fmt_fn in MODULES:
            print(f'  {mod_name}...', end=' ', flush=True)
            try:
                result = cached_call_llm(sys_prompt, fmt_fn(thread))
                print(f'OK ({len(result)} chars)')
            except Exception as e:
                print(f'FAILED: {e}')
    import glob
    cache_files = glob.glob(os.path.join(os.path.dirname(__file__), 'data', 'cache', '*.json'))
    print(f'\nDone! Cache files: {len(cache_files)}')


if __name__ == "__main__":
    # Opt this script into live LLM calls. Set inside __main__ so that
    # importing this module from elsewhere does not silently authorize
    # billable calls.
    os.environ.setdefault("SEMANTICMAIL_RUNTIME", "cli_warmer")
    main()
