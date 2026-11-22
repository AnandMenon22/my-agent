"""Demo mode: the same agent steps without an AI key, using simple keyword rules.

Sorts each test-metric line by looking for QA-specific words, extracts owners and dates,
and flags questions for anything missing. A real AI model (add your key) does this far better.
"""
import re

SECTIONS = ["Passed", "Failed", "Blocked", "Risks", "Next Sprint"]

KEYWORDS = {
    "Blocked":     ["blocked", "waiting on", "waiting for", "environment down", "no access",
                    "cannot execute", "pending", "dependency"],
    "Failed":      ["failed", "fail", "defect", "bug", "error", "tc-", "critical", "severity",
                    "broken", "did not pass", "not passed"],
    "Risks":       ["risk", "delay", "may slip", "might miss", "could affect", "concern",
                    "behind", "tight", "jeopardise", "jeopardize", "at risk", "demo"],
    "Next Sprint": ["next sprint", "next week", "planned", "plan to", "will execute",
                    "going to", "target", "scheduled", "upcoming"],
}

NAME = re.compile(r"\b([A-Z][a-z]+)\s+(?:is|was|will|found|owns|fixed|raised|assigned|reported)\b")
DATE = re.compile(r"\b(\d{1,2}\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
                  r"|Monday|Tuesday|Wednesday|Thursday|Friday|Nov\s\d+|Dec\s\d+|next sprint)\b", re.I)
NUMBER = re.compile(r"\b(\d+)\b")


def _clean(line: str) -> str:
    return re.sub(r"^[\s\-\*•\d\.\)]+(?=[A-Za-z])", "", line).strip()


def _owner(line: str) -> str:
    m = NAME.search(line)
    return m.group(1) if m else ""


def demo_analyse(notes: str) -> dict:
    """Return the same structure the AI model returns (see agent.py)."""
    items = []
    for raw in notes.splitlines():
        line = _clean(raw)
        if not line:
            continue
        low = line.lower()
        section = "Passed"  # default: assume passed unless a keyword says otherwise
        for name in ("Blocked", "Failed", "Risks", "Next Sprint"):
            if any(w in low for w in KEYWORDS[name]):
                section = name
                break
        d = DATE.search(line)
        impact = "High" if section == "Blocked" else "Medium" if section in ("Failed", "Risks") else ""
        items.append({
            "section": section,
            "text": line,
            "owner": _owner(line),
            "due": d.group(1) if d else "",
            "impact": impact,
        })

    failed   = [i for i in items if i["section"] == "Failed"]
    blocked  = [i for i in items if i["section"] == "Blocked"]
    passed   = [i for i in items if i["section"] == "Passed"]
    risks    = [i for i in items if i["section"] == "Risks"]

    # Try to extract totals from raw notes for pass-rate calculation
    total_m  = re.search(r"(?:total|planned)[^\d]*(\d+)", notes, re.I)
    exec_m   = re.search(r"executed[^\d]*(\d+)", notes, re.I)
    pass_m   = re.search(r"passed[^\d]*(\d+)", notes, re.I)
    total    = int(total_m.group(1)) if total_m else None
    executed = int(exec_m.group(1)) if exec_m else None
    n_passed = int(pass_m.group(1)) if pass_m else None
    pass_rate = round(n_passed / executed * 100) if (n_passed and executed) else None

    if pass_rate is not None:
        status = "Green" if (pass_rate >= 90 and not any(
            "critical" in i["text"].lower() for i in failed + blocked)) \
            else "Amber" if pass_rate >= 75 else "Red"
        status_reason = f"Pass rate {pass_rate}% ({n_passed}/{executed} executed)."
    else:
        status = "Red" if len(blocked) >= 2 else "Amber" if blocked or failed else "Green"
        status_reason = f"{len(failed)} failed, {len(blocked)} blocked test case(s)."

    questions = []
    for i in failed + blocked:
        if not i["owner"]:
            questions.append(f"Who owns this, and when will it be resolved: \"{i['text'][:80]}\"?")
    if not items:
        questions.append("Not enough information: no QA notes were given.")

    def n(k, word):
        return f"{k} {word}" if k == 1 else f"{k} {word}s"

    headline_num = f"Pass rate {pass_rate}%" if pass_rate else f"{n(len(passed), 'item')} passed"
    lead = (failed + blocked)[0]["text"] if (failed or blocked) else "No failures or blockers reported"
    actions = [{"action": "Resolve: " + i["text"][:80], "owner": i["owner"], "why": i["section"]}
               for i in (blocked + failed)[:3]]
    email = (
        f"Hi,\n\nQA status this sprint is {status}. {headline_num}; "
        f"{n(len(failed), 'test case')} failed and {n(len(blocked), 'test case')} blocked. "
        f"Main issue: {lead[:100]}.\n\nFull report attached."
    )
    return {
        "headline": f"{status}: {headline_num}. Main concern — {lead[:100]}.",
        "summary": (f"{headline_num} this sprint. {n(len(failed), 'failure')} and "
                    f"{n(len(blocked), 'blocker')} require attention before sign-off."),
        "status": status,
        "status_reason": status_reason,
        "actions": actions,
        "decisions": [],
        "email": email,
        "items": items,
        "questions": questions[:5],
    }
