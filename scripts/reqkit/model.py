"""Data model and structural validation for requirements.json.

The field specifications in this module are the single source of truth for the
data model. ``schemas/requirements.schema.json`` is generated from them by
``json_schema()`` / ``write_schema()``, and ``tests/test_schema_sync.py`` fails
if the file and the model drift apart.

``validate()`` never raises on malformed input: whatever shape the document
has, problems are reported as findings.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "1.0"

# --- Vocabularies -----------------------------------------------------------

REQUIREMENT_TYPES: Dict[str, str] = {
    "functional": "FR",
    "non_functional": "NFR",
    "business": "BR",
    "user": "UR",
}
RULE_KINDS: Dict[str, str] = {
    "business_rule": "BRL",
    "constraint": "CON",
    "assumption": "ASM",
}
ORIGINS = ("confirmed", "assumed", "suggested", "open")
PRIORITIES = ("must", "should", "could", "wont", "unset")
REQUIREMENT_STATUSES = ("draft", "needs_clarification", "approved", "deferred", "rejected")
ISSUE_KINDS = (
    "ambiguity",
    "missing_information",
    "conflict",
    "duplicate",
    "overlap",
    "terminology",
    "dependency",
)
SEVERITIES = ("critical", "important", "optional")
ISSUE_STATUSES = ("open", "resolved", "accepted_risk")
AC_TYPES = ("positive", "negative", "boundary")
MODES = ("interactive", "automatic")

QUALITY_CHARACTERISTICS = (
    "clarity",
    "completeness",
    "consistency",
    "unambiguity",
    "verifiability",
    "feasibility",
    "traceability",
)
# Judged by the agent (needs language understanding), stored in the JSON.
JUDGED_CHARACTERISTICS = ("clarity", "completeness", "feasibility")
# Computed deterministically by reqkit.quality from the JSON contents.
COMPUTED_CHARACTERISTICS = ("consistency", "unambiguity", "verifiability", "traceability")
SCORE_VALUES = (0, 1, 2)

ID_PREFIXES = {
    "stakeholders": ("SH",),
    "requirements": tuple(REQUIREMENT_TYPES.values()),
    "rules": tuple(RULE_KINDS.values()),
    "issues": ("ISS",),
    "user_stories": ("US",),
    "acceptance_criteria": ("AC",),
}
ID_PATTERN = re.compile(r"^([A-Z]{2,4})-(\d{3,})$")
NON_EMPTY_PATTERN = r"\S"


def id_pattern_for(prefixes: Tuple[str, ...]) -> str:
    """Regex (as a string) matching IDs with one of the given prefixes."""
    return r"^(" + "|".join(prefixes) + r")-\d{3,}$"


# --- Field specification ----------------------------------------------------


@dataclass(frozen=True)
class Field:
    """Specification of one JSON field.

    kind:
      ``text``        non-empty string
      ``string``      string, may be empty
      ``enum``        one of ``choices``
      ``id``          an ID string such as ``FR-001``
      ``id_list``     list of IDs
      ``string_list`` list of non-empty strings
      ``integer``     non-negative integer
      ``score_map``   {judged characteristic: 0 | 1 | 2 | null}
      ``text_map``    {key: string}
      ``object``      a JSON object (checked by its own field table)
      ``object_list`` a list of JSON objects (checked by its own field table)
    """

    kind: str
    required: bool = True
    choices: Tuple[str, ...] = ()
    min_items: int = 0


PROJECT_FIELDS: Dict[str, Field] = {
    "name": Field("text"),
    "overview": Field("string"),
    "mode": Field("enum", choices=MODES),
    "scope_in": Field("string_list", required=False),
    "scope_out": Field("string_list", required=False),
    "clarification_round": Field("integer", required=False),
}

STAKEHOLDER_FIELDS: Dict[str, Field] = {
    "id": Field("id"),
    "name": Field("text"),
    "description": Field("string", required=False),
    "permissions": Field("string_list", required=False),
    "origin": Field("enum", choices=ORIGINS),
}

REQUIREMENT_FIELDS: Dict[str, Field] = {
    "id": Field("id"),
    "type": Field("enum", choices=tuple(REQUIREMENT_TYPES)),
    "title": Field("text"),
    "description": Field("text"),
    "priority": Field("enum", choices=PRIORITIES),
    "origin": Field("enum", choices=ORIGINS),
    "status": Field("enum", choices=REQUIREMENT_STATUSES),
    "source": Field("string"),
    "fit_criterion": Field("string", required=False),
    "rationale": Field("string", required=False),
    "depends_on": Field("id_list", required=False),
    "derived_from": Field("id_list", required=False),
    "stakeholders": Field("id_list", required=False),
}

RULE_FIELDS: Dict[str, Field] = {
    "id": Field("id"),
    "kind": Field("enum", choices=tuple(RULE_KINDS)),
    "statement": Field("text"),
    "origin": Field("enum", choices=ORIGINS),
    "source": Field("string"),
    "related": Field("id_list", required=False),
}

ISSUE_FIELDS: Dict[str, Field] = {
    "id": Field("id"),
    "kind": Field("enum", choices=ISSUE_KINDS),
    "severity": Field("enum", choices=SEVERITIES),
    "status": Field("enum", choices=ISSUE_STATUSES),
    "requirement_ids": Field("id_list"),
    "description": Field("text"),
    "missing_information": Field("string", required=False),
    "question": Field("string", required=False),
    "suggestion": Field("string", required=False),
    "resolution": Field("string", required=False),
}

STORY_FIELDS: Dict[str, Field] = {
    "id": Field("id"),
    "role": Field("text"),
    "goal": Field("text"),
    "benefit": Field("text"),
    "requirement_ids": Field("id_list"),
    "priority": Field("enum", choices=PRIORITIES),
    "description": Field("string", required=False),
}

AC_FIELDS: Dict[str, Field] = {
    "id": Field("id"),
    "story_id": Field("id"),
    "requirement_ids": Field("id_list"),
    "title": Field("text"),
    "type": Field("enum", choices=AC_TYPES),
    "given": Field("string_list", min_items=1),
    "when": Field("string_list", min_items=1),
    "then": Field("string_list", min_items=1),
}

QUALITY_FIELDS: Dict[str, Field] = {
    "requirement_id": Field("id"),
    "scores": Field("score_map"),
    "reasons": Field("text_map"),
}

TOP_LEVEL_FIELDS: Dict[str, Field] = {
    "schema_version": Field("text"),
    "project": Field("object"),
    "requirements": Field("object_list"),
    "stakeholders": Field("object_list", required=False),
    "rules": Field("object_list", required=False),
    "issues": Field("object_list", required=False),
    "user_stories": Field("object_list", required=False),
    "acceptance_criteria": Field("object_list", required=False),
    "quality_assessments": Field("object_list", required=False),
}

# Top-level list sections, in document order, with their field tables.
LIST_SECTIONS: Dict[str, Dict[str, Field]] = {
    "stakeholders": STAKEHOLDER_FIELDS,
    "requirements": REQUIREMENT_FIELDS,
    "rules": RULE_FIELDS,
    "issues": ISSUE_FIELDS,
    "user_stories": STORY_FIELDS,
    "acceptance_criteria": AC_FIELDS,
    "quality_assessments": QUALITY_FIELDS,
}


# --- Findings ---------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """A validation or lint result.

    level: ``error`` (document is invalid), ``warning`` (likely quality
    problem) or ``hint`` (worth a look; may be irrelevant to the project).
    """

    level: str
    code: str
    path: str
    message: str
    ids: Tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "code": self.code,
            "path": self.path,
            "message": self.message,
            "ids": list(self.ids),
        }


# --- Small helpers ----------------------------------------------------------


def _str(value: Any) -> Optional[str]:
    """``value`` if it is a string, else None (keeps dict lookups safe)."""
    return value if isinstance(value, str) else None


def _str_list(value: Any) -> List[str]:
    """The string items of ``value`` if it is a list, else an empty list."""
    if not isinstance(value, list):
        return []
    return [x for x in value if isinstance(x, str)]


def _label(value: Any) -> str:
    """A printable owner label for messages, even when the ID is malformed."""
    return value if isinstance(value, str) and value else "?"


def _blank(value: Any) -> bool:
    return not isinstance(value, str) or not value.strip()


def _prefix(item_id: Any) -> Optional[str]:
    if isinstance(item_id, str):
        m = ID_PATTERN.match(item_id)
        if m:
            return m.group(1)
    return None


def _items(doc: Dict[str, Any], section: str) -> List[Tuple[int, Dict[str, Any]]]:
    """(index, item) pairs of the dict items in a list section."""
    value = doc.get(section, [])
    if not isinstance(value, list):
        return []
    return [(i, x) for i, x in enumerate(value) if isinstance(x, dict)]


# --- Structural checks ------------------------------------------------------


def _check_value(value: Any, spec: Field, path: str, out: List[Finding]) -> None:
    def err(msg: str) -> None:
        out.append(Finding("error", "type", path, msg))

    kind = spec.kind
    if kind in ("text", "string", "id"):
        if not isinstance(value, str):
            err(f"expected a string, got {_type_name(value)}")
        elif kind == "text" and not value.strip():
            err("must not be empty")
        elif kind == "id" and not ID_PATTERN.match(value):
            err(f"'{value}' is not a valid ID (expected e.g. FR-001)")
    elif kind == "enum":
        if not isinstance(value, str) or value not in spec.choices:
            err(f"{_show(value)} is not one of: {', '.join(spec.choices)}")
    elif kind == "integer":
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            err("expected a non-negative integer")
    elif kind in ("id_list", "string_list"):
        if not isinstance(value, list):
            err(f"expected a list, got {_type_name(value)}")
            return
        if len(value) < spec.min_items:
            err(f"must contain at least {spec.min_items} item(s)")
        for i, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                out.append(Finding("error", "type", f"{path}[{i}]", "expected a non-empty string"))
            elif kind == "id_list" and not ID_PATTERN.match(item):
                out.append(Finding("error", "type", f"{path}[{i}]", f"'{item}' is not a valid ID"))
    elif kind == "score_map":
        if not isinstance(value, dict):
            err(f"expected an object, got {_type_name(value)}")
            return
        for key, score in value.items():
            if key not in JUDGED_CHARACTERISTICS:
                out.append(Finding(
                    "error", "type", f"{path}.{key}",
                    f"'{key}' is not an agent-judged characteristic "
                    f"({', '.join(JUDGED_CHARACTERISTICS)}); the others are computed",
                ))
            elif score is not None and (type(score) is not int or score not in SCORE_VALUES):
                out.append(Finding("error", "type", f"{path}.{key}",
                                   "score must be 0, 1, 2 or null (not applicable)"))
    elif kind == "text_map":
        if not isinstance(value, dict):
            err(f"expected an object, got {_type_name(value)}")
            return
        for key, text in value.items():
            if not isinstance(text, str):
                out.append(Finding("error", "type", f"{path}.{key}", "expected a string"))
    elif kind == "object":
        if not isinstance(value, dict):
            err(f"expected an object, got {_type_name(value)}")
    elif kind == "object_list":
        if not isinstance(value, list):
            err(f"expected a list, got {_type_name(value)}")
    else:  # pragma: no cover - programming error in a field table
        raise ValueError(f"unknown field kind {kind!r}")


def _type_name(value: Any) -> str:
    """JSON-style type name for messages."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _show(value: Any) -> str:
    return f"'{value}'" if isinstance(value, str) else _type_name(value)


