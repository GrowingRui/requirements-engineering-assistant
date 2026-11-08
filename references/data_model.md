# Data model: `requirements.json`

The agent writes only this file. `rea.py validate` checks it; `rea.py export` turns it into
`requirements.md`. The machine-readable mirror is `schemas/requirements.schema.json`.

## Top level

| Field | Required | Content |
|---|---|---|
| `schema_version` | yes | Always `"1.0"` |
| `project` | yes | Project metadata (below) |
| `requirements` | yes | List of requirements (may be empty at first) |
| `stakeholders` | no | Users, roles and other stakeholders |
| `rules` | no | Business rules, constraints and assumptions |
| `issues` | no | Quality problems found and their questions |
| `user_stories` | no | User stories linked to requirements |
| `acceptance_criteria` | no | Given/When/Then criteria linked to stories |
| `quality_assessments` | no | Agent-judged scores with reasons |

`rea.py init` writes all of these with empty lists. Unknown fields produce a warning and are ignored.

## IDs

- Format: prefix, hyphen, at least three digits: `FR-001`, `NFR-012`, `ISS-104`.
- Unique across the whole document. Never reuse an ID, even after an item is rejected.
- Number in order of creation; gaps are fine.

| Section | Prefixes |
|---|---|
| stakeholders | `SH` |
| requirements | `BR` business, `UR` user, `FR` functional, `NFR` non-functional (must match `type`) |
| rules | `BRL` business rule, `CON` constraint, `ASM` assumption (must match `kind`) |
| issues | `ISS` |
| user_stories | `US` |
| acceptance_criteria | `AC` |

## Origin: where an item comes from

Every stakeholder, requirement and rule has an `origin`.

| Origin | Meaning | Example |
|---|---|---|
| `confirmed` | The user said it or confirmed it. `source` must say where. | "Users can delete their account." |
| `assumed` | You inferred it from the description; the user has not confirmed it. | Users need an account because the text mentions "my collection". |
| `suggested` | You propose it as good practice; the user did not ask for it. | A response-time target. |
| `open` | Needed, but nobody knows the answer yet. | Which platforms are supported? |

Rules enforced by `rea.py validate`:
- `confirmed` without a non-empty `source` is an **error**.
- `status: "approved"` with any origin other than `confirmed` is an **error**.
- `origin: "open"` with status `draft` or `approved` is a warning: use `needs_clarification`.
- A `confirmed` assumption (`ASM`) is a warning: if the user confirmed it, record it as a
  constraint or requirement instead.

Good `source` values: `"user input"`, `"user input, input.md line 4"`, `"clarification round 2"`.
Leave `source` as `""` for `assumed`, `suggested` and `open` items unless you can cite the text
you inferred them from.

## `project`

| Field | Required | Content |
|---|---|---|
| `name` | yes | Project name |
| `overview` | yes | One paragraph; may be `""` |
| `mode` | yes | `interactive` or `automatic` |
| `scope_in` | no | Features or areas in scope |
| `scope_out` | no | Explicitly out of scope (also silences missing-topic hints for those areas) |
| `clarification_round` | no | Number of completed question rounds, starting at `0` |

## `stakeholders`

| Field | Required | Content |
|---|---|---|
| `id` | yes | `SH-001` |
| `name` | yes | Role name, e.g. "Collector", "Administrator" |
| `description` | no | Who they are |
| `permissions` | no | What this role may do, e.g. `["delete any post"]` |
| `origin` | yes | See above |

## `requirements`

| Field | Required | Content |
|---|---|---|
| `id` | yes | Prefix matches `type` |
| `type` | yes | `business`, `user`, `functional`, `non_functional` |
| `title` | yes | Short name |
| `description` | yes | One requirement, one "shall" statement |
| `priority` | yes | `must`, `should`, `could`, `wont`, `unset` (use `unset` until the user decides) |
| `origin` | yes | See above |
| `status` | yes | `draft`, `needs_clarification`, `approved`, `deferred`, `rejected` |
| `source` | yes | Where it came from; may be `""` unless `confirmed` |
| `fit_criterion` | no | Measurable target that makes it testable, e.g. "p95 < 2 s with 200 users" |
| `rationale` | no | Why it exists |
| `depends_on` | no | IDs of requirements this one needs (no self-reference, no cycles) |
| `derived_from` | no | IDs of the business or user requirements it refines |
| `stakeholders` | no | `SH` IDs it concerns |

