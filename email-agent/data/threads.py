"""Demo email thread data for SemanticMail."""

from __future__ import annotations

import email
import email.utils
import hashlib
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
# Thread D: 模糊请求  — Ambiguous Request + High-Context Dependency
# ---------------------------------------------------------------------------

THREAD_D: dict[str, Any] = {
    "title": "Thread D: 模糊请求",
    "scenario": "Ambiguous Request + High-Context Dependency",
    "description": (
        "A manager sends a vague email to a subordinate asking to 'look into' something "
        "without specifying what outcome they want. The subordinate over-interprets and "
        "delivers far more than expected. Tests whether the analyst detects the missing "
        "explicit ask and the subordinate's face-driven over-compliance."
    ),
    "pragmatic_signals": [
        "No explicit request or deadline — 'look into' is intentionally vague",
        "Subordinate over-delivers as face-saving strategy (guanxi maintenance)",
        "Manager's brevity may signal trust OR low priority — ambiguous",
        "Grice quantity violation: manager provides too little information",
    ],
    "messages": [
        {
            "from": "Director Wang <wangd@nextera-tech.com>",
            "to": "Chen Ming <chenming@nextera-tech.com>",
            "date": "Apr 7, 2026",
            "subject": "Competitor activity",
            "body": (
                "Ming,\n\n"
                "Could you look into what CloudSync has been doing lately? "
                "Heard they had a product update.\n\n"
                "Thanks,\n"
                "Wang"
            ),
        },
        {
            "from": "Chen Ming <chenming@nextera-tech.com>",
            "to": "Director Wang <wangd@nextera-tech.com>",
            "date": "Apr 9, 2026",
            "subject": "Re: Competitor activity",
            "body": (
                "Hi Director Wang,\n\n"
                "I've completed a competitive analysis of CloudSync's recent "
                "activities. Here's a summary:\n\n"
                "1. Product: Launched v3.0 on Mar 28 — new features include "
                "real-time collaboration and AI-powered search.\n\n"
                "2. Pricing: Shifted from per-seat to usage-based model. "
                "Entry tier dropped 30%. This targets our mid-market segment.\n\n"
                "3. Marketing: Sponsored three industry events in Q2. "
                "Keynote at DataSummit on Apr 15.\n\n"
                "4. Hiring: 12 open roles on their careers page, mostly "
                "in enterprise sales — suggests expansion push.\n\n"
                "5. Customer signals: Two of our prospects (FinCore, MedLink) "
                "attended their webinar last week.\n\n"
                "I've also prepared a one-page positioning comparison and a "
                "draft response strategy if we want to counter their pricing "
                "move before Q2. Happy to walk through it whenever convenient.\n\n"
                "Full deck attached (12 pages).\n\n"
                "Best regards,\n"
                "Chen Ming"
            ),
        },
        {
            "from": "Director Wang <wangd@nextera-tech.com>",
            "to": "Chen Ming <chenming@nextera-tech.com>",
            "date": "Apr 9, 2026",
            "subject": "Re: Competitor activity",
            "body": (
                "收到。另外下周一的会你准备一下Q2的pipeline update。\n\n"
                "Wang"
            ),
        },
    ],
}

# ---------------------------------------------------------------------------
# Thread E: 公开表扬  — Public Praise / Private Criticism
# ---------------------------------------------------------------------------

THREAD_E: dict[str, Any] = {
    "title": "Thread E: 公开表扬",
    "scenario": "Public Praise Masking Private Criticism",
    "description": (
        "A team lead CCs the department head while praising a team member's work, but "
        "the praised work has subtle issues. The real message is performative — the lead "
        "is managing their own face with the boss while subtly pressuring the subordinate "
        "to fix problems without being asked directly."
    ),
    "pragmatic_signals": [
        "CC to superior as audience-widening power move",
        "Praise contains embedded correction hints ('thorough, though we could refine X')",
        "Public vs private face management: praising publicly to avoid private confrontation",
        "Brown & Levinson: positive politeness strategy masking a face-threatening act to subordinate",
    ],
    "messages": [
        {
            "from": "Liu Fang <liufang@orion-group.com>",
            "to": "Zhao Yun <zhaoyun@orion-group.com>",
            "cc": "VP Chen <chenwp@orion-group.com>",
            "date": "Apr 10, 2026",
            "subject": "Q1 Market Analysis — nice work",
            "body": (
                "Hi Zhao Yun,\n\n"
                "Great job on the Q1 market analysis — it's comprehensive and "
                "well-structured. The competitive landscape section in particular "
                "is very thorough.\n\n"
                "A few areas we could sharpen for next time:\n"
                "- The Q3 revenue comparison uses 2024 data rather than 2025 "
                "audited figures\n"
                "- The market sizing assumptions might benefit from cross-referencing "
                "with our internal pipeline data\n"
                "- The executive summary could be more concise — leadership tends "
                "to prefer half a page\n\n"
                "Overall solid work. Looking forward to the next one!\n\n"
                "Best,\n"
                "Liu Fang"
            ),
        },
        {
            "from": "Zhao Yun <zhaoyun@orion-group.com>",
            "to": "Liu Fang <liufang@orion-group.com>",
            "cc": "VP Chen <chenwp@orion-group.com>",
            "date": "Apr 10, 2026",
            "subject": "Re: Q1 Market Analysis — nice work",
            "body": (
                "Hi Liu Fang,\n\n"
                "Thank you for the feedback! You're right — I'll update the Q3 "
                "comparison with the 2025 audited numbers and cross-reference the "
                "market sizing with pipeline data. I can send the revised version "
                "by Friday.\n\n"
                "Noted on the executive summary length as well.\n\n"
                "Thanks again for the guidance!\n\n"
                "Zhao Yun"
            ),
        },
        {
            "from": "Liu Fang <liufang@orion-group.com>",
            "to": "Zhao Yun <zhaoyun@orion-group.com>",
            "cc": "VP Chen <chenwp@orion-group.com>",
            "date": "Apr 10, 2026",
            "subject": "Re: Q1 Market Analysis — nice work",
            "body": (
                "Sounds good! No rush — whenever you have time is fine.\n\n"
                "Fang"
            ),
        },
    ],
}

