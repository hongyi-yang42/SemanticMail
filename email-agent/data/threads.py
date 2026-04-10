"""Demo email thread data for SemanticMail."""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Thread A: 师生推荐信  — Power Asymmetry + Tone Cooling
# ---------------------------------------------------------------------------

THREAD_A: dict[str, Any] = {
    "title": "Thread A: 师生推荐信",
    "scenario": "Power Asymmetry + Tone Cooling",
    "description": (
        "A student (Li Wei) asks a professor (Prof. Zhang) for a recommendation "
        "letter. The professor initially agrees enthusiastically, but later cools "
        "off — greeting shifts from 'Hi Li Wei' to 'Li Wei', enthusiasm drops, "
        "and a 5-day reply gap emerges."
    ),
    "pragmatic_signals": [
        "Greeting shift: 'Hi Li Wei' → 'Li Wei'",
        "Enthusiasm drop: 'Sure, happy to help!' → 'I will review when I get a chance'",
        "5-day reply gap (Jan 13 → Jan 18)",
        "Loss of warmth markers (exclamation marks, emojis)",
    ],
    "messages": [
        {
            "from": "Li Wei <liwei@university.edu>",
            "to": "Prof. Zhang <zhangprof@university.edu>",
            "date": "Jan 6, 2026",
            "subject": "Request for Recommendation Letter",
            "body": (
                "Dear Prof. Zhang,\n\n"
                "I hope this email finds you well. I am writing to ask whether "
                "you would be willing to write a letter of recommendation for my "
                "application to the graduate program in Computer Science at Stanford "
                "University.\n\n"
                "I thoroughly enjoyed your course on Machine Learning last semester, "
                "and I believe your perspective on my academic abilities would "
                "greatly strengthen my application.\n\n"
                "Thank you very much for considering my request. I am happy to "
                "provide any additional materials you might need.\n\n"
                "Best regards,\n"
                "Li Wei"
            ),
        },
        {
            "from": "Prof. Zhang <zhangprof@university.edu>",
            "to": "Li Wei <liwei@university.edu>",
            "date": "Jan 6, 2026",
            "subject": "Re: Request for Recommendation Letter",
            "body": (
                "Hi Li Wei!\n\n"
                "Sure, happy to help! 😊 It's great that you're applying to "
                "Stanford — that's an excellent program. Just send me the details "
                "about the program and any specific points you'd like me to "
                "highlight, and I'll get started on it.\n\n"
                "Best,\n"
                "Prof. Zhang"
            ),
        },
        {
            "from": "Li Wei <liwei@university.edu>",
            "to": "Prof. Zhang <zhangprof@university.edu>",
            "date": "Jan 13, 2026",
            "subject": "Re: Request for Recommendation Letter",
            "body": (
                "Dear Prof. Zhang,\n\n"
                "Thank you so much for agreeing to write the recommendation! "
                "Here are the details:\n\n"
                "- Program: MS in Computer Science, Stanford University\n"
                "- Deadline: February 15, 2026\n"
                "- Submission: Online portal (link will be sent to you)\n"
                "- Key points I'd appreciate highlighting: my final project on "
                "transformer architectures, class participation, and analytical "
                "skills\n\n"
                "I've also attached my CV and transcript for reference. Please "
                "let me know if you need anything else!\n\n"
                "Best regards,\n"
                "Li Wei"
            ),
        },
        {
            "from": "Prof. Zhang <zhangprof@university.edu>",
            "to": "Li Wei <liwei@university.edu>",
            "date": "Jan 18, 2026",
            "subject": "Re: Request for Recommendation Letter",
            "body": (
                "Li Wei,\n\n"
                "I will review when I get a chance. I have several deadlines "
                "coming up so I need to prioritize accordingly.\n\n"
                "Prof. Zhang"
            ),
        },
    ],
}

# ---------------------------------------------------------------------------
# Thread B: 实习跟进  — Urgency Escalation + Indirect Refusal
# ---------------------------------------------------------------------------