Status guide:
- `draft`: extracted, no open blocker.
- `needs_clarification`: an open issue blocks it.
- `approved`: confirmed by the user and ready. Only for `confirmed` requirements.
- `deferred`: not for this release. Traceability checks skip it, and its score does not count
  missing stories or criteria.
- `rejected`: dropped. Kept for history; not scored or linted.

Write one testable statement per requirement: "The system shall ..." or "A collector shall be
able to ...". Split "and" requirements that could be delivered separately.

## `rules`

| Field | Required | Content |
|---|---|---|
| `id` | yes | Prefix matches `kind` |
| `kind` | yes | `business_rule`, `constraint`, `assumption` |
| `statement` | yes | The rule itself |
| `origin` | yes | See above |
| `source` | yes | May be `""` unless `confirmed` |
| `related` | no | IDs of any items it affects |

- Business rule: a policy of the domain ("A student may hold at most 2 bookings").
- Constraint: a fixed limit on the solution ("Must run on Android 10+").
- Assumption: something taken as true without confirmation ("Users have a smartphone camera").

## `issues`

| Field | Required | Content |
|---|---|---|
| `id` | yes | `ISS-001` |
| `kind` | yes | `ambiguity`, `missing_information`, `conflict`, `duplicate`, `overlap`, `terminology`, `dependency` |
| `severity` | yes | `critical`, `important`, `optional` (see requirements_quality.md) |
| `status` | yes | `open`, `resolved`, `accepted_risk` |
| `requirement_ids` | yes | Requirement or rule IDs involved; may be `[]` for document-wide gaps |
| `description` | yes | What is wrong |
| `missing_information` | no | What exactly is unknown |
| `question` | no | The question to ask the user |
| `suggestion` | no | Your proposed answer; shown as "Suggestion (not confirmed)" |
| `resolution` | no | How it was settled; expected once `resolved` or `accepted_risk` |

`conflict`, `duplicate` and `overlap` issues should list at least two IDs.

## `user_stories`

| Field | Required | Content |
|---|---|---|
| `id` | yes | `US-001` |
| `role` | yes | Who; ideally a stakeholder name |
| `goal` | yes | What they want |
| `benefit` | yes | Why |
| `requirement_ids` | yes | Requirements this story covers (should not be empty) |
| `priority` | yes | Same values as requirements |
| `description` | no | Notes |

## `acceptance_criteria`

| Field | Required | Content |
|---|---|---|
| `id` | yes | `AC-001` |
| `story_id` | yes | The `US` ID it belongs to |
| `requirement_ids` | yes | Requirements it verifies |
| `title` | yes | Short scenario name |
| `type` | yes | `positive`, `negative`, `boundary` |
| `given` | yes | At least one precondition |
| `when` | yes | At least one action |
| `then` | yes | At least one observable outcome |

## `quality_assessments`

One entry per requirement, at most.

| Field | Required | Content |
|---|---|---|
| `requirement_id` | yes | The requirement scored |
| `scores` | yes | Only `clarity`, `completeness`, `feasibility`; each `0`, `1`, `2` or `null` (not applicable) |
| `reasons` | yes | One reason per score key |

The other characteristics (unambiguity, verifiability, consistency, traceability) are computed
by the script; putting them in `scores` is an error.

## Example