# ---------------------------------------------------------------------------
# Thread F: 同事催办  — Peer Deadline Pressure Without Authority
# ---------------------------------------------------------------------------

THREAD_F: dict[str, Any] = {
    "title": "Thread F: 同事催办",
    "scenario": "Peer Deadline Pressure + No Authority Gradient",
    "description": (
        "A peer (not a manager) urgently needs a deliverable from a colleague. They have "
        "no formal authority but use escalating urgency language, social obligation appeals, "
        "and indirect guilt-tripping. Tests detection of power-less pressure tactics."
    ),
    "pragmatic_signals": [
        "No authority gradient — peer-to-peer, yet urgency escalates",
        "Social obligation framing: 'the team is counting on this'",
        "Passive-aggressive deadline reminders: 'just checking in again'",
        "Indirect guilt-trip: 'I don't want to delay everyone else'",
    ],
    "messages": [
        {
            "from": "Xu Jie <xujie@nextera-tech.com>",
            "to": "Lin Hao <linhao@nextera-tech.com>",
            "date": "Apr 14, 2026",
            "subject": "API integration docs for client demo",
            "body": (
                "Hey Lin Hao,\n\n"
                "Quick ask — would you be able to share the API integration "
                "docs for the payment module by end of this week? We're "
                "prepping for the FinCore demo and I want to make sure "
                "everything's aligned on the integration flow.\n\n"
                "No pressure if the timeline's tight — just let me know.\n\n"
                "Thanks!\n"
                "Jie"
            ),
        },
        {
            "from": "Lin Hao <linhao@nextera-tech.com>",
            "to": "Xu Jie <xujie@nextera-tech.com>",
            "date": "Apr 14, 2026",
            "subject": "Re: API integration docs for client demo",
            "body": (
                "Hey Jie,\n\n"
                "Will try my best — I'm a bit backed up with the v2.4 release "
                "right now. If I can get to it by Friday I will, but it might "
                "slip to early next week.\n\n"
                "Hao"
            ),
        },
        {
            "from": "Xu Jie <xujie@nextera-tech.com>",
            "to": "Lin Hao <linhao@nextera-tech.com>",
            "date": "Apr 17, 2026",
            "subject": "Re: API integration docs for client demo",
            "body": (
                "Hey Hao,\n\n"
                "Just circling back on this — the FinCore demo is Thursday "
                "morning and the team's counting on having the integration "
                "ready to show. I don't want to delay everyone else's prep.\n\n"
                "Is there any way to get even a draft version by tomorrow?\n\n"
                "Really appreciate it.\n"
                "Jie"
            ),
        },
        {
            "from": "Lin Hao <linhao@nextera-tech.com>",
            "to": "Xu Jie <xujie@nextera-tech.com>",
            "date": "Apr 18, 2026",
            "subject": "Re: API integration docs for client demo",
            "body": (
                "Jie,\n\n"
                "Here are the integration docs — API reference, auth flow, "
                "and error handling specs. Apologies for the delay, had to "
                "squeeze this in between release tasks.\n\n"
                "Hope this works for the demo.\n\n"
                "Hao"
            ),
        },
    ],
}

# ---------------------------------------------------------------------------
# Thread G: 抄送升级  — CC Escalation as Power Move
# ---------------------------------------------------------------------------