def _check_object(obj: Any, spec: Dict[str, Field], path: str, out: List[Finding]) -> bool:
    if not isinstance(obj, dict):
        out.append(Finding("error", "type", path, f"expected an object, got {_type_name(obj)}"))
        return False
    for name, fspec in spec.items():
        if name not in obj:
            if fspec.required:
                out.append(Finding("error", "missing_field", f"{path}.{name}", "required field is missing"))
            continue
        _check_value(obj[name], fspec, f"{path}.{name}", out)
    for name in obj:
        if name not in spec:
            out.append(Finding("warning", "unknown_field", f"{path}.{name}", "unknown field (ignored)"))
    return True


def _find_cycles(graph: Dict[str, List[str]]) -> List[List[str]]:
    """Return dependency cycles, each as ``[a, b, ..., a]``.

    Iterative DFS (no recursion limit on long chains). Each cycle is reported
    once, rotated to start at its smallest ID.
    """
    white, grey, black = 0, 1, 2
    color = {node: white for node in graph}
    seen: set = set()
    cycles: List[List[str]] = []

    for root in sorted(graph):
        if color[root] != white:
            continue
        path: List[str] = [root]
        color[root] = grey
        iters = [iter(graph[root])]
        while iters:
            nxt = next(iters[-1], None)
            if nxt is None:
                color[path.pop()] = black
                iters.pop()
                continue
            if nxt not in color:
                continue
            if color[nxt] == grey:
                loop = path[path.index(nxt):]
                start = loop.index(min(loop))
                loop = loop[start:] + loop[:start]
                key = tuple(loop)
                if key not in seen:
                    seen.add(key)
                    cycles.append(loop + [loop[0]])
            elif color[nxt] == white:
                color[nxt] = grey
                path.append(nxt)
                iters.append(iter(graph[nxt]))
    return cycles


