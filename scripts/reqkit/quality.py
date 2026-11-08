"""Requirements quality scores (0-2 per characteristic).

Four characteristics are computed here from the JSON contents (see PLAN.md
section 7): unambiguity, verifiability, consistency and traceability. Three
are judged by the agent and read from ``quality_assessments``: clarity,
completeness and feasibility.

A score of ``None`` means "not applicable" (or "not assessed" for a judged
characteristic the agent has not scored yet). Neither counts against the
requirement. The result is a transparent guide, not an objective measurement.

Rejected requirements are not scored. The functions expect a document that
passed ``model.validate``; malformed parts are skipped rather than raising.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .checks import find_terms, requirement_text
from .model import COMPUTED_CHARACTERISTICS, JUDGED_CHARACTERISTICS, QUALITY_CHARACTERISTICS

MAX_SCORE = 2
# Issue kinds that make a requirement inconsistent, and the ones that count as
# severe (score 0) when the issue is critical.
CONSISTENCY_KINDS = ("conflict", "duplicate", "overlap", "terminology")
SEVERE_CONSISTENCY_KINDS = ("conflict", "duplicate")


@dataclass(frozen=True)
class Score:
    """One characteristic of one requirement.

    method: ``computed`` (by this module) or ``judged`` (by the agent).
    assessed: False when a judged characteristic has no score yet.
    """

    characteristic: str
    value: Optional[int]
    reason: str
    method: str
    assessed: bool = True

    def as_dict(self) -> Dict[str, Any]:
        return {
            "characteristic": self.characteristic,
            "value": self.value,
            "reason": self.reason,
            "method": self.method,
            "assessed": self.assessed,
        }


@dataclass(frozen=True)
class RequirementQuality:
    requirement_id: str
    scores: Dict[str, Score]

    @property
    def points(self) -> int:
        return sum(s.value for s in self.scores.values() if s.value is not None)

    @property
    def max_points(self) -> int:
        return MAX_SCORE * sum(1 for s in self.scores.values() if s.value is not None)

    @property
    def percent(self) -> Optional[float]:
        return 100.0 * self.points / self.max_points if self.max_points else None

    @property
    def weak(self) -> List[str]:
        """Characteristics scored below the maximum, in characteristic order."""
        return [c for c, s in self.scores.items() if s.value is not None and s.value < MAX_SCORE]

    @property
    def not_assessed(self) -> List[str]:
        return [c for c, s in self.scores.items() if not s.assessed]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "scores": {c: s.as_dict() for c, s in self.scores.items()},
            "points": self.points,
            "max_points": self.max_points,
            "percent": self.percent,
            "needs_improvement": self.weak,
            "not_assessed": self.not_assessed,
        }


@dataclass(frozen=True)
class QualityReport:
    requirements: List[RequirementQuality] = field(default_factory=list)

    @property
    def points(self) -> int:
        return sum(r.points for r in self.requirements)

    @property
    def max_points(self) -> int:
        return sum(r.max_points for r in self.requirements)

    @property
    def percent(self) -> Optional[float]:
        return 100.0 * self.points / self.max_points if self.max_points else None

    @property
    def needs_improvement(self) -> List[RequirementQuality]:
        """Requirements with at least one score below 2, lowest percentage first."""
        weak = [r for r in self.requirements if r.weak]
        return sorted(weak, key=lambda r: (r.percent if r.percent is not None else 100.0))

    @property
    def not_assessed(self) -> List[RequirementQuality]:
        return [r for r in self.requirements if r.not_assessed]

    def get(self, requirement_id: str) -> Optional[RequirementQuality]:
        return next((r for r in self.requirements if r.requirement_id == requirement_id), None)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "points": self.points,
            "max_points": self.max_points,
            "percent": self.percent,
            "requirements": [r.as_dict() for r in self.requirements],
            "needs_improvement": [r.requirement_id for r in self.needs_improvement],
            "not_assessed": [r.requirement_id for r in self.not_assessed],
        }


# --- Helpers ------------------------------------------------------------------


def _items(doc: Dict[str, Any], section: str) -> List[Dict[str, Any]]:
    value = doc.get(section, [])
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def _strings(value: Any) -> List[str]:
    return [x for x in value if isinstance(x, str)] if isinstance(value, list) else []


def _filled(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _ids(items: List[Dict[str, Any]]) -> str:
    return ", ".join(str(i.get("id", "?")) for i in items)


# --- Computed characteristics -------------------------------------------------


def _unambiguity(req: Dict[str, Any], issues: List[Dict[str, Any]]) -> Score:
    terms = sorted({t.term for t in find_terms(requirement_text(req))})
    if not terms:
        return Score("unambiguity", 2, "No vague words found.", "computed")
    words = ", ".join(f"'{t}'" for t in terms)
    if _filled(req.get("fit_criterion")):
        return Score("unambiguity", 2, f"Uses {words}, but a fit criterion defines the target.", "computed")
    tracked = [i for i in issues if i.get("kind") == "ambiguity" and i.get("status") != "resolved"]
    if tracked:
        return Score("unambiguity", 1, f"Uses {words}; tracked as ambiguity issue {_ids(tracked)}.", "computed")
    return Score("unambiguity", 0, f"Uses {words} with no fit criterion and no tracked ambiguity issue.",
                 "computed")


def _verifiability(req: Dict[str, Any], stories: List[Dict[str, Any]],
                   acs: List[Dict[str, Any]]) -> Score:
    if req.get("type") == "business":
        return Score("verifiability", None, "Not applicable to business requirements.", "computed")
    if acs and _filled(req.get("fit_criterion")):
        return Score("verifiability", 2, f"Has acceptance criteria ({_ids(acs)}) and a fit criterion.",
                     "computed")
    if acs:
        return Score("verifiability", 2, f"Has acceptance criteria: {_ids(acs)}.", "computed")
    if _filled(req.get("fit_criterion")):
        return Score("verifiability", 2, "Has a fit criterion.", "computed")
    if stories:
        return Score("verifiability", 1,
                     f"Covered by user story {_ids(stories)}, but no acceptance criterion or fit criterion.",
                     "computed")
    return Score("verifiability", 0, "No acceptance criterion, fit criterion or user story.", "computed")


def _consistency(issues: List[Dict[str, Any]]) -> Score:
    open_issues = [i for i in issues if i.get("status") == "open" and i.get("kind") in CONSISTENCY_KINDS]
    severe = [i for i in open_issues
              if i.get("severity") == "critical" and i.get("kind") in SEVERE_CONSISTENCY_KINDS]
    if severe:
        return Score("consistency", 0, f"In open critical conflict or duplicate issue {_ids(severe)}.", "computed")
    if open_issues:
        kinds = ", ".join(sorted({str(i.get("kind")) for i in open_issues}))
        return Score("consistency", 1, f"In open {kinds} issue {_ids(open_issues)}.", "computed")
    return Score("consistency", 2, "No open conflict, duplicate, overlap or terminology issue.", "computed")


def _traceability(req: Dict[str, Any], links: List[str]) -> Score:
    if not _filled(req.get("source")):
        return Score("traceability", 0, "No source recorded.", "computed")
    if links:
        return Score("traceability", 2, f"Has a source and is linked to {', '.join(links)}.", "computed")
    return Score("traceability", 1, "Has a source but is not linked to any parent, child, story or criterion.",
                 "computed")


def _judged(characteristic: str, assessment: Optional[Dict[str, Any]]) -> Score:
    scores = assessment.get("scores") if assessment and isinstance(assessment.get("scores"), dict) else {}
    reasons = assessment.get("reasons") if assessment and isinstance(assessment.get("reasons"), dict) else {}
    if characteristic not in scores:
        return Score(characteristic, None, "Not assessed yet.", "judged", assessed=False)
    value = scores[characteristic]
    if value is not None and (type(value) is not int or not 0 <= value <= MAX_SCORE):
        return Score(characteristic, None, "Invalid score ignored.", "judged", assessed=False)
    reason = reasons.get(characteristic)
    if not _filled(reason):
        reason = "Not applicable." if value is None else "No reason given."
    return Score(characteristic, value, reason.strip(), "judged")


# --- Report -------------------------------------------------------------------


def assess(doc: Dict[str, Any]) -> QualityReport:
    """Score every requirement that is not rejected, in document order."""
    if not isinstance(doc, dict):
        return QualityReport()
    reqs = [r for r in _items(doc, "requirements") if isinstance(r.get("id"), str)]
    issues = _items(doc, "issues")
    stories = _items(doc, "user_stories")
    acs = _items(doc, "acceptance_criteria")
    assessments: Dict[str, Dict[str, Any]] = {}
    for qa in _items(doc, "quality_assessments"):
        if isinstance(qa.get("requirement_id"), str):
            assessments.setdefault(qa["requirement_id"], qa)
    children: Dict[str, List[str]] = {}
    for r in reqs:
        for parent in _strings(r.get("derived_from")):
            children.setdefault(parent, []).append(r["id"])

    report: List[RequirementQuality] = []
    for req in reqs:
        if req.get("status") == "rejected":
            continue
        rid = req["id"]
        req_issues = [i for i in issues if rid in _strings(i.get("requirement_ids"))]
        req_stories = [s for s in stories if rid in _strings(s.get("requirement_ids"))]
        req_acs = [a for a in acs if rid in _strings(a.get("requirement_ids"))]
        # "Linked up or down": parents, children, stories, acceptance criteria.
        seen: Set[str] = set()
        links = [x for x in (_strings(req.get("derived_from")) + children.get(rid, [])
                             + [str(s.get("id")) for s in req_stories] + [str(a.get("id")) for a in req_acs])
                 if not (x in seen or seen.add(x))]

        computed = {
            "unambiguity": _unambiguity(req, req_issues),
            "verifiability": _verifiability(req, req_stories, req_acs),
            "consistency": _consistency(req_issues),
            "traceability": _traceability(req, links),
        }
        scores: Dict[str, Score] = {}
        for characteristic in QUALITY_CHARACTERISTICS:
            if characteristic in COMPUTED_CHARACTERISTICS:
                scores[characteristic] = computed[characteristic]
            elif characteristic in JUDGED_CHARACTERISTICS:
                scores[characteristic] = _judged(characteristic, assessments.get(rid))
        report.append(RequirementQuality(rid, scores))
    return QualityReport(report)