THREAD_G: dict[str, Any] = {
    "title": "Thread G: 抄送升级",
    "scenario": "CC Escalation + Audience Expansion as Leverage",
    "description": (
        "An email thread starts 1-on-1 between colleagues. When one party doesn't get "
        "the response they want, they add the other person's manager to CC. The added "
        "manager's brief reply changes the dynamic entirely. Tests detection of audience "
        "manipulation as a face-threatening act."
    ),
    "pragmatic_signals": [
        "CC addition of manager as implicit escalation/threat",
        "Original respondent's tone shift after manager appears on thread",
        "Manager's terse reply as implicit endorsement of one side",
        "Power recalibration mid-thread via audience change",
    ],
    "messages": [
        {
            "from": "Zhang Wei <zhangwei@nextera-tech.com>",
            "to": "Li Bo <libo@nextera-tech.com>",
            "date": "Mar 20, 2026",
            "subject": "CRM export tool access request",
            "body": (
                "Hi Li Bo,\n\n"
                "I need access to the CRM bulk export tool for the quarterly "
                "client report. Could you set that up for my account?\n\n"
                "Thanks,\n"
                "Zhang Wei\n"
                "Sales Manager"
            ),
        },
        {
            "from": "Li Bo <libo@nextera-tech.com>",
            "to": "Zhang Wei <zhangwei@nextera-tech.com>",
            "date": "Mar 20, 2026",
            "subject": "Re: CRM export tool access request",
            "body": (
                "Hi Zhang Wei,\n\n"
                "Unfortunately that tool is restricted to admin-level accounts "
                "per our data security policy. I can't grant access without "
                "formal approval from IT leadership.\n\n"
                "If you need the export, you can submit a data request ticket "
                "and we'll generate it for you within 48 hours.\n\n"
                "Best,\n"
                "Li Bo\n"
                "IT Support"
            ),
        },
        {
            "from": "Zhang Wei <zhangwei@nextera-tech.com>",
            "to": "Li Bo <libo@nextera-tech.com>",
            "cc": "Ma Director <madir@nextera-tech.com>",
            "date": "Mar 21, 2026",
            "subject": "Re: CRM export tool access request",
            "body": (
                "Hi Li Bo,\n\n"
                "Understood on the policy. The issue is that we have a client "
                "presentation on Monday and the 48-hour ticket turnaround "
                "won't work for this timeline.\n\n"
                "I'm sure we can find a solution that works within policy — "
                "perhaps a temporary read-only access window, or an expedited "
                "ticket? I'd really appreciate any flexibility here.\n\n"
                "Thanks,\n"
                "Zhang Wei"
            ),
        },
        {
            "from": "Ma Director <madir@nextera-tech.com>",
            "to": "Li Bo <libo@nextera-tech.com>",
            "cc": "Zhang Wei <zhangwei@nextera-tech.com>",
            "date": "Mar 21, 2026",
            "subject": "Re: CRM export tool access request",
            "body": (
                "Li Bo — set up temporary read-only access for Zhang Wei's "
                "team through end of next week. We can review the policy "
                "after Q1 close.\n\n"
                "Ma"
            ),
        },
    ],
}

# ---------------------------------------------------------------------------
# Thread H: 过度敬语  — Deference Overload Signaling Dissatisfaction
# ---------------------------------------------------------------------------

THREAD_H: dict[str, Any] = {
    "title": "Thread H: 过度敬语",
    "scenario": "Excessive Politeness as Passive Resistance",
    "description": (
        "An employee responds to a new policy or request with extreme formality and "
        "excessive deference — far beyond normal workplace norms. The hyper-politeness "
        "signals disagreement or resentment rather than genuine respect. Tests whether the "
        "analyst detects politeness-as-hostility (ironic politeness)."
    ),
    "pragmatic_signals": [
        "Politeness level exceeds relationship norms — ironic politeness",
        "Excessive honorifics and hedging: 'If it wouldn't be too much trouble...'",
        "Every sentence is grammatically polite but pragmatically resistant",
        "Brown & Levinson: over-use of negative politeness as off-record refusal",
    ],
    "messages": [
        {
            "from": "Huang Lei <huanglei@meridian-agency.com>",
            "to": "Su Qin <suqin@meridian-agency.com>",
            "date": "May 5, 2026",
            "subject": "Landing page revisions",
            "body": (
                "Hey Su Qin,\n\n"
                "Client came back with feedback on the landing page. "
                "They want the hero section redesigned and the CTA copy "
                "changed. Could you get a revised version to them by Monday?\n\n"
                "I know it's short notice — let me know if that's doable.\n\n"
                "Thanks,\n"
                "Huang Lei"
            ),
        },
        {
            "from": "Su Qin <suqin@meridian-agency.com>",
            "to": "Huang Lei <huanglei@meridian-agency.com>",
            "date": "May 5, 2026",
            "subject": "Re: Landing page revisions",
            "body": (
                "Dear Huang Lei,\n\n"
                "Thank you very much for passing along the client's feedback. "
                "I completely understand the urgency.\n\n"
                "如果您看方便的话，我想确认一下—— revised hero section "
                "的参考风格是否有具体方向？ If it's not too much trouble, "
                "could we perhaps get the client's preferred references before "
                "I start the redesign?\n\n"
                "如果时间允许的话， I wonder if we might also clarify "
                "whether the CTA copy changes should go through the usual "
                "copy review process, or if this is a direct client edit.\n\n"
                "不知道是否可以考虑把 deadline 调整到周二？ "
                "I want to make sure we deliver something the client is "
                "truly happy with, and Monday might be a bit rushed.\n\n"
                "麻烦您帮忙跟 client 确认一下，非常感谢！\n\n"
                "Best regards,\n"
                "Su Qin"
            ),
        },
        {
            "from": "Huang Lei <huanglei@meridian-agency.com>",
            "to": "Su Qin <suqin@meridian-agency.com>",
            "date": "May 6, 2026",
            "subject": "Re: Landing page revisions",
            "body": (
                "Thanks Su Qin!\n\n"
                "Just go with the modern/clean direction — client mentioned "
                "Stripe's landing page as reference. CTA copy is a direct "
                "client edit, no review needed.\n\n"
                "Monday deadline stands — client's presenting to their board "
                "Tuesday morning. Just send it when it's ready.\n\n"
                "Huang Lei"
            ),
        },
    ],
}