def validate(doc: Any) -> List[Finding]:
    """Validate structure, ID integrity, cross-references and origin rules.

    Returns all findings; the document is valid when none has level ``error``.
    """
    out: List[Finding] = []
    if not _check_object(doc, TOP_LEVEL_FIELDS, "$", out):
        return out

    if isinstance(doc.get("project"), dict):
        _check_object(doc["project"], PROJECT_FIELDS, "$.project", out)

    version = doc.get("schema_version")
    if isinstance(version, str) and version.strip() and version != SCHEMA_VERSION:
        out.append(Finding(
            "warning", "schema_version", "$.schema_version",
            f"schema_version '{version}' differs from supported '{SCHEMA_VERSION}'",
        ))

    # Per-object structure, ID prefix per section, ID uniqueness across the document.
    all_ids: Dict[str, str] = {}
    for section, spec in LIST_SECTIONS.items():
        raw = doc.get(section, [])
        if not isinstance(raw, list):
            continue
        for i, item in enumerate(raw):
            path = f"$.{section}[{i}]"
            if not _check_object(item, spec, path, out):
                continue
            if section == "quality_assessments":
                continue
            item_id = item.get("id")
            prefix = _prefix(item_id)
            if prefix is None:
                continue
            if prefix not in ID_PREFIXES[section]:
                out.append(Finding(
                    "error", "id_prefix", f"{path}.id",
                    f"'{item_id}' does not belong in {section} "
                    f"(allowed prefixes: {', '.join(ID_PREFIXES[section])})", (item_id,),
                ))
            if item_id in all_ids:
                out.append(Finding(
                    "error", "duplicate_id", f"{path}.id",
                    f"ID '{item_id}' is already used in {all_ids[item_id]}", (item_id,),
                ))
            else:
                all_ids[item_id] = path

    reqs = {r["id"]: r for _, r in _items(doc, "requirements") if _str(r.get("id"))}
    rules = {r["id"]: r for _, r in _items(doc, "rules") if _str(r.get("id"))}
    stakeholders = {s["id"] for _, s in _items(doc, "stakeholders") if _str(s.get("id"))}
    stories = {s["id"] for _, s in _items(doc, "user_stories") if _str(s.get("id"))}

    def check_refs(ids: Any, allowed: Any, path: str, what: str, owner: str) -> None:
        if not isinstance(ids, list):
            return
        for i, ref in enumerate(ids):
            if isinstance(ref, str) and ID_PATTERN.match(ref) and ref not in allowed:
                out.append(Finding(
                    "error", "broken_reference", f"{path}[{i}]",
                    f"{owner} references unknown {what} '{ref}'", (owner, ref),
                ))

    # Requirements: type/prefix agreement, references, origin rules.
    for i, req in _items(doc, "requirements"):
        path = f"$.requirements[{i}]"
        rid = _label(req.get("id"))
        expected = REQUIREMENT_TYPES.get(_str(req.get("type")) or "")
        if expected and _prefix(rid) and _prefix(rid) != expected:
            out.append(Finding(
                "error", "id_type_mismatch", f"{path}.id",
                f"'{rid}' has type '{req.get('type')}' so its ID should start with {expected}-", (rid,),
            ))
        check_refs(req.get("depends_on"), reqs, f"{path}.depends_on", "requirement", rid)
        check_refs(req.get("derived_from"), reqs, f"{path}.derived_from", "requirement", rid)
        check_refs(req.get("stakeholders"), stakeholders, f"{path}.stakeholders", "stakeholder", rid)
        if rid != "?" and rid in _str_list(req.get("depends_on")):
            out.append(Finding("error", "self_dependency", f"{path}.depends_on",
                               f"{rid} depends on itself", (rid,)))
        if rid != "?" and rid in _str_list(req.get("derived_from")):
            out.append(Finding("error", "self_derivation", f"{path}.derived_from",
                               f"{rid} is derived from itself", (rid,)))
        for parent in _str_list(req.get("derived_from")):
            if parent != rid and parent in reqs and reqs[parent].get("type") not in ("business", "user"):
                out.append(Finding(
                    "warning", "derivation", f"{path}.derived_from",
                    f"{rid} is derived from {parent}, which is not a business or user requirement",
                    (rid, parent),
                ))
        _check_origin(req, path, rid, out)

    for i, rule in _items(doc, "rules"):
        path = f"$.rules[{i}]"
        rid = _label(rule.get("id"))
        expected = RULE_KINDS.get(_str(rule.get("kind")) or "")
        if expected and _prefix(rid) and _prefix(rid) != expected:
            out.append(Finding(
                "error", "id_type_mismatch", f"{path}.id",
                f"'{rid}' has kind '{rule.get('kind')}' so its ID should start with {expected}-", (rid,),
            ))
        check_refs(rule.get("related"), all_ids, f"{path}.related", "item", rid)
        if rule.get("origin") == "confirmed" and _blank(rule.get("source")):
            out.append(Finding("error", "unsourced_confirmation", f"{path}.source",
                               f"{rid} is 'confirmed' but has no source", (rid,)))
        if rule.get("kind") == "assumption" and rule.get("origin") == "confirmed":
            out.append(Finding("warning", "confirmed_assumption", f"{path}.kind",
                               f"{rid} is a confirmed assumption; if the user confirmed it, "
                               "consider recording it as a constraint or requirement", (rid,)))

    for i, issue in _items(doc, "issues"):
        path = f"$.issues[{i}]"
        iid = _label(issue.get("id"))
        check_refs(issue.get("requirement_ids"), {**reqs, **rules}, f"{path}.requirement_ids",
                   "requirement or rule", iid)
        if issue.get("status") in ("resolved", "accepted_risk") and _blank(issue.get("resolution")):
            out.append(Finding("warning", "missing_resolution", f"{path}.resolution",
                               f"{iid} is {issue.get('status')} but has no resolution text", (iid,)))
        if issue.get("kind") in ("conflict", "duplicate", "overlap") \
                and len(set(_str_list(issue.get("requirement_ids")))) < 2:
            out.append(Finding("warning", "single_sided_conflict", f"{path}.requirement_ids",
                               f"{iid} is a {issue.get('kind')} but references fewer than two items", (iid,)))

    for i, story in _items(doc, "user_stories"):
        path = f"$.user_stories[{i}]"
        sid = _label(story.get("id"))
        check_refs(story.get("requirement_ids"), reqs, f"{path}.requirement_ids", "requirement", sid)
        if story.get("requirement_ids") == []:
            out.append(Finding("warning", "untraced_story", f"{path}.requirement_ids",
                               f"{sid} is not linked to any requirement", (sid,)))

    for i, ac in _items(doc, "acceptance_criteria"):
        path = f"$.acceptance_criteria[{i}]"
        aid = _label(ac.get("id"))
        story_id = _str(ac.get("story_id"))
        if story_id and ID_PATTERN.match(story_id) and story_id not in stories:
            out.append(Finding("error", "broken_reference", f"{path}.story_id",
                               f"{aid} references unknown user story '{story_id}'", (aid, story_id)))
        check_refs(ac.get("requirement_ids"), reqs, f"{path}.requirement_ids", "requirement", aid)

    seen_assessed: set = set()
    for i, qa in _items(doc, "quality_assessments"):
        path = f"$.quality_assessments[{i}]"
        rid = _str(qa.get("requirement_id"))
        if rid and ID_PATTERN.match(rid):
            if rid not in reqs:
                out.append(Finding("error", "broken_reference", f"{path}.requirement_id",
                                   f"quality assessment references unknown requirement '{rid}'", (rid,)))
            if rid in seen_assessed:
                out.append(Finding("error", "duplicate_assessment", f"{path}.requirement_id",
                                   f"{rid} is assessed more than once", (rid,)))
            seen_assessed.add(rid)
        scores = qa.get("scores") if isinstance(qa.get("scores"), dict) else {}
        reasons = qa.get("reasons") if isinstance(qa.get("reasons"), dict) else {}
        for key, score in scores.items():
            if score is not None and _blank(reasons.get(key)):
                out.append(Finding("warning", "unexplained_score", f"{path}.reasons.{key}",
                                   f"score for '{key}' on {_label(rid)} has no reason", (_label(rid),)))

    graph = {rid: _str_list(r.get("depends_on")) for rid, r in reqs.items()}
    for cycle in _find_cycles(graph):
        if len(cycle) == 2:  # a -> a is already reported as self_dependency
            continue
        out.append(Finding("error", "dependency_cycle", "$.requirements",
                           "circular dependency: " + " -> ".join(cycle), tuple(cycle[:-1])))
    return out