```json
{
  "schema_version": "1.0",
  "project": {"name": "Room Booking", "overview": "Students book library study rooms.",
              "mode": "interactive", "scope_in": ["Booking"], "scope_out": ["Payment"],
              "clarification_round": 1},
  "stakeholders": [
    {"id": "SH-001", "name": "Student", "permissions": ["create booking", "cancel own booking"],
     "origin": "confirmed"}
  ],
  "requirements": [
    {"id": "FR-001", "type": "functional", "title": "Book a room",
     "description": "A student shall be able to book a free study room for 1 to 3 hours.",
     "priority": "must", "origin": "confirmed", "status": "approved", "source": "user input",
     "stakeholders": ["SH-001"]},
    {"id": "NFR-001", "type": "non_functional", "title": "Booking response time",
     "description": "Booking confirmation shall be shown within the response-time target.",
     "priority": "should", "origin": "suggested", "status": "draft", "source": "",
     "fit_criterion": "95% of bookings confirm in under 2 s with 200 concurrent users"}
  ],
  "rules": [
    {"id": "BRL-001", "kind": "business_rule", "statement": "A student may hold at most 2 future bookings.",
     "origin": "confirmed", "source": "clarification round 1", "related": ["FR-001"]}
  ],
  "issues": [
    {"id": "ISS-001", "kind": "missing_information", "severity": "important", "status": "open",
     "requirement_ids": ["FR-001"], "description": "Opening hours are not defined.",
     "question": "During which hours can rooms be booked?",
     "suggestion": "Library opening hours, 08:00-22:00."}
  ],
  "user_stories": [
    {"id": "US-001", "role": "Student", "goal": "book a study room for a time slot",
     "benefit": "I have a quiet place to study", "requirement_ids": ["FR-001"], "priority": "must"}
  ],
  "acceptance_criteria": [
    {"id": "AC-001", "story_id": "US-001", "requirement_ids": ["FR-001"],
     "title": "Book a free room", "type": "positive",
     "given": ["Room 3 is free from 10:00 to 12:00"], "when": ["the student books it for 10:00-12:00"],
     "then": ["the booking is confirmed", "room 3 shows as booked from 10:00 to 12:00"]}
  ],
  "quality_assessments": [
    {"requirement_id": "FR-001", "scores": {"clarity": 2, "completeness": 1, "feasibility": 2},
     "reasons": {"clarity": "One action, clear actor and object.",
                 "completeness": "Opening hours are still open (ISS-001).",
                 "feasibility": "Standard booking feature."}}
  ]
}
```

## Fixing validation errors

| Code | Cause | Fix |
|---|---|---|
| `invalid_json` | Syntax error | Fix the JSON at the reported line and column |
| `missing_field` | Required field absent | Add it (empty string or list where allowed) |
| `type` | Wrong value type, empty text, bad enum value, bad score | Use the allowed values above |
| `id_prefix` | ID prefix not allowed in that section | Use the section's prefix |
| `id_type_mismatch` | Prefix does not match `type` / `kind` | Change the ID or the type |
| `duplicate_id` | Same ID used twice | Give the second item a new ID and update links |
| `broken_reference` | A link points to an ID that does not exist | Fix the ID or remove the link |
| `self_dependency`, `self_derivation` | An item links to itself | Remove the self-link |
| `dependency_cycle` | `depends_on` forms a loop | Break the loop; raise a `dependency` issue if unclear |
| `unsourced_confirmation` | `confirmed` with empty `source` | Add the source, or change the origin |
| `unconfirmed_approval` | `approved` but not `confirmed` | Use `draft`, or confirm with the user first |
| `duplicate_assessment` | Two assessments for one requirement | Merge them |

Validation warnings:

| Code | Meaning |
|---|---|
| `unknown_field` | Field not in the model; it is ignored |
| `schema_version` | Version differs from `1.0` |
| `derivation` | `derived_from` points to a requirement that is not business or user |
| `confirmed_assumption` | An assumption marked `confirmed` |
| `open_not_flagged` | `open` requirement not marked `needs_clarification` |
| `missing_resolution` | Issue resolved or accepted without `resolution` text |
| `single_sided_conflict` | Conflict, duplicate or overlap issue with fewer than two IDs |
| `untraced_story` | Story with an empty `requirement_ids` |
| `unexplained_score` | Quality score without a reason |