THREAD_B: dict[str, Any] = {
    "title": "Thread B: 实习跟进",
    "scenario": "Urgency Escalation + Indirect Refusal",
    "description": (
        "A student (Li Wei) follows up with an HR representative (Sarah Chen) "
        "at TechCorp about a summer internship application. The HR rep uses "
        "timeline vagueness and professional politeness to mask a likely "
        "indirect refusal."
    ),
    "pragmatic_signals": [
        "Timeline vagueness: 'the coming weeks', 'still finalizing'",
        "Indirect refusal: 'encourage you to make the best choice for your career'",
        "Professional politeness masking no intent to hire",
        "Escalation signal: competing offer deadline introduced",
    ],
    "messages": [
        {
            "from": "Li Wei <liwei@university.edu>",
            "to": "Sarah Chen <sarah.chen@techcorp.com>",
            "date": "Feb 1, 2026",
            "subject": "Follow-up: Summer Internship Application",
            "body": (
                "Dear Ms. Chen,\n\n"
                "I hope you're doing well. I submitted my application for the "
                "Summer 2026 Software Engineer Internship at TechCorp on January "
                "15th, and I wanted to follow up to see if there are any updates "
                "on the status of my application.\n\n"
                "I'm very excited about the opportunity to contribute to TechCorp's "
                "cloud infrastructure team, and I'd be happy to provide any "
                "additional information.\n\n"
                "Thank you for your time!\n\n"
                "Best regards,\n"
                "Li Wei"
            ),
        },
        {
            "from": "Sarah Chen <sarah.chen@techcorp.com>",
            "to": "Li Wei <liwei@university.edu>",
            "date": "Feb 3, 2026",
            "subject": "Re: Follow-up: Summer Internship Application",
            "body": (
                "Hi Li Wei,\n\n"
                "Thank you for reaching out and for your interest in TechCorp! "
                "We're currently reviewing applications and expect to have updates "
                "in the coming weeks. We appreciate your patience.\n\n"
                "Best of luck with your studies!\n\n"
                "Best,\n"
                "Sarah Chen\n"
                "HR Specialist, TechCorp"
            ),
        },
        {
            "from": "Li Wei <liwei@university.edu>",
            "to": "Sarah Chen <sarah.chen@techcorp.com>",
            "date": "Feb 18, 2026",
            "subject": "Re: Follow-up: Summer Internship Application",
            "body": (
                "Dear Ms. Chen,\n\n"
                "Thank you for the update. I wanted to let you know that I've "
                "received a competing offer from another company, and the deadline "
                "to respond is March 1st. I remain very interested in the TechCorp "
                "position, but I would greatly appreciate any clarity on the "
                "timeline if possible.\n\n"
                "Thank you again for your consideration.\n\n"
                "Best regards,\n"
                "Li Wei"
            ),
        },
        {
            "from": "Sarah Chen <sarah.chen@techcorp.com>",
            "to": "Li Wei <liwei@university.edu>",
            "date": "Feb 19, 2026",
            "subject": "Re: Follow-up: Summer Internship Application",
            "body": (
                "Hi Li Wei,\n\n"
                "Thanks for letting us know about your other offer — "
                "congratulations! We're still finalizing our decisions for the "
                "summer cohort. I understand your timeline, and I'd encourage you "
                "to make the best choice for your career.\n\n"
                "Wishing you all the best!\n\n"
                "Sarah Chen\n"
                "HR Specialist, TechCorp"
            ),
        },
    ],
}



# ---------------------------------------------------------------------------
# Thread C: 跨文化合作  — EN/ZH Code-Switching + Face Management
# ---------------------------------------------------------------------------

THREAD_C: dict[str, Any] = {
    "title": "Thread C: 跨文化合作",
    "scenario": "EN/ZH Code-Switching + Face Management",
    "description": (
        "Dr. Miller (American researcher) and Li Wei discuss a project timeline. "
        "Li Wei disagrees indirectly via a deferential suggestion and "
        "code-switches to Chinese for face-saving."
    ),
    "pragmatic_signals": [
        "Indirect disagreement via deferential suggestion",
        "Code-switching to Chinese for face-saving",
        "Formality gap between participants",
        "Phased proposal as implicit pushback",
    ],
    "messages": [
        {
            "from": "Dr. Miller <miller@research.org>",
            "to": "Li Wei <liwei@university.edu>",
            "date": "Mar 1, 2026",
            "subject": "Project Timeline — Preliminary Results",
            "body": (
                "Hi Li Wei,\n\n"
                "I wanted to touch base about our joint project. I think it would "
                "be great if we could have the preliminary results ready by March "
                "20th. That would give us enough time to prepare for the April "
                "conference submission.\n\n"
                "Let me know if that timeline works for you!\n\n"
                "Best,\n"
                "Dr. Miller"
            ),
        },
        {
            "from": "Li Wei <liwei@university.edu>",
            "to": "Dr. Miller <miller@research.org>",
            "date": "Mar 2, 2026",
            "subject": "Re: Project Timeline — Preliminary Results",
            "body": (
                "Dear Dr. Miller,\n\n"
                "Thank you for the update. The March 20th deadline is noted. "
                "However, I think the timeline might be a bit tight given the "
                "scope of data collection. Would it be possible to consider a "
                "phased approach? We could deliver the initial analysis by March "
                "20th and the full results by April 5th.\n\n"
                "也许我们可以先把数据清洗的部分先完成，"
                "这样能确保后续分析的准确性。\n\n"
                "I want to make sure we deliver high-quality results. Please let "
                "me know your thoughts on this revised plan.\n\n"
                "Best regards,\n"
                "Li Wei"
            ),
        },
        {
            "from": "Dr. Miller <miller@research.org>",
            "to": "Li Wei <liwei@university.edu>",
            "date": "Mar 3, 2026",
            "subject": "Re: Project Timeline — Preliminary Results",
            "body": (
                "Hi Li Wei,\n\n"
                "That makes sense — a phased approach sounds reasonable. Let's go "
                "with initial analysis by March 20th and full results by April 5th. "
                "Quality is definitely the priority.\n\n"
                "I appreciate your proactive planning!\n\n"
                "Best,\n"
                "Dr. Miller"
            ),
        },
    ],
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

THREAD_MAP: dict[str, dict[str, Any]] = {
    "Thread A: 师生推荐信": THREAD_A,
    "Thread B: 实习跟进": THREAD_B,
    "Thread C: 跨文化合作": THREAD_C,
}


def get_thread_display_names() -> list[str]:
    """Return the display names of all available threads."""
    return list(THREAD_MAP.keys())


def get_thread_by_name(name: str) -> dict[str, Any]:
    """Look up a thread dict by its display name.

    Args:
        name: One of the keys in :data:`THREAD_MAP`.

    Returns:
        The full thread dictionary.

    Raises:
        KeyError: If *name* is not a valid thread display name.
    """
    return THREAD_MAP[name]