def _check_origin(req: Dict[str, Any], path: str, rid: str, out: List[Finding]) -> None:
    """Enforce: assumptions and suggestions are never silently treated as confirmed."""
    origin, status = req.get("origin"), req.get("status")
    if origin == "confirmed" and _blank(req.get("source")):
        out.append(Finding("error", "unsourced_confirmation", f"{path}.source",
                           f"{rid} is 'confirmed' but has no source; record where it was confirmed", (rid,)))
    if status == "approved" and origin in ORIGINS and origin != "confirmed":
        out.append(Finding("error", "unconfirmed_approval", f"{path}.status",
                           f"{rid} is 'approved' but its origin is '{origin}'; only confirmed "
                           "requirements can be approved", (rid,)))
    if origin == "open" and status in ("draft", "approved"):
        out.append(Finding("warning", "open_not_flagged", f"{path}.status",
                           f"{rid} has origin 'open' but status '{status}'; expected 'needs_clarification'",
                           (rid,)))


def has_errors(findings: List[Finding]) -> bool:
    return any(f.level == "error" for f in findings)


# --- Loading ----------------------------------------------------------------


def parse_document(text: str) -> Tuple[Any, List[Finding]]:
    """Parse JSON text. Returns ``(doc, [])`` or ``(None, [invalid_json error])``."""
    if text.startswith("﻿"):  # BOM written by some Windows editors / PowerShell
        text = text[1:]
    try:
        return json.loads(text), []
    except json.JSONDecodeError as exc:
        return None, [Finding("error", "invalid_json", f"line {exc.lineno}, column {exc.colno}",
                              f"not valid JSON: {exc.msg}")]