# ---------------------------------------------------------------------------
# Thread I: 简短回复  — Brevity as Power Signal
# ---------------------------------------------------------------------------

THREAD_I: dict[str, Any] = {
    "title": "Thread I: 简短回复",
    "scenario": "Brevity + Terse Replies as Power Marker",
    "description": (
        "A senior person replies to detailed emails with one-word or very short responses "
        "('Noted.', 'Fine.', 'Send it.'). The brevity itself is the pragmatic signal — it "
        "communicates dominance, dismissal, or controlled urgency. Tests detection of "
        "silence/brevity as a pragmatic device."
    ),
    "pragmatic_signals": [
        "One-word replies: 'Noted.', 'Fine.', 'Send it.' — brevity as power",
        "No reciprocation of warmth or elaboration",
        "Grice manner violation: deliberately uninformative",
        "Asymmetry in message length mirrors power asymmetry",
    ],
    "messages": [
        {
            "from": "Yang Fan <yangfan@crest-consulting.com>",
            "to": "Managing Director Guo <guomd@crest-consulting.com>",
            "date": "Feb 10, 2026",
            "subject": "Strategic options for XinHua engagement",
            "body": (
                "Dear Managing Director Guo,\n\n"
                "I've prepared three strategic options for the XinHua Group "
                "engagement, as discussed in last week's partner meeting:\n\n"
                "Option 1 — Full digital transformation consulting ($2.4M, "
                "12 months). Highest revenue but stretches our delivery team. "
                "Requires hiring 4 additional consultants.\n\n"
                "Option 2 — Focused operations optimization ($1.1M, 6 months). "
                "Better margins, leverages existing team capacity. "
                "Lower risk but smaller footprint.\n\n"
                "Option 3 — Diagnostic phase only ($280K, 8 weeks). "
                "Low commitment entry. Builds relationship for larger "
                "follow-on engagement in Q3-Q4.\n\n"
                "My recommendation is Option 2 — it balances revenue, "
                "deliverability, and positions us well for expansion. "
                "I've attached the full analysis with financial modeling.\n\n"
                "Would appreciate your thoughts on which direction to "
                "take to the client meeting on Friday.\n\n"
                "Best regards,\n"
                "Yang Fan\n"
                "Associate Consultant"
            ),
        },
        {
            "from": "Managing Director Guo <guomd@crest-consulting.com>",
            "to": "Yang Fan <yangfan@crest-consulting.com>",
            "date": "Feb 11, 2026",
            "subject": "Re: Strategic options for XinHua engagement",
            "body": "Fine.\n",
        },
        {
            "from": "Yang Fan <yangfan@crest-consulting.com>",
            "to": "Managing Director Guo <guomd@crest-consulting.com>",
            "date": "Feb 11, 2026",
            "subject": "Re: Strategic options for XinHua engagement",
            "body": (
                "Dear Managing Director Guo,\n\n"
                "Thank you. Just to confirm a few details:\n\n"
                "- Should I proceed with Option 2 as recommended?\n"
                "- Do we need partner-level approval for the $1.1M scope, "
                "or can I move forward with the client discussion?\n"
                "- For the Friday meeting, would you like me to present "
                "all three options or focus on Option 2?\n\n"
                "Happy to adjust based on your preference.\n\n"
                "Yang Fan"
            ),
        },
        {
            "from": "Managing Director Guo <guomd@crest-consulting.com>",
            "to": "Yang Fan <yangfan@crest-consulting.com>",
            "date": "Feb 12, 2026",
            "subject": "Re: Strategic options for XinHua engagement",
            "body": "Option 2. Proceed.\n",
        },
    ],
}

# ---------------------------------------------------------------------------
# Thread J: 道歉推诿  — Apology with Blame Deflection
# ---------------------------------------------------------------------------

