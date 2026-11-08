"""Render requirements.json as requirements.md.

The Markdown is generated entirely from the JSON, so the two files cannot
contradict each other: every ID in the JSON appears in the Markdown, and the
Markdown names no item, link or fact that is not in the JSON. The only derived
content is counts, quality scores (``reqkit.quality``) and traceability gaps,
all computed from the JSON.

Output is deterministic (no timestamps), so exporting twice gives the same file.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence

from .model import Finding, QUALITY_CHARACTERISTICS, has_errors, validate
from .quality import CONSISTENCY_KINDS, QualityReport, assess

NOT_AVAILABLE = "*Not yet available.*"
EMPTY_CELL = "-"

SECTION_TITLES = (
    "Project Overview",
    "Scope",
    "Stakeholders and User Roles",
    "Business Requirements",
    "Functional Requirements",
    "Non-Functional Requirements",
    "Business Rules and Constraints",
    "Assumptions",
    "Ambiguities and Open Questions",
    "Conflict and Consistency Analysis",
    "User Stories",
    "Acceptance Criteria",
    "Requirements Quality Assessment",
    "Requirements Traceability Matrix",
)

ORIGIN_LABELS = {
    "confirmed": "confirmed",
    "assumed": "assumed (not confirmed)",
    "suggested": "suggested (not confirmed)",
    "open": "open (not confirmed)",
}
TYPE_LABELS = {
    "business": "business",
    "user": "user",
    "functional": "functional",
    "non_functional": "non-functional",
}
SEVERITY_ORDER = {"critical": 0, "important": 1, "optional": 2}


class InvalidDocument(ValueError):
    """Raised when asked to render a document that has validation errors."""

    def __init__(self, findings: List[Finding]):
        self.findings = [f for f in findings if f.level == "error"]
        super().__init__(f"requirements document has {len(self.findings)} validation error(s)")


# --- Markdown helpers ---------------------------------------------------------


def _items(doc: Dict[str, Any], section: str) -> List[Dict[str, Any]]:
    value = doc.get(section, [])
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def _strings(value: Any) -> List[str]:
    return [x for x in value if isinstance(x, str)] if isinstance(value, list) else []


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _cell(value: Any) -> str:
    """Text made safe for a table cell (no pipes, no line breaks)."""
    text = _text(value) if not isinstance(value, (int, float)) else str(value)
    if not text:
        return EMPTY_CELL
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\r\n", "\n").replace("\n", "<br>")


def _join(values: Sequence[str]) -> str:
    return ", ".join(values) if values else EMPTY_CELL


def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> List[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(_cell(c) if not isinstance(c, _Raw) else c.text for c in row) + " |"
              for row in rows]
    return lines


class _Raw:
    """A table cell that is already valid Markdown (e.g. a joined ID list)."""

    def __init__(self, text: str):
        self.text = text or EMPTY_CELL


def _origin(value: Any) -> str:
    return ORIGIN_LABELS.get(str(value), str(value))


def _percent(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{value:.0f}%"


# --- Document renderer --------------------------------------------------------


class _Renderer:
    def __init__(self, doc: Dict[str, Any], report: QualityReport):
        self.doc = doc
        self.report = report
        project = doc.get("project")
        self.project: Dict[str, Any] = project if isinstance(project, dict) else {}
        self.reqs = [r for r in _items(doc, "requirements") if isinstance(r.get("id"), str)]
        self.stakeholders = _items(doc, "stakeholders")
        self.rules = _items(doc, "rules")
        self.issues = _items(doc, "issues")
        self.stories = _items(doc, "user_stories")
        self.acs = _items(doc, "acceptance_criteria")
        self.stakeholder_names = {s.get("id"): _text(s.get("name")) for s in self.stakeholders}
        self.lines: List[str] = []

    # Output helpers ----------------------------------------------------------

    def add(self, *lines: str) -> None:
        self.lines.extend(lines)

    def blank(self) -> None:
        if self.lines and self.lines[-1] != "":
            self.lines.append("")

    def section(self, number: int, body: Callable[[], bool]) -> None:
        """Write section ``number``; ``body`` returns False when it had nothing to show."""
        self.blank()
        self.add(f"## {number}. {SECTION_TITLES[number - 1]}", "")
        if not body():
            self.add(NOT_AVAILABLE)

    # Whole document ------------------------------------------------------------

    def render(self) -> str:
        name = _text(self.project.get("name")) or "Untitled project"
        self.add(f"# {name}: Requirements Specification", "")
        self.add("> Generated from `requirements.json` by the Requirements Engineering Assistant. "
                 "Edit the JSON and export again instead of editing this file.")
        bodies = (
            self.overview, self.scope, self.stakeholders_section,
            lambda: self.requirements_of(("business", "user")),
            lambda: self.requirements_of(("functional",)),
            lambda: self.requirements_of(("non_functional",)),
            lambda: self.rules_of(("business_rule", "constraint")),
            lambda: self.rules_of(("assumption",)),
            self.open_questions, self.consistency, self.user_stories,
            self.acceptance_criteria, self.quality, self.traceability,
        )
        for number, body in enumerate(bodies, start=1):
            self.section(number, body)
        self.blank()
        return "\n".join(self.lines).rstrip("\n") + "\n"

    # 1. Overview ---------------------------------------------------------------

    def overview(self) -> bool:
        overview = _text(self.project.get("overview"))
        self.add(overview if overview else NOT_AVAILABLE, "")
        counts: Dict[str, int] = {}
        for r in self.reqs:
            counts[str(r.get("type"))] = counts.get(str(r.get("type")), 0) + 1
        breakdown = ", ".join(f"{counts[t]} {TYPE_LABELS[t]}" for t in TYPE_LABELS if t in counts)
        open_issues = [i for i in self.issues if i.get("status") == "open"]
        critical = sum(1 for i in open_issues if i.get("severity") == "critical")
        self.add(f"- **Mode:** {_text(self.project.get('mode')) or EMPTY_CELL}")
        rounds = self.project.get("clarification_round")
        if isinstance(rounds, int) and not isinstance(rounds, bool):
            self.add(f"- **Clarification rounds completed:** {rounds}")
        self.add(f"- **Requirements:** {len(self.reqs)}" + (f" ({breakdown})" if breakdown else ""))
        self.add(f"- **Open issues:** {len(open_issues)} ({critical} critical)")
        self.add(f"- **User stories:** {len(self.stories)}; **acceptance criteria:** {len(self.acs)}")
        return True

    # 2. Scope --------------------------------------------------------------------

    def scope(self) -> bool:
        scope_in = _strings(self.project.get("scope_in"))
        scope_out = _strings(self.project.get("scope_out"))
        if not scope_in and not scope_out:
            return False
        for title, values in (("In scope", scope_in), ("Out of scope", scope_out)):
            self.add(f"### {title}", "")
            if values:
                self.add(*(f"- {v.strip()}" for v in values))
            else:
                self.add(NOT_AVAILABLE)
            self.blank()
        return True

    # 3. Stakeholders -------------------------------------------------------------

    def stakeholders_section(self) -> bool:
        if not self.stakeholders:
            return False
        rows = [(s.get("id"), s.get("name"), s.get("description"),
                 "; ".join(p.strip() for p in _strings(s.get("permissions"))), _origin(s.get("origin")))
                for s in self.stakeholders]
        self.add(*_table(("ID", "Name", "Description", "Permissions", "Origin"), rows))
        return True

    # 4-6. Requirements -----------------------------------------------------------

    def _stakeholder_ref(self, sid: str) -> str:
        name = self.stakeholder_names.get(sid)
        return f"{sid} ({name})" if name else sid

    def requirements_of(self, types: Sequence[str]) -> bool:
        groups = [(t, [r for r in self.reqs if r.get("type") == t]) for t in types]
        groups = [(t, g) for t, g in groups if g]
        nested = len(groups) > 1  # subheadings only when several types are present
        for rtype, group in groups:
            if nested:
                self.blank()
                self.add(f"### {TYPE_LABELS[rtype].capitalize()} requirements", "")
            for req in group:
                self.requirement(req, heading="####" if nested else "###")
        return bool(groups)

    def requirement(self, req: Dict[str, Any], heading: str) -> None:
        self.blank()
        self.add(f"{heading} {req['id']}: {_text(req.get('title'))}", "")
        self.add(_text(req.get("description")), "")
        self.add(f"- **Priority:** {req.get('priority')} · **Status:** {req.get('status')} · "
                 f"**Origin:** {_origin(req.get('origin'))}")
        self.add(f"- **Source:** {_text(req.get('source')) or 'not recorded'}")
        for label, key in (("Fit criterion", "fit_criterion"), ("Rationale", "rationale")):
            if _text(req.get(key)):
                self.add(f"- **{label}:** {_text(req.get(key))}")
        for label, key in (("Derived from", "derived_from"), ("Depends on", "depends_on")):
            if _strings(req.get(key)):
                self.add(f"- **{label}:** {', '.join(_strings(req.get(key)))}")
        if _strings(req.get("stakeholders")):
            self.add("- **Stakeholders:** " + ", ".join(self._stakeholder_ref(s) for s in _strings(req.get("stakeholders"))))

    # 7-8. Rules --------------------------------------------------------------------

    def rules_of(self, kinds: Sequence[str]) -> bool:
        group = [r for r in self.rules if r.get("kind") in kinds]
        if not group:
            return False
        headers = ["ID"] + (["Kind"] if len(kinds) > 1 else []) + ["Statement", "Origin", "Source", "Related"]
        rows = []
        for r in group:
            row: List[Any] = [r.get("id")]
            if len(kinds) > 1:
                row.append(str(r.get("kind", "")).replace("_", " "))
            row += [r.get("statement"), _origin(r.get("origin")), r.get("source"), _join(_strings(r.get("related")))]
            rows.append(row)
        self.add(*_table(headers, rows))
        return True

    # 9-10. Issues ------------------------------------------------------------------

    def issue(self, issue: Dict[str, Any]) -> None:
        self.blank()
        kind = str(issue.get("kind", "")).replace("_", " ")
        self.add(f"#### {issue.get('id')}: {kind} ({issue.get('severity')}, {str(issue.get('status')).replace('_', ' ')})", "")
        self.add(f"- **Affects:** {_join(_strings(issue.get('requirement_ids')))}")
        self.add(f"- **Description:** {_text(issue.get('description'))}")
        for label, key in (("Missing information", "missing_information"), ("Question", "question"),
                           ("Suggestion (not confirmed)", "suggestion"), ("Resolution", "resolution")):
            if _text(issue.get(key)):
                self.add(f"- **{label}:** {_text(issue.get(key))}")

    def issue_groups(self, issues: List[Dict[str, Any]]) -> None:
        open_issues = sorted((i for i in issues if i.get("status") == "open"),
                             key=lambda i: SEVERITY_ORDER.get(str(i.get("severity")), 9))
        closed = [i for i in issues if i.get("status") != "open"]
        for title, group in (("Open", open_issues), ("Resolved or accepted", closed)):
            if group:
                self.blank()
                self.add(f"### {title}", "")
                for issue in group:
                    self.issue(issue)

    def open_questions(self) -> bool:
        issues = [i for i in self.issues if i.get("kind") not in CONSISTENCY_KINDS]
        self.issue_groups(issues)
        unconfirmed = [(s.get("id"), "stakeholder", s.get("name"), s.get("origin"), EMPTY_CELL)
                       for s in self.stakeholders if s.get("origin") != "confirmed"]
        unconfirmed += [(r["id"], TYPE_LABELS.get(str(r.get("type")), "requirement") + " requirement",
                         r.get("title"), r.get("origin"), r.get("status"))
                        for r in self.reqs if r.get("origin") != "confirmed"]
        unconfirmed += [(r.get("id"), str(r.get("kind", "")).replace("_", " "), r.get("statement"),
                         r.get("origin"), EMPTY_CELL)
                        for r in self.rules if r.get("origin") != "confirmed"]
        if unconfirmed:
            self.blank()
            self.add("### Items not yet confirmed by the user", "")
            self.add(*_table(("ID", "Kind", "Item", "Origin", "Status"),
                             [(i, k, t, _origin(o), s) for i, k, t, o, s in unconfirmed]))
        return bool(issues or unconfirmed)

    def consistency(self) -> bool:
        issues = [i for i in self.issues if i.get("kind") in CONSISTENCY_KINDS]
        if not issues:
            self.add("No conflicts, duplicates, overlaps or terminology issues are recorded.")
            return True
        self.issue_groups(issues)
        return True

    # 11-12. Stories and acceptance criteria -----------------------------------------

    @staticmethod
    def story_sentence(story: Dict[str, Any]) -> str:
        goal = _text(story.get("goal"))
        if not goal.lower().startswith("to "):
            goal = "to " + goal
        return (f"As a {_text(story.get('role'))}, I want {goal}, "
                f"so that {_text(story.get('benefit')).rstrip('.')}.")

    def user_stories(self) -> bool:
        if not self.stories:
            return False
        with_notes = any(_text(s.get("description")) for s in self.stories)
        headers = ["ID", "User story", "Priority", "Requirements"] + (["Notes"] if with_notes else [])
        rows = []
        for s in self.stories:
            row: List[Any] = [s.get("id"), self.story_sentence(s), s.get("priority"),
                              _join(_strings(s.get("requirement_ids")))]
            if with_notes:
                row.append(s.get("description"))
            rows.append(row)
        self.add(*_table(headers, rows))
        return True

    def acceptance_criteria(self) -> bool:
        if not self.acs:
            return False
        story_ids = [s.get("id") for s in self.stories]
        for story in self.stories:
            group = [ac for ac in self.acs if ac.get("story_id") == story.get("id")]
            self.blank()
            self.add(f"### {story.get('id')}: {_text(story.get('goal'))}", "")
            if not group:
                self.add("*No acceptance criteria yet.*")
            for ac in group:
                self.criterion(ac)
        orphans = [ac for ac in self.acs if ac.get("story_id") not in story_ids]
        for ac in orphans:  # only possible in an invalid document
            self.criterion(ac)
        return True

    def criterion(self, ac: Dict[str, Any]) -> None:
        self.blank()
        self.add(f"#### {ac.get('id')}: {_text(ac.get('title'))} ({ac.get('type')})", "")
        self.add(f"*Requirements: {_join(_strings(ac.get('requirement_ids')))}*", "")
        for keyword, step in (("Given", "given"), ("When", "when"), ("Then", "then")):
            for n, line in enumerate(_strings(ac.get(step))):
                self.add(f"- **{keyword if n == 0 else 'And'}** {line.strip()}")

    # 13. Quality -----------------------------------------------------------------

    def quality(self) -> bool:
        if not self.report.requirements:
            return False
        self.add("Each characteristic is scored 0 (poor), 1 (partial) or 2 (good); *n/a* means not applicable "
                 "and *?* means not assessed yet. Neither counts against the requirement. Unambiguity, "
                 "verifiability, consistency and traceability are computed by the script; clarity, "
                 "completeness and feasibility are judged by the AI agent, with a reason. "
                 "The score is a guide, not a certification. Rejected requirements are not scored.", "")
        self.add(f"**Overall: {_percent(self.report.percent)}** "
                 f"({self.report.points} of {self.report.max_points} applicable points)", "")
        headers = ["Requirement"] + [c.capitalize() for c in QUALITY_CHARACTERISTICS] + ["Score"]
        rows = []
        for rq in self.report.requirements:
            cells = []
            for c in QUALITY_CHARACTERISTICS:
                score = rq.scores[c]
                cells.append("?" if not score.assessed else "n/a" if score.value is None else str(score.value))
            rows.append([rq.requirement_id, *cells, _percent(rq.percent)])
        self.add(*_table(headers, rows))

        self.blank()
        self.add("### Requirements needing improvement", "")
        if self.report.needs_improvement:
            for rq in self.report.needs_improvement:
                weak = "; ".join(f"{c} {rq.scores[c].value} ({rq.scores[c].reason.rstrip('.')})" for c in rq.weak)
                self.add(f"- **{rq.requirement_id}** ({_percent(rq.percent)}): {weak}")
        else:
            self.add("None: every applicable score is 2.")

        if self.report.not_assessed:
            self.blank()
            self.add("### Not assessed yet", "")
            for rq in self.report.not_assessed:
                self.add(f"- **{rq.requirement_id}:** {', '.join(rq.not_assessed)}")

        self.blank()
        self.add("### Score reasons", "")
        for rq in self.report.requirements:
            self.blank()
            self.add(f"#### {rq.requirement_id}", "")
            for c in QUALITY_CHARACTERISTICS:
                score = rq.scores[c]
                value = "?" if not score.assessed else "n/a" if score.value is None else str(score.value)
                self.add(f"- **{c.capitalize()}** ({score.method}, {value}): {score.reason}")
        return True

    # 14. Traceability ----------------------------------------------------------------

    def gaps(self, req: Dict[str, Any], stories: List[str], acs: List[str], children: List[str]) -> List[str]:
        status, rtype = req.get("status"), req.get("type")
        if status == "rejected":
            return []
        gaps: List[str] = []
        if req.get("origin") != "confirmed":
            gaps.append("not confirmed")
        if not _text(req.get("source")):
            gaps.append("no source")
        if status != "deferred":
            if rtype in ("functional", "user") and not stories:
                gaps.append("no user story")
            if rtype in ("functional", "non_functional") and not acs and not _text(req.get("fit_criterion")):
                gaps.append("not verifiable")
            if rtype == "business" and not children:
                gaps.append("not refined")
        return gaps

    def traceability(self) -> bool:
        if not self.reqs:
            return False
        self.add("Only links recorded in `requirements.json` are shown.", "")
        children: Dict[str, List[str]] = {}
        for r in self.reqs:
            for parent in _strings(r.get("derived_from")):
                children.setdefault(parent, []).append(r["id"])
        rows = []
        for req in self.reqs:
            rid = req["id"]
            stories = [str(s.get("id")) for s in self.stories if rid in _strings(s.get("requirement_ids"))]
            acs = [str(a.get("id")) for a in self.acs if rid in _strings(a.get("requirement_ids"))]
            issues = [str(i.get("id")) for i in self.issues
                      if i.get("status") == "open" and rid in _strings(i.get("requirement_ids"))]
            kids = children.get(rid, [])
            rows.append([
                rid, req.get("status"), _join(_strings(req.get("derived_from"))), _join(kids),
                _join(_strings(req.get("depends_on"))), _join(stories), _join(acs), _join(issues),
                _join(self.gaps(req, stories, acs, kids)),
            ])
        self.add(*_table(("Requirement", "Status", "Derived from", "Refined by", "Depends on",
                          "User stories", "Acceptance criteria", "Open issues", "Gaps"), rows))
        return True


def render_markdown(doc: Dict[str, Any], report: Optional[QualityReport] = None) -> str:
    """Return requirements.md for a valid document.

    Raises ``InvalidDocument`` if the document has validation errors, so an
    invalid file is never exported.
    """
    findings = validate(doc)
    if has_errors(findings):
        raise InvalidDocument(findings)
    return _Renderer(doc, report if report is not None else assess(doc)).render()