def load_document(path: str) -> Tuple[Any, List[Finding]]:
    """Read and parse a requirements file.

    Raises OSError (missing file, no permission) and UnicodeDecodeError
    (not UTF-8); the caller treats those as file errors, not validation errors.
    """
    with open(path, "r", encoding="utf-8-sig") as fh:
        return parse_document(fh.read())


def new_document(name: str, mode: str = "interactive", overview: str = "") -> Dict[str, Any]:
    """Return an empty, valid requirements document."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")
    return {
        "schema_version": SCHEMA_VERSION,
        "project": {
            "name": name,
            "overview": overview,
            "mode": mode,
            "scope_in": [],
            "scope_out": [],
            "clarification_round": 0,
        },
        "stakeholders": [],
        "requirements": [],
        "rules": [],
        "issues": [],
        "user_stories": [],
        "acceptance_criteria": [],
        "quality_assessments": [],
    }


# --- JSON Schema mirror -----------------------------------------------------

JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
SCHEMA_FILE = "schemas/requirements.schema.json"

_SECTION_DEFS = {
    "project": "project",
    "stakeholders": "stakeholder",
    "requirements": "requirement",
    "rules": "rule",
    "issues": "issue",
    "user_stories": "user_story",
    "acceptance_criteria": "acceptance_criterion",
    "quality_assessments": "quality_assessment",
}


def _field_schema(spec: Field) -> Dict[str, Any]:
    text = {"type": "string", "pattern": NON_EMPTY_PATTERN}
    any_id = {"type": "string", "pattern": ID_PATTERN.pattern}
    kind = spec.kind
    if kind == "text":
        return text
    if kind == "string":
        return {"type": "string"}
    if kind == "enum":
        return {"enum": list(spec.choices)}
    if kind == "id":
        return any_id
    if kind in ("id_list", "string_list"):
        schema: Dict[str, Any] = {"type": "array", "items": any_id if kind == "id_list" else text}
        if spec.min_items:
            schema["minItems"] = spec.min_items
        return schema
    if kind == "integer":
        return {"type": "integer", "minimum": 0}
    if kind == "score_map":
        return {
            "type": "object",
            "propertyNames": {"enum": list(JUDGED_CHARACTERISTICS)},
            "additionalProperties": {"enum": [*SCORE_VALUES, None]},
        }
    if kind == "text_map":
        return {"type": "object", "additionalProperties": {"type": "string"}}
    raise ValueError(f"no schema for field kind {kind!r}")


def _object_schema(fields: Dict[str, Field], description: str) -> Dict[str, Any]:
    return {
        "type": "object",
        "description": description,
        "required": [name for name, spec in fields.items() if spec.required],
        "properties": {name: _field_schema(spec) for name, spec in fields.items()},
    }


def _if_then(prop: str, value: str, then: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "if": {"properties": {prop: {"const": value}}, "required": [prop]},
        "then": then,
    }


def _confirmed_needs_source() -> Dict[str, Any]:
    return _if_then("origin", "confirmed", {
        "required": ["source"],
        "properties": {"source": {"type": "string", "pattern": NON_EMPTY_PATTERN}},
    })


def json_schema() -> Dict[str, Any]:
    """Build the JSON Schema (draft 2020-12) that mirrors the field tables.

    Cross-references, ID uniqueness, dependency cycles and warnings cannot be
    expressed in JSON Schema; only ``validate()`` checks those.
    """
    defs: Dict[str, Any] = {
        "project": _object_schema(PROJECT_FIELDS, "Project metadata."),
    }
    descriptions = {
        "stakeholders": "A stakeholder or user role.",
        "requirements": "A business, user, functional or non-functional requirement.",
        "rules": "A business rule, constraint or assumption.",
        "issues": "A quality problem: ambiguity, missing information, conflict, ...",
        "user_stories": "A user story linked to requirements.",
        "acceptance_criteria": "A Given/When/Then acceptance criterion for a user story.",
        "quality_assessments": "Agent-judged quality scores (0-2) with reasons for one requirement.",
    }
    for section, fields in LIST_SECTIONS.items():
        schema = _object_schema(fields, descriptions[section])
        if "id" in fields:
            schema["properties"]["id"] = {"type": "string", "pattern": id_pattern_for(ID_PREFIXES[section])}
        defs[_SECTION_DEFS[section]] = schema

    req = defs["requirement"]
    req["allOf"] = [
        _if_then("type", t, {"properties": {"id": {"pattern": id_pattern_for((p,))}}})
        for t, p in REQUIREMENT_TYPES.items()
    ] + [
        _if_then("status", "approved", {"properties": {"origin": {"const": "confirmed"}}}),
        _confirmed_needs_source(),
    ]
    rule = defs["rule"]
    rule["allOf"] = [
        _if_then("kind", k, {"properties": {"id": {"pattern": id_pattern_for((p,))}}})
        for k, p in RULE_KINDS.items()
    ] + [_confirmed_needs_source()]

    properties: Dict[str, Any] = {}
    for name, spec in TOP_LEVEL_FIELDS.items():
        if name == "schema_version":
            properties[name] = _field_schema(spec)
        elif spec.kind == "object":
            properties[name] = {"$ref": f"#/$defs/{_SECTION_DEFS[name]}"}
        else:
            properties[name] = {"type": "array", "items": {"$ref": f"#/$defs/{_SECTION_DEFS[name]}"}}

    return {
        "$schema": JSON_SCHEMA_DIALECT,
        "title": "Requirements Engineering Assistant: requirements.json",
        "description": (
            f"Schema version {SCHEMA_VERSION}. Generated from scripts/reqkit/model.py; do not edit "
            "by hand. Cross-references, unique IDs and dependency cycles are only checked by "
            "'rea.py validate'."
        ),
        "type": "object",
        "required": [name for name, spec in TOP_LEVEL_FIELDS.items() if spec.required],
        "properties": properties,
        "$defs": defs,
    }


def schema_text() -> str:
    """The schema file contents exactly as written to disk."""
    return json.dumps(json_schema(), indent=2, ensure_ascii=False) + "\n"


def write_schema(path: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(schema_text())


if __name__ == "__main__":  # python scripts/reqkit/model.py  -> regenerate the schema file
    import os

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    target = os.path.join(root, *SCHEMA_FILE.split("/"))
    write_schema(target)
    print(f"wrote {target}")