THREAD_J: dict[str, Any] = {
    "title": "Thread J: 道歉推诿",
    "scenario": "Apology + Blame Deflection + Face Preservation",
    "description": (
        "Someone apologizes for a mistake but the apology is structured to shift blame — "
        "'I'm sorry, but if the requirements had been clearer...' The recipient must "
        "detect the face-saving deflection embedded in the apology. Tests analysis of "
        "compound speech acts (apology + accusation)."
    ),
    "pragmatic_signals": [
        "Apology structured with blame-shifting: 'I'm sorry, but...'",
        "Compound speech act: surface apology + implicit accusation",
        "Face management: apologizing to save face while deflecting to preserve positive face",
        "Hedging and conditional framing to weaken the apology",
    ],
    "messages": [
        {
            "from": "Wu Dan <wudan@skyline-pharma.com>",
            "to": "Tian Rong <tianrong@pixel-creative.com>",
            "date": "Apr 2, 2026",
            "subject": "Deliverable — wrong brand assets",
            "body": (
                "Hi Tian Rong,\n\n"
                "I'm reviewing the campaign materials your team delivered "
                "yesterday. I noticed the digital ads are using the old brand "
                "colors (teal gradient) and the previous-generation logo without "
                "the registered trademark mark.\n\n"
                "The updated brand guidelines were part of the original brief. "
                "Can you confirm when the corrected versions will be ready?\n\n"
                "Thanks,\n"
                "Wu Dan\n"
                "Project Lead, Skyline Pharma"
            ),
        },
        {
            "from": "Tian Rong <tianrong@pixel-creative.com>",
            "to": "Wu Dan <wudan@skyline-pharma.com>",
            "date": "Apr 2, 2026",
            "subject": "Re: Deliverable — wrong brand assets",
            "body": (
                "Dear Wu Dan,\n\n"
                "I sincerely apologize for any confusion regarding the brand "
                "assets used in the campaign materials.\n\n"
                "Upon reviewing our project files, I notice that the brand "
                "guidelines document we received was dated January 2025, which "
                "may have been superseded. To avoid similar issues in the "
                "future, it would be very helpful if your team could share "
                "updated guidelines and confirm them before we begin creative "
                "production.\n\n"
                "Additionally, if the brand standards team could be available "
                "for a brief alignment call during the creative development "
                "phase, that would ensure we're fully aligned with Skyline's "
                "latest brand direction.\n\n"
                "We're committed to delivering work that meets your "
                "expectations. I'll have the corrected files to you by "
                "Thursday.\n\n"
                "Best regards,\n"
                "Tian Rong\n"
                "Creative Director, Pixel Creative"
            ),
        },
        {
            "from": "Wu Dan <wudan@skyline-pharma.com>",
            "to": "Tian Rong <tianrong@pixel-creative.com>",
            "date": "Apr 2, 2026",
            "subject": "Re: Deliverable — wrong brand assets",
            "body": (
                "Tian Rong,\n\n"
                "The updated guidelines (v3.2, February 2026) were attached to "
                "the original creative brief sent on March 3rd. The alignment "
                "call was also offered during scoping.\n\n"
                "Thursday works for the corrected files.\n\n"
                "Wu Dan"
            ),
        },
    ],
}

# ---------------------------------------------------------------------------
# Thread K: 跨部门协作  — Cross-Department Request via Guanxi
# ---------------------------------------------------------------------------

THREAD_K: dict[str, Any] = {
    "title": "Thread K: 跨部门协作",
    "scenario": "Cross-Department Request + Guanxi Leverage",
    "description": (
        "Someone needs a favor from another department where they have no direct authority. "
        "They invoke a shared relationship ('I heard from Xiao Wang that you...') and "
        "frame the request as mutually beneficial. Tests detection of relational capital "
        "deployment and indirect persuasion."
    ),
    "pragmatic_signals": [
        "Third-party name-dropping as social proof and guanxi activation",
        "Request framed as mutual benefit rather than personal favor",
        "No formal authority — persuasion through relational obligation",
        "Spencer-Oatey: sociality rights and obligation face management",
    ],
    "messages": [
        {
            "from": "Cheng Yu <chengyu@nextera-tech.com>",
            "to": "Peng Jie <pengjie@nextera-tech.com>",
            "date": "Apr 22, 2026",
            "subject": "User engagement data for Q2 campaign",
            "body": (
                "Hey Peng Jie,\n\n"
                "Xiao Liu mentioned you're the go-to person for user behavior "
                "data on the Analytics team. I'm putting together our Q2 "
                "campaign strategy and could really use some engagement "
                "metrics — DAU trends, feature adoption rates, and retention "
                "cohort data for the past quarter.\n\n"
                "This could actually help both our teams — I'm presenting to "
                "leadership next week and I'd love to include your team's "
                "insights as part of the data-driven strategy story. Good "
                "visibility for everyone.\n\n"
                "Totally understand if your plate is full. Just thought I'd ask!\n\n"
                "Cheers,\n"
                "Cheng Yu\n"
                "Marketing"
            ),
        },
        {
            "from": "Peng Jie <pengjie@nextera-tech.com>",
            "to": "Cheng Yu <chengyu@nextera-tech.com>",
            "date": "Apr 22, 2026",
            "subject": "Re: User engagement data for Q2 campaign",
            "body": (
                "Hey Cheng Yu!\n\n"
                "Liu was too kind — I'm one of a few who work with that data, "
                "but happy to help where I can.\n\n"
                "DAU trends and feature adoption I can pull fairly easily. "
                "Retention cohorts are a bit more involved since they need "
                "custom segmentation. What granularity do you need?\n\n"
                "I do have a backlog of requests from my own team, so I might "
                "not be able to get to it until next week. Would that still "
                "work for your timeline?\n\n"
                "Best,\n"
                "Peng Jie"
            ),
        },
        {
            "from": "Cheng Yu <chengyu@nextera-tech.com>",
            "to": "Peng Jie <pengjie@nextera-tech.com>",
            "date": "Apr 22, 2026",
            "subject": "Re: User engagement data for Q2 campaign",
            "body": (
                "Peng Jie, you're a lifesaver!\n\n"
                "DAU and feature adoption by week would be perfect. For "
                "retention, monthly cohorts are fine — don't need anything "
                "too granular.\n\n"
                "Next week is totally fine — even a rough cut by Wednesday "
                "would be amazing. And I'll definitely make sure your team's "
                "contribution is highlighted in the leadership deck :)\n\n"
                "Thanks again!\n"
                "Cheng Yu"
            ),
        },
    ],
}

