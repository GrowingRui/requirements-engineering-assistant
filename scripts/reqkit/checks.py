"""Deterministic quality checks (linting) for requirements.

These checks are heuristics. They produce *candidates* for the agent to review:
a flagged word is not automatically an ambiguity, and two similar requirements
are not automatically duplicates. The agent confirms or dismisses each finding
and records confirmed problems as issues in requirements.json.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import combinations
from typing import Any, Dict, Iterable, List, Sequence, Set, Tuple

from .model import Finding

# --- Ambiguity lexicon --------------------------------------------------------
# term -> what is missing / what a measurable refinement would need.

VAGUE_TERMS: Dict[str, str] = {
    "fast": "a measurable time target (e.g. response time at a percentile, under a stated load)",
    "quick": "a measurable time target",
    "quickly": "a measurable time target",
    "slow": "a measurable time threshold",
    "instant": "a measurable time target",
    "instantly": "a measurable time target",
    "real-time": "a maximum latency",
    "real time": "a maximum latency",
    "responsive": "a response-time target or the devices/screen sizes it must support",
    "easy": "who must achieve what, in how many steps or how much time, with what success rate",
    "easy to use": "a usability target (task, user group, success rate, time on task)",
    "user-friendly": "a usability target (task, user group, success rate, time on task)",
    "user friendly": "a usability target (task, user group, success rate, time on task)",
    "intuitive": "a usability target (e.g. first-time users complete a task without help)",
    "simple": "what must be simple, for whom, measured how",
    "seamless": "which transitions must work and what counts as an interruption",
    "secure": "which assets, which threats, and which controls (authentication, encryption, roles)",
    "safe": "which hazards must be prevented and how compliance is checked",
    "efficient": "which resource (time, memory, battery, cost) and the target value",
    "reliable": "an availability, error-rate or recovery target",
    "robust": "which failures or invalid inputs must be tolerated and the expected behaviour",
    "stable": "an availability, crash-rate or error-rate target",
    "highly available": "an availability target (e.g. percentage per month)",
    "flexible": "which changes must be supported and at what cost",
    "scalable": "the load to support (users, requests, data volume) and the growth expected",
    "large": "a numeric size or quantity",
    "small": "a numeric size or quantity",
    "many": "a number",
    "few": "a number",
    "several": "a number",
    "some": "which ones or how many",
    "most": "a percentage or a list",
    "accurate": "an accuracy metric and target (e.g. top-1 accuracy on a defined test set)",
    "precise": "a precision target and how it is measured",
    "high performance": "measurable performance targets",
    "high quality": "measurable quality criteria",
    "low latency": "a maximum latency",
    "modern": "concrete design or technology requirements",
    "good": "measurable acceptance criteria",
    "better": "a baseline and the improvement target",
    "best": "a measurable criterion; 'best' is not verifiable",
    "optimal": "the objective being optimised and its target",
    "adequate": "the threshold that counts as adequate",
    "sufficient": "the threshold that counts as sufficient",
    "appropriate": "the concrete rule for what is appropriate",
    "acceptable": "the threshold that counts as acceptable",
    "reasonable": "the concrete limit",
    "normal": "the definition of normal conditions (load, data, environment)",
    "minimal": "a numeric limit",
    "lightweight": "a size, memory or dependency limit",
    "frequently": "a frequency (e.g. every N minutes)",
    "regularly": "a frequency",
    "periodically": "a frequency",
    "as soon as possible": "a deadline or time limit",
    "approximately": "a tolerance range",
    "user-centric": "measurable user-experience criteria",
}

WEAK_PHRASES: Dict[str, str] = {
    "tbd": "the value is still to be determined",
    "tbc": "the value is still to be confirmed",
    "to be determined": "the value is still to be determined",
    "etc": "an open-ended list; enumerate the items",
    "and so on": "an open-ended list; enumerate the items",
    "and/or": "unclear whether both or either are required",
    "if possible": "makes the requirement optional; state the condition or priority",
    "where possible": "makes the requirement optional; state the condition or priority",
    "as needed": "the triggering condition is not defined",
    "as appropriate": "the rule for what is appropriate is not defined",
    "where applicable": "the cases where it applies are not listed",
    "including but not limited to": "an open-ended list; enumerate the items",
    "support for": "what 'support' must do is not defined",
}


@dataclass(frozen=True)
class TermMatch:
    term: str
    kind: str  # "vague" | "weak"
    explanation: str
    start: int
    end: int


def _compile(terms: Iterable[str]) -> re.Pattern:
    # Longest first so "easy to use" wins over "easy".
    ordered = sorted(terms, key=len, reverse=True)
    return re.compile(r"(?<![\w-])(" + "|".join(re.escape(t) for t in ordered) + r")(?![\w-])", re.IGNORECASE)


_VAGUE_RE = _compile(VAGUE_TERMS)
_WEAK_RE = _compile(WEAK_PHRASES)


def find_terms(text: str) -> List[TermMatch]:
    """Find vague terms and weak phrases in text (case-insensitive, whole words)."""
    matches: List[TermMatch] = []
    for m in _VAGUE_RE.finditer(text):
        term = m.group(1).lower()
        matches.append(TermMatch(term, "vague", VAGUE_TERMS[term], m.start(), m.end()))
    for m in _WEAK_RE.finditer(text):
        term = m.group(1).lower()
        matches.append(TermMatch(term, "weak", WEAK_PHRASES[term], m.start(), m.end()))
    return sorted(matches, key=lambda t: t.start)


def scan_text(text: str) -> List[Dict[str, Any]]:
    """Scan free text (e.g. the user's raw project description) line by line."""
    results: List[Dict[str, Any]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in find_terms(line):
            results.append({
                "line": lineno,
                "column": match.start + 1,
                "term": match.term,
                "kind": match.kind,
                "missing": match.explanation,
                "context": line.strip(),
            })
    return results


# --- Text similarity ----------------------------------------------------------

_STOPWORDS = {
    "the", "a", "an", "system", "shall", "must", "should", "will", "be", "able", "to", "of",
    "and", "or", "for", "in", "on", "with", "by", "is", "are", "it", "its", "their", "his",
    "her", "that", "this", "can", "may", "user", "users", "app", "application", "as", "at",
    "from", "into", "all", "any", "each", "get", "has", "have",
}
_NEGATIONS = {"not", "never", "no", "cannot", "without", "nor", "neither", "prohibited", "forbidden"}
_WORD_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
_SUFFIXES = ("ations", "ation", "ions", "ion", "ings", "ing", "ies", "ied", "ed", "es", "s", "ly")
_STEM_LENGTH = 6


def _tokens(text: str) -> List[str]:
    text = text.lower().replace("can't", "cannot").replace("won't", "will not").replace("n't", " not")
    return _WORD_RE.findall(text)


def _stem(token: str) -> str:
    """Crude stemmer: strip one common suffix, then truncate.

    "identify", "identified" and "identification" all become "identi";
    "booking" and "bookings" become "book". Good enough for overlap detection.
    """
    for suffix in _SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            token = token[: -len(suffix)]
            break
    return token[:_STEM_LENGTH]


def _content_tokens(text: str) -> Set[str]:
    return {_stem(t) for t in _tokens(text) if t not in _STOPWORDS and t not in _NEGATIONS}


def _has_negation(text: str) -> bool:
    return any(t in _NEGATIONS for t in _tokens(text))


def similarity(a: str, b: str) -> float:
    """Word-overlap similarity in [0, 1] (Dice coefficient over stemmed content words).

    Negations and filler words are ignored, so "X shall not do Y" and
    "X shall do Y" score 1.0; the caller checks negation separately.
    """
    ta, tb = _content_tokens(a), _content_tokens(b)
    if not ta or not tb:
        return 0.0
    return 2 * len(ta & tb) / (len(ta) + len(tb))


DUPLICATE_THRESHOLD = 0.8
OVERLAP_THRESHOLD = 0.5
# Short requirements share a word or two by chance; require real overlap.
MIN_SHARED_WORDS = 3


# --- Missing-information topics ----------------------------------------------
# (topic, trigger keywords found in active requirement text, coverage keywords
#  that show the topic has been addressed somewhere in the document).
# Keywords match whole words plus simple inflections ("upload" matches
# "uploads", "uploaded"); a trailing "*" makes a keyword a prefix ("valid*").

MISSING_INFO_TOPICS: Sequence[Tuple[str, Tuple[str, ...], Tuple[str, ...]]] = (
    ("authentication and session handling",
     ("login", "log in", "sign in", "sign-in", "sign up", "account", "register", "registration", "password"),
     ("authenticat*", "password", "session", "oauth", "two-factor", "2fa", "mfa", "sso",
      "single sign-on", "credential")),
    ("user roles and permissions",
     ("admin", "administrator", "moderator", "manager", "role", "permission"),
     ("permission", "authoriz*", "authoris*", "access control", "can only", "cannot", "role-based")),
    ("file and image limits (size, format)",
     ("upload", "photo", "image", "picture", "attachment", "camera"),
     ("mb", "kb", "size", "format", "jpeg", "jpg", "png", "heic", "resolution", "file type")),
    ("input validation rules",
     ("form", "input", "register", "registration", "submit", "sign up"),
     ("valid*", "invalid", "format", "required field", "maximum length", "characters", "must contain")),
    ("error handling and failure behaviour",
     ("upload", "submit", "sync", "payment", "import", "send"),
     ("error", "fail*", "invalid", "retry", "timeout", "unavailable", "offline", "reject*")),
    ("personal data and privacy",
     ("personal", "profile", "email", "location", "gps", "contact"),
     ("privacy", "gdpr", "consent", "retention", "encrypt*", "delete account", "data protection")),
    ("data storage, retention and backup",
     ("store", "collection", "history", "archive"),
     ("retention", "backup", "storage limit", "delete", "export", "stored for")),
    ("AI/ML result confidence and fallback",
     ("identify", "identification", "recognition", "recognise", "recognize", "classify",
      "classification", "predict", "prediction", "ai", "machine learning", "ml model"),
     ("confiden*", "accuracy", "precision", "threshold", "fallback", "uncertain", "manual*")),
    ("payments",
     ("payment", "pay", "subscription", "purchase", "checkout", "premium"),
     ("currency", "refund", "payment provider", "pci", "invoice", "billing")),
    ("offline and connectivity behaviour",
     ("mobile", "phone", "outdoor", "sync", "synchronise", "synchronize"),
     ("offline", "network", "connectivity", "no connection", "internet")),
)

_INFLECTIONS = r"(?:s|es|ed|d|ing|ion|ions|er|ers)?"
_KEYWORD_CACHE: Dict[str, "re.Pattern[str]"] = {}


def _keyword_re(keyword: str) -> "re.Pattern[str]":
    pattern = _KEYWORD_CACHE.get(keyword)
    if pattern is None:
        if keyword.endswith("*"):
            body = re.escape(keyword[:-1])
        else:
            body = re.escape(keyword) + _INFLECTIONS + r"(?![a-z0-9])"
        pattern = re.compile(r"(?<![a-z0-9])" + body, re.IGNORECASE)
        _KEYWORD_CACHE[keyword] = pattern
    return pattern


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    return any(_keyword_re(kw).search(text) for kw in keywords)


# --- Lint ---------------------------------------------------------------------


def _items(doc: Dict[str, Any], section: str) -> List[Dict[str, Any]]:
    value = doc.get(section, [])
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def _strings(value: Any) -> List[str]:
    """The string entries of a list (IDs, Given/When/Then lines); ignores anything malformed."""
    return [x for x in value if isinstance(x, str)] if isinstance(value, list) else []


def requirement_text(req: Dict[str, Any]) -> str:
    """The text that vague-word and similarity checks look at: title and description."""
    return f"{req.get('title', '')}. {req.get('description', '')}"


def _has_fit_criterion(item: Dict[str, Any]) -> bool:
    value = item.get("fit_criterion")
    return isinstance(value, str) and bool(value.strip())


def lint(doc: Dict[str, Any]) -> List[Finding]:
    """Run heuristic quality checks.

    Intended for documents that passed ``model.validate``; malformed parts are
    skipped rather than raising. Every finding is a candidate for the agent to
    confirm or dismiss.
    """
    out: List[Finding] = []
    if not isinstance(doc, dict):
        return out
    reqs = [r for r in _items(doc, "requirements") if isinstance(r.get("id"), str)]
    by_id = {r["id"]: r for r in reqs}
    active = [r for r in reqs if r.get("status") != "rejected"]
    issues = _items(doc, "issues")
    stories = _items(doc, "user_stories")
    acs = _items(doc, "acceptance_criteria")
    stakeholders = _items(doc, "stakeholders")

    # Issue kinds already tracked per requirement. Resolved issues no longer
    # count: if the wording is still vague after resolution, the fix did not land.
    tracked: Dict[str, Set[str]] = {}
    for issue in issues:
        if issue.get("status") == "resolved":
            continue
        for rid in _strings(issue.get("requirement_ids")):
            tracked.setdefault(rid, set()).add(str(issue.get("kind", "")))

    # 1. Vague terms / weak phrases in requirements.
    for req in active:
        rid = req["id"]
        terms = find_terms(requirement_text(req))
        if not terms or _has_fit_criterion(req) or "ambiguity" in tracked.get(rid, set()):
            continue
        names = sorted({t.term for t in terms})
        out.append(Finding(
            "warning", "ambiguous_term", f"requirement {rid}",
            f"{rid} uses {', '.join(repr(n) for n in names)} without a fit criterion or a tracked "
            f"ambiguity issue. Missing: {terms[0].explanation}.", (rid,),
        ))

    # 2. Vague wording in acceptance criteria (makes them untestable).
    #    Vague terms matter in outcomes ("then"); weak phrases matter anywhere.
    for ac in acs:
        aid = str(ac.get("id", "?"))
        for step in ("given", "when", "then"):
            for line in _strings(ac.get(step)):
                terms = [t for t in find_terms(line) if step == "then" or t.kind == "weak"]
                if terms:
                    out.append(Finding(
                        "warning", "untestable_criterion", f"acceptance criterion {aid}",
                        f"{aid} '{step}' step uses {', '.join(repr(t.term) for t in terms)}: "
                        f"\"{line}\". Replace with an observable, measurable outcome.", (aid,),
                    ))

    # 3. Duplicate / overlap / contradiction candidates.
    #    Pairs already named together in an issue are skipped. Pairs linked by
    #    depends_on / derived_from are expected to share words, so only a
    #    near-duplicate is reported for them.
    already_paired: Set[frozenset] = set()
    for issue in issues:
        for a, b in combinations(_strings(issue.get("requirement_ids")), 2):
            already_paired.add(frozenset((a, b)))
    linked: Set[frozenset] = set()
    for req in reqs:
        for other in _strings(req.get("depends_on")) + _strings(req.get("derived_from")):
            linked.add(frozenset((req["id"], other)))

    for a, b in combinations([r for r in active if r.get("type") != "business"], 2):
        pair = frozenset((a["id"], b["id"]))
        if pair in already_paired:
            continue
        ta, tb = requirement_text(a), requirement_text(b)
        score = similarity(ta, tb)
        if score < OVERLAP_THRESHOLD or len(_content_tokens(ta) & _content_tokens(tb)) < MIN_SHARED_WORDS:
            continue
        ids = (a["id"], b["id"])
        where = f"requirements {a['id']}, {b['id']}"
        same_polarity = _has_negation(ta) == _has_negation(tb)
        if score >= DUPLICATE_THRESHOLD and same_polarity:
            out.append(Finding(
                "warning", "possible_duplicate", where,
                f"{a['id']} and {b['id']} are very similar ({score:.0%}). Check whether one duplicates the other.",
                ids,
            ))
        elif pair in linked:
            continue
        elif not same_polarity:
            out.append(Finding(
                "warning", "possible_contradiction", where,
                f"{a['id']} and {b['id']} are similar ({score:.0%}) but only one is negated. "
                "Check whether they contradict each other.", ids,
            ))
        else:
            out.append(Finding(
                "hint", "possible_overlap", where,
                f"{a['id']} and {b['id']} overlap ({score:.0%}). They may be fine; check that the boundary "
                "between them is clear.", ids,
            ))

    # 4. Traceability gaps.
    story_reqs: Set[str] = {rid for s in stories for rid in _strings(s.get("requirement_ids"))}
    ac_reqs: Set[str] = {rid for ac in acs for rid in _strings(ac.get("requirement_ids"))}
    stories_with_ac: Set[Any] = {ac.get("story_id") for ac in acs}
    children: Set[str] = {p for r in reqs for p in _strings(r.get("derived_from"))}

    for req in active:
        rid, rtype = req["id"], req.get("type")
        if req.get("status") == "deferred":
            continue
        if rtype in ("functional", "user") and rid not in story_reqs:
            out.append(Finding("warning", "no_user_story", f"requirement {rid}",
                               f"{rid} is not covered by any user story.", (rid,)))
        if rtype in ("functional", "non_functional") and rid not in ac_reqs and not _has_fit_criterion(req):
            out.append(Finding("warning", "not_verifiable", f"requirement {rid}",
                               f"{rid} has no acceptance criterion and no fit criterion, so it cannot be verified.",
                               (rid,)))
        if rtype == "business" and rid not in children:
            out.append(Finding("hint", "business_requirement_not_refined", f"requirement {rid}",
                               f"No requirement is derived from {rid}. Check how it will be achieved.", (rid,)))

    for story in stories:
        sid = str(story.get("id", "?"))
        if sid not in stories_with_ac:
            out.append(Finding("warning", "story_without_ac", f"user story {sid}",
                               f"{sid} has no acceptance criteria.", (sid,)))
            continue
        types = {ac.get("type") for ac in acs if ac.get("story_id") == sid}
        if types == {"positive"}:
            out.append(Finding("hint", "only_positive_ac", f"user story {sid}",
                               f"{sid} only has positive scenarios. Consider negative or boundary cases.", (sid,)))

    # 5. Approved requirements with an open critical issue.
    for issue in issues:
        if issue.get("status") == "open" and issue.get("severity") == "critical":
            for rid in _strings(issue.get("requirement_ids")):
                match = by_id.get(rid)
                if match and match.get("status") == "approved":
                    out.append(Finding(
                        "warning", "approved_with_critical_issue", f"requirement {rid}",
                        f"{rid} is approved but critical issue {issue.get('id')} is still open.", (rid,),
                    ))

    # 6. Missing-information hints by topic. A topic is skipped when the
    #    document already covers it anywhere, or when it is explicitly out of scope.
    project = doc.get("project") if isinstance(doc.get("project"), dict) else {}
    scope_out = "\n".join(_strings(project.get("scope_out")))
    corpus_parts: List[str] = [requirement_text(r) + " " + str(r.get("fit_criterion", "")) for r in reqs]
    corpus_parts += [str(r.get("statement", "")) for r in _items(doc, "rules")]
    corpus_parts += [f"{i.get('description', '')} {i.get('missing_information', '')} {i.get('question', '')}"
                     for i in issues]
    corpus_parts += [" ".join(_strings(s.get("permissions"))) for s in stakeholders]
    corpus_parts += [f"{s.get('goal', '')} {s.get('description', '')}" for s in stories]
    corpus_parts += [" ".join(_strings(ac.get("given")) + _strings(ac.get("when")) + _strings(ac.get("then")))
                     for ac in acs]
    corpus = "\n".join(corpus_parts)
    for topic, triggers, coverage in MISSING_INFO_TOPICS:
        if _contains_any(scope_out, triggers) or _contains_any(corpus, coverage):
            continue
        hits = tuple(r["id"] for r in active if _contains_any(requirement_text(r), triggers))
        if hits:
            out.append(Finding("hint", "possibly_missing", "document",
                               f"{', '.join(hits)} {'mentions' if len(hits) == 1 else 'mention'} this area but nothing covers {topic}. "
                               "Decide whether it matters for this project.", hits))

    if active and not any(r.get("type") == "non_functional" for r in active):
        out.append(Finding("hint", "no_nfr", "document",
                           "No non-functional requirements are recorded (performance, security, usability, ...)."))

    # 7. Roles without permissions (only meaningful with more than one role).
    if len(stakeholders) > 1:
        missing = tuple(str(s.get("id", "?")) for s in stakeholders if not _strings(s.get("permissions")))
        if missing:
            verb = "has" if len(missing) == 1 else "have"
            out.append(Finding("hint", "roles_without_permissions", "stakeholders",
                               f"Several roles exist but {', '.join(missing)} {verb} no permissions defined. "
                               "State what each role may and may not do.", missing))
    return out