# ---------------------------------------------------------------------------
# Thread L: 好消息背后  — Good News Sandwiching Bad News
# ---------------------------------------------------------------------------

THREAD_L: dict[str, Any] = {
    "title": "Thread L: 好消息背后",
    "scenario": "Positive Framing Masking Negative Information",
    "description": (
        "A manager announces a 'restructuring' using entirely positive language — 'exciting "
        "new opportunities', 'streamlined teams' — while the practical implications are "
        "negative for the recipient. Tests whether the analyst sees through corporate "
        "euphemism and detects the face threat beneath positive framing."
    ),
    "pragmatic_signals": [
        "Corporate euphemism: 'restructuring', 'exciting opportunities', 'streamlined'",
        "Positive framing masking negative implications (layoffs, role changes)",
        "Grice quality violation: literal words are positive, intended meaning is negative",
        "Brown & Levinson: positive politeness strategy to soften a major face-threatening act",
    ],
    "messages": [
        {
            "from": "VP Shen <shen@orion-group.com>",
            "to": "Product Team <product-team@orion-group.com>",
            "date": "May 12, 2026",
            "subject": "Exciting organizational update — Product team evolution",
            "body": (
                "Hi Product Team,\n\n"
                "I'm thrilled to share some exciting news about the next phase "
                "of our product organization's evolution.\n\n"
                "As we continue to scale, we're creating a more agile and "
                "customer-focused structure. Some of our teams will be "
                "streamlined to accelerate decision-making and reduce overhead. "
                "This evolution will create exciting new opportunities for "
                "many of you to take on expanded roles with greater scope "
                "and visibility.\n\n"
                "To ensure a smooth transition, we'll be hosting individual "
                "sessions next week where each of you can learn about your "
                "exciting new path within the organization.\n\n"
                "I want to thank all of you for your incredible work. "
                "The future is bright, and I'm confident this evolution "
                "will unlock even greater impact.\n\n"
                "Warmly,\n"
                "VP Shen"
            ),
        },
        {
            "from": "Zhou Xin <zhouxin@orion-group.com>",
            "to": "VP Shen <shen@orion-group.com>",
            "date": "May 12, 2026",
            "subject": "Re: Exciting organizational update — Product team evolution",
            "body": (
                "Hi VP Shen,\n\n"
                "Thanks for sharing the update. Could you share more details "
                "on what the 'expanded roles' and 'streamlined structure' "
                "would look like for the product design sub-team specifically? "
                "Want to make sure we're prepared for the individual sessions "
                "next week.\n\n"
                "Thanks,\n"
                "Zhou Xin"
            ),
        },
    ],
}

# ---------------------------------------------------------------------------
# Thread M: 战略性沉默  — Strategic Non-Response / Delayed Reply
# ---------------------------------------------------------------------------

THREAD_M: dict[str, Any] = {
    "title": "Thread M: 战略性沉默",
    "scenario": "Response Delay as Power Play",
    "description": (
        "A senior person systematically delays responses to a subordinate's emails. The "
        "delays correlate with the importance of the request — more important asks get "
        "longer silences. When they do respond, it's brief and noncommittal. Tests "
        "detection of strategic silence as a pragmatic device."
    ),
    "pragmatic_signals": [
        "Response delays correlate with request importance — strategic timing",
        "Brief, noncommittal replies when they do respond",
        "Silence as implicit power assertion: 'your request is not my priority'",
        "Grice quantity violation: deliberate under-informativeness",
    ],
    "messages": [
        {
            "from": "Ren Xia <renxia@zju.edu.cn>",
            "to": "Prof. Liang <lianghq@zju.edu.cn>",
            "date": "Mar 16, 2026",
            "subject": "Conference travel budget — ACM SIGCHI 2026",
            "body": (
                "Dear Prof. Liang,\n\n"
                "I'd like to request approval for conference travel budget to "
                "attend ACM SIGCHI 2026 in Osaka (May 5-8). Registration is "
                "$800, estimated travel and accommodation $1,500. Total ~$2,300.\n\n"
                "Our paper was accepted as a short paper, so this is a good "
                "visibility opportunity for the lab.\n\n"
                "Best,\n"
                "Ren Xia"
            ),
        },
        {
            "from": "Prof. Liang <lianghq@zju.edu.cn>",
            "to": "Ren Xia <renxia@zju.edu.cn>",
            "date": "Mar 17, 2026",
            "subject": "Re: Conference travel budget — ACM SIGCHI 2026",
            "body": (
                "Approved. Submit through the finance portal.\n\n"
                "Liang"
            ),
        },
        {
            "from": "Ren Xia <renxia@zju.edu.cn>",
            "to": "Prof. Liang <lianghq@zju.edu.cn>",
            "date": "Mar 18, 2026",
            "subject": "RA hiring — additional research assistant for summer project",
            "body": (
                "Dear Prof. Liang,\n\n"
                "Following up on our discussion last month about expanding the "
                "team for the summer data collection project. I'd like to "
                "formally request hiring one additional research assistant "
                "(RA) starting in May.\n\n"
                "The workload for the annotation pipeline is about 40% larger "
                "than originally scoped. With one more RA, we can meet the "
                "August paper deadline without compromising quality.\n\n"
                "Budget estimate: ¥6,000/month for 4 months = ¥24,000 total. "
                "This would come from the project grant (NSFC-2024-1147).\n\n"
                "Happy to prepare a formal budget justification if needed.\n\n"
                "Best,\n"
                "Ren Xia"
            ),
        },
        {
            "from": "Ren Xia <renxia@zju.edu.cn>",
            "to": "Prof. Liang <lianghq@zju.edu.cn>",
            "date": "Mar 24, 2026",
            "subject": "Re: RA hiring — additional research assistant for summer project",
            "body": (
                "Dear Prof. Liang,\n\n"
                "Gentle reminder — following up on the RA hiring request from "
                "last week. The student I had in mind has another offer "
                "pending, so I'd need to confirm with them soon if we'd like "
                "to proceed.\n\n"
                "Please let me know if you need any additional information.\n\n"
                "Best,\n"
                "Ren Xia"
            ),
        },
        {
            "from": "Prof. Liang <lianghq@zju.edu.cn>",
            "to": "Ren Xia <renxia@zju.edu.cn>",
            "date": "Mar 26, 2026",
            "subject": "Re: RA hiring — additional research assistant for summer project",
            "body": (
                "Ren Xia,\n\n"
                "Let's discuss when the semester starts. There are several "
                "factors to consider regarding the grant allocation.\n\n"
                "Liang"
            ),
        },
    ],
}

# ---------------------------------------------------------------------------
# Thread N: 称呼转变  — Formality Shift Mid-Thread
# ---------------------------------------------------------------------------

THREAD_N: dict[str, Any] = {
    "title": "Thread N: 称呼转变",
    "scenario": "Formality Shift Signaling Relationship Transition",
    "description": (
        "Two colleagues who have been using informal language gradually shift to formal "
        "address mid-thread after a disagreement. The formality shift signals relational "
        "cooling — a withdrawal of intimacy. Tests whether the analyst tracks address form "
        "changes as pragmatic markers of relationship state."
    ),
    "pragmatic_signals": [
        "Address shift: first name → title + surname after disagreement",
        "Tone vocabulary shift: casual → formal as relationship cools",
        "Formality increase as face-distancing strategy",
        "Spencer-Oatey: rapport-neglect signaled through stylistic downgrade",
    ],
    "messages": [
        {
            "from": "Dr. Qian Bo <qianbo@zju.edu.cn>",
            "to": "Dr. Sun Wei <sunwei@zju.edu.cn>",
            "date": "Jun 2, 2026",
            "subject": "Draft feedback",
            "body": (
                "Hey Sun Wei,\n\n"
                "Great work on the first draft! Really solid overall. "
                "A few tweaks and we're golden:\n\n"
                "- The methodology section could use more detail on the "
                "participant recruitment process\n"
                "- Related work is missing the Chen et al. 2025 paper\n"
                "- Discussion feels a bit thin — can you connect the "
                "findings back to RQ2 more explicitly?\n\n"
                "Other than that, looking good. Let's aim to submit by "
                "end of month!\n\n"
                "Cheers,\n"
                "Qian Bo"
            ),
        },
        {
            "from": "Dr. Sun Wei <sunwei@zju.edu.cn>",
            "to": "Dr. Qian Bo <qianbo@zju.edu.cn>",
            "date": "Jun 2, 2026",
            "subject": "Re: Draft feedback",
            "body": (
                "Hey Qian Bo,\n\n"
                "Thanks! Glad you liked it overall.\n\n"
                "On the methodology point — actually, I think the recruitment "
                "process is already well-described in Section 3.2. We included "
                "the screening criteria, incentive structure, and demographic "
                "breakdown. The reviewers at CHI specifically commended this "
                "section last year.\n\n"
                "I'll add the Chen et al. citation and expand the RQ2 "
                "connection in the discussion.\n\n"
                "Best,\n"
                "Sun Wei"
            ),
        },
        {
            "from": "Dr. Qian Bo <qianbo@zju.edu.cn>",
            "to": "Dr. Sun Wei <sunwei@zju.edu.cn>",
            "date": "Jun 3, 2026",
            "subject": "Re: Draft feedback",
            "body": (
                "Sun Wei,\n\n"
                "Right, but the submission guidelines changed this cycle. "
                "They now require explicit IRB documentation details in the "
                "methodology, not just the recruitment criteria. We should "
                "probably update it to be safe.\n\n"
                "Qian Bo"
            ),
        },
        {
            "from": "Dr. Sun Wei <sunwei@zju.edu.cn>",
            "to": "Dr. Qian Bo <qianbo@zju.edu.cn>",
            "date": "Jun 3, 2026",
            "subject": "Re: Draft feedback",
            "body": (
                "Dear Dr. Qian,\n\n"
                "Thank you for the additional feedback. I have reviewed the "
                "updated submission guidelines and confirmed that Section 3.2 "
                "already addresses the IRB documentation requirements "
                "(approval number, consent process, data handling protocol).\n\n"
                "Please let me know if there are specific revisions you would "
                "like me to make, and I will incorporate them accordingly.\n\n"
                "Sincerely,\n"
                "Dr. Sun Wei"
            ),
        },
        {
            "from": "Dr. Qian Bo <qianbo@zju.edu.cn>",
            "to": "Dr. Sun Wei <sunwei@zju.edu.cn>",
            "date": "Jun 3, 2026",
            "subject": "Re: Draft feedback",
            "body": (
                "Dr. Sun —\n\n"
                "Understood. I will send specific comments by end of week.\n\n"
                "Dr. Qian"
            ),
        },
    ],
}

# ---------------------------------------------------------------------------
# Thread O: 纯信息交换  — True Negative (No Subtext)
# ---------------------------------------------------------------------------

THREAD_O: dict[str, Any] = {
    "title": "Thread O: 纯信息交换",
    "scenario": "Straightforward Information Exchange (True Negative)",
    "description": (
        "A simple factual exchange between two colleagues with no power dynamics, "
        "no face management, no hedging, and no subtext. Used to test PIC's false "
        "positive rate — if it reports significant pragmatic signals here, the "
        "framework is over-reading."
    ),
    "pragmatic_signals": [
        "No pragmatic signals expected — this is a true negative control",
        "Direct question, direct answer, no ambiguity",
        "No power asymmetry, no face threats, no indirect speech acts",
    ],
    "messages": [
        {
            "from": "Zhang Hao <zhanghao@nextera-tech.com>",
            "to": "Li Mei <limei@nextera-tech.com>",
            "date": "Apr 28, 2026",
            "subject": "VPN server address?",
            "body": (
                "Hi Li Mei,\n\n"
                "What's the VPN server address for the staging environment? "
                "I need to connect to test the API endpoints.\n\n"
                "Thanks,\n"
                "Zhang Hao"
            ),
        },
        {
            "from": "Li Mei <limei@nextera-tech.com>",
            "to": "Zhang Hao <zhanghao@nextera-tech.com>",
            "date": "Apr 28, 2026",
            "subject": "Re: VPN server address?",
            "body": (
                "Hey Zhang Hao,\n\n"
                "It's vpn-staging.nextera-tech.com. Use your SSO credentials "
                "to log in. Port is 443.\n\n"
                "Let me know if you have trouble connecting.\n\n"
                "Li Mei"
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
    "Thread D: 模糊请求": THREAD_D,
    "Thread E: 公开表扬": THREAD_E,
    "Thread F: 同事催办": THREAD_F,
    "Thread G: 抄送升级": THREAD_G,
    "Thread H: 过度敬语": THREAD_H,
    "Thread I: 简短回复": THREAD_I,
    "Thread J: 道歉推诿": THREAD_J,
    "Thread K: 跨部门协作": THREAD_K,
    "Thread L: 好消息背后": THREAD_L,
    "Thread M: 战略性沉默": THREAD_M,
    "Thread N: 称呼转变": THREAD_N,
    "Thread O: 纯信息交换": THREAD_O,
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


def build_thread_from_raw(raw_text: str) -> dict[str, Any]:
    """Parse raw email text into a THREAD_MAP-shaped dict for ad-hoc analysis.

    Accepts RFC 822/.eml-style input (headers + blank line + body) or loose
    body-only text. Output schema matches THREAD_A/THREAD_B/etc. so all
    downstream UI tabs render without modification.

    The MD5 digest of the raw input is embedded in the title for traceability
    and acts as a stable cache key across Streamlit reruns.

    Args:
        raw_text: Raw email text, optionally with RFC 822 headers.

    Returns:
        Thread dict with title/description/scenario/pragmatic_signals/messages.
    """
    raw_text = (raw_text or "").strip()
    digest = hashlib.md5(raw_text.encode("utf-8")).hexdigest()[:12]

    msg = email.message_from_string(raw_text)

    from_raw = msg.get("From", "") or "Unknown Sender"
    from_display, _ = email.utils.parseaddr(from_raw)
    from_field = from_display or from_raw

    subject = msg.get("Subject", "") or "(no subject)"
    date = msg.get("Date", "") or "(unknown date)"
    to = msg.get("To", "") or ""

    if msg.is_multipart():
        body_parts = []
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body_parts.append(part.get_payload(decode=False) or "")
        body = "\n".join(body_parts).strip()
    else:
        body = (msg.get_payload(decode=False) or "").strip()

    if not body:
        body = raw_text

    return {
        "title": f"✍️ Pasted Email ({digest})",
        "scenario": "User-pasted email (ad-hoc analysis)",
        "description": (
            "Email pasted directly into the UI for ad-hoc pragmatic analysis. "
            "Pre-computed pragmatic signals are not available — the PIC chain "
            "derives everything from the message content."
        ),
        "pragmatic_signals": [],
        "messages": [
            {
                "from": from_field,
                "to": to,
                "date": date,
                "subject": subject,
                "body": body,
            }
        ],
    }

