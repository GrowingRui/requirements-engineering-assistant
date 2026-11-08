# Requirements Engineering Assistant: Implementation Plan

Status: **approved and built** (phases 0–7). Kept as the design record for version 0.1.0.

---

## 1. Goal

Build a reusable **Agent Skill** that turns informal software ideas into structured,
testable requirements. Its main feature is **requirements quality analysis**:
finding ambiguity, missing information, conflicts and untestable requirements.
It is more than a user story generator.

**Two parts work together:**

| Part | Who does it | What it does |
|---|---|---|
| Understanding and judgement | The AI agent that loads the skill (Claude Code, Codex, ...) | Reads the user's description, extracts requirements, judges ambiguity, asks clarification questions, writes user stories and acceptance criteria |
| Deterministic checks | Python scripts in the skill | Validates the data, checks IDs and links, flags vague words, finds duplicate candidates, computes quality scores and traceability, generates the Markdown document |

## 2. Key decisions (changes from the original idea)

1. **Zero installation.** Python standard library only. No Pydantic, no pip install.
   Tests use the built-in `unittest` module, and pytest can also run them if it's installed.
2. **One source of truth.** The agent writes only `requirements.json`. The script
   generates `requirements.md` from it, so the two files can never contradict each other.
3. **Data model defined once.** The data model lives in Python (`model.py`).
   `schemas/requirements.schema.json` mirrors it for other tools, and a test fails if they drift apart.
4. **Every item has an `origin`:** `confirmed | assumed | suggested | open`.
   This lets the script enforce "never silently turn an assumption into a confirmed requirement":
   - `approved` status is only allowed when origin is `confirmed`.
   - `confirmed` requires a `source` (where it was confirmed).
5. **One command-line tool with subcommands** instead of four separate scripts.
6. **Honest scoring.** The script computes some quality scores. The AI judges the rest
   and must give a written reason. The README states that the score is a guide,
   not an industry certification.
7. **`requirements.json` saves progress.** In interactive mode each clarification
   round updates the file, so work can stop and continue later.
8. **Smaller scope.** Business Rules, Constraints and Assumptions share one `rules`
   list with a `kind` field. Business and User Requirements are optional.

## 3. Cost

**No extra cost.**
- Python, the standard library and the MIT license are free. GitHub is free for public repositories.
- The skill makes **no API calls**. It uses the AI agent the user is already running.
- The only cost is normal usage of your existing Claude plan while it's being built.
- There will be no automated AI test suite, because that would need paid API calls.

## 4. Directory structure

```
requirements-engineering-assistant/
├── SKILL.md                         # Instructions the agent follows (workflow, modes, rules)
├── README.md                        # Human documentation
├── LICENSE                          # MIT
├── PLAN.md                          # This file
│
├── scripts/
│   ├── rea.py                       # Command-line entry point
│   └── reqkit/                      # Internal package (standard library only)
│       ├── __init__.py
│       ├── model.py                 # Data model + structural validation
│       ├── checks.py                # Vague words, duplicates, conflicts, gaps (lint)
│       ├── quality.py               # Quality scores (computed + AI-judged)
│       └── render.py                # JSON -> Markdown (+ traceability matrix)
│
├── references/                      # Loaded by the agent only when needed
│   ├── data_model.md                # Every JSON field explained, with examples
│   ├── requirements_quality.md      # Quality characteristics + scoring rubric
│   ├── user_story_guidelines.md     # INVEST, story format, splitting
│   ├── acceptance_criteria_guidelines.md  # Given/When/Then, positive/negative/boundary
│   └── clarification_guidelines.md  # How to prioritise and group questions
│
├── schemas/
│   └── requirements.schema.json     # JSON Schema (draft 2020-12) mirror of model.py
│
├── examples/
│   └── rock-identification/
│       ├── input.md                 # Informal project description
│       ├── clarifications.md        # Example question/answer round
│       ├── requirements.json        # Result produced by following SKILL.md
│       └── requirements.md          # Generated from the JSON by the script
│
└── tests/
    ├── fixtures/                    # Small JSON files, valid and invalid
    ├── test_model.py
    ├── test_checks.py
    ├── test_quality.py
    ├── test_render.py
    ├── test_schema_sync.py
    └── test_cli.py
```

## 5. Data model (`requirements.json`)

```jsonc
{
  "schema_version": "1.0",
  "project": { "name", "overview", "mode": "interactive|automatic",
               "scope_in": [], "scope_out": [], "clarification_round": 0 },
  "stakeholders": [ { "id": "SH-001", "name", "description", "permissions": [], "origin" } ],
  "requirements": [ {
      "id": "FR-001",                       // FR / NFR / BR / UR, must match type
      "type": "functional|non_functional|business|user",
      "title", "description",
      "priority": "must|should|could|wont|unset",
      "origin": "confirmed|assumed|suggested|open",
      "status": "draft|needs_clarification|approved|deferred|rejected",
      "source": "user input, round 1",      // where it came from
      "fit_criterion": "p95 response < 3 s", // optional measurable target
      "rationale", "depends_on": [], "derived_from": [], "stakeholders": []
  } ],
  "rules": [ { "id": "BRL-001|CON-001|ASM-001",
               "kind": "business_rule|constraint|assumption",
               "statement", "origin", "source", "related": [] } ],
  "issues": [ { "id": "ISS-001",
                "kind": "ambiguity|missing_information|conflict|duplicate|overlap|terminology|dependency",
                "severity": "critical|important|optional",
                "status": "open|resolved|accepted_risk",
                "requirement_ids": [], "description", "missing_information",
                "question", "suggestion", "resolution" } ],
  "user_stories": [ { "id": "US-001", "role", "goal", "benefit",
                      "requirement_ids": [], "priority", "description" } ],
  "acceptance_criteria": [ { "id": "AC-001", "story_id": "US-001", "requirement_ids": [],
                             "title", "type": "positive|negative|boundary",
                             "given": [], "when": [], "then": [] } ],
  "quality_assessments": [ { "requirement_id": "FR-001",
                             "scores": { "clarity": 2, "completeness": 1, "feasibility": null },
                             "reasons": { "clarity": "...", "completeness": "..." } } ]
}
```

Notes:
- The `suggestion` field on issues is always shown as **"Suggestion (not confirmed)"** in the Markdown.
- `null` score = not applicable. It is not counted against the requirement.

## 6. Command-line tool (`scripts/rea.py`)

| Command | Purpose |
|---|---|
| `rea.py init --name "X" [--mode automatic]` | Create an empty, valid `requirements.json` |
| `rea.py scan input.md` | Flag vague words in the user's raw text before analysis (line numbers) |
| `rea.py validate requirements.json` | Structure, IDs, broken links, dependency cycles, origin rules |
| `rea.py lint requirements.json [--json]` | Validation + quality warnings + hints + scores |
| `rea.py export requirements.json [--out DIR]` | Generate `requirements.md` (refuses if the JSON is invalid) |

Exit codes: `0` OK, `1` validation errors, `2` usage or file errors.
Output is plain text by default and `--json` for machine use.

### What the checks find

**Errors (invalid document):**
- Missing or wrong-type fields.
- Duplicate IDs, or an ID prefix that doesn't match the type.
- References to IDs that don't exist.
- Self-dependency and circular dependencies.
- `approved` but not `confirmed`, or `confirmed` without a source.

**Warnings (likely quality problems):**
- Vague words without a fit criterion or a tracked ambiguity issue.
- Vague words in acceptance criteria outcomes.
- Possible duplicates.
- Possible contradictions (similar text, but only one is negated).
- Functional requirement with no user story.
- Requirement with no acceptance criterion and no fit criterion.
- Story with no acceptance criteria.
- Approved requirement with an open critical issue.

**Hints (may not apply to this project):**
- Overlapping requirements.
- Possibly missing topics: for example, the text mentions "upload photo" but nothing covers size or format limits.
- No non-functional requirements at all.
- Roles without permissions.
- A story with only positive scenarios.

All of these are **candidates**. The AI confirms or dismisses each one and records the real
problems as `issues`. A related pair of requirements is not reported as a conflict.

## 7. Quality assessment (0–2 per characteristic)

| Characteristic | Who scores | Rule |
|---|---|---|
| Clarity | AI | Judged, reason required |
| Completeness | AI | Judged, reason required |
| Feasibility | AI | Judged, reason required (often `null` if unknown) |
| Unambiguity | Script | 2 = no vague words, or a fit criterion is defined; 1 = vague words but tracked as an issue; 0 = untracked vague words |
| Verifiability | Script | 2 = has acceptance criteria or a fit criterion; 1 = has a story but no criteria; 0 = nothing. Business requirements = N/A |
| Consistency | Script | 0 = in an open critical conflict/duplicate; 1 = in another open conflict/overlap/terminology issue; 2 = none |
| Traceability | Script | 2 = has a source and is linked up or down; 1 = has a source only; 0 = no source |

The report shows the score per requirement, the overall percentage of applicable points,
the reason for each score, and a list of requirements that need improvement.

## 8. Agent workflow (written in `SKILL.md`)

**Interactive mode (default):**
1. Receive the description. Optionally run `rea.py scan` on it.
2. Extract requirements into `requirements.json`, marking each with its `origin`.
   Nothing is invented. Anything guessed is `assumed` or `suggested`.
3. Run `rea.py lint`. Review the candidates and record real problems as `issues`.
4. Present the findings briefly: the requirements found, then the issues by severity.
5. Ask at most **3–7 questions per round**, most important first, with related questions grouped.
   Each question has a suggested answer the user can simply accept.
6. Wait for the answers. Update the JSON: answered items become `confirmed` with the source
   "clarification round N". Resolved issues get a `resolution`.
7. Repeat only while **critical** or important issues remain. The user can say "enough" at any time.
8. Generate user stories, acceptance criteria and AI quality judgements.
9. Run `rea.py validate`, fix errors, then run `rea.py export` to write the final documents.

**Automatic mode** ("just analyse it"): steps 1–3 and 8–9. No questions are asked.
Unresolved items stay `open` or `assumed` and are listed under "Open Questions".

**Rules for the agent:**
- Only create or edit the requirements files. Never touch the user's source code.
- Keep SKILL.md short and load the reference files only when needed.
- If Python is not available, still produce the JSON and Markdown by hand and say that validation was skipped.

## 9. Generated `requirements.md` sections

1. Project Overview
2. Scope
3. Stakeholders and User Roles
4. Business Requirements
5. Functional Requirements
6. Non-Functional Requirements
7. Business Rules and Constraints
8. Assumptions
9. Ambiguities and Open Questions
10. Conflict and Consistency Analysis
11. User Stories
12. Acceptance Criteria
13. Requirements Quality Assessment
14. Requirements Traceability Matrix

Empty sections show *"Not yet available."* or are left out where they don't apply.
The traceability matrix lists, for each requirement: its parent requirements, user stories,
acceptance criteria, status, and gaps. It only shows links that exist in the JSON,
with no invented links.

## 10. Testing

**Automated (`python -m unittest discover -s tests`)**, covering the 10 required scenarios
with small JSON fixtures:

| # | Scenario | What is checked |
|---|---|---|
| 1 | Clear, complete requirement | No errors, no warnings, full score |
| 2 | Ambiguous requirement ("fast", "user-friendly") | Vague words flagged; disappears once a fit criterion is added |
| 3 | Missing information | Topic hints (upload limits, auth); critical issues listed |
| 4 | Contradictory requirements | Negation-contradiction candidate; conflict lowers the consistency score |
| 5 | Duplicate requirements | Duplicate candidate found; not reported once tracked as an issue |
| 6 | Multiple user roles | Roles without permissions hint; stakeholder references checked |
| 7 | Non-functional requirements | Fit criterion makes them verifiable |
| 8 | Dependencies | Broken reference, self-dependency and cycle detected |
| 9 | Incomplete acceptance criteria | Empty Given/When/Then rejected; story without AC flagged |
| 10 | Complete small project | The rock-identification example validates, exports and its Markdown matches the JSON |

Also tested:
- The origin rules (approved + assumed = error).
- Invalid JSON and wrong types.
- The schema and Python model stay in sync.
- The CLI exit codes.

**Manual:** I will follow `SKILL.md` myself on the rock-identification example
in this Claude Code session. That produces the example output and shows whether the instructions work.

## 11. Example project

**AI-powered rock and mineral identification app.** Users photograph a rock, get an
identification with a confidence level, and manage a personal collection.

The input will be written informally on purpose, with:
- vague words ("fast", "accurate", "easy to use"),
- missing details (photo size, offline use, privacy),
- one contradiction (works offline vs. needs a cloud model),
- one duplicate.

This shows the whole workflow. The skill itself is not tied to this domain.

## 12. Platform compatibility

| Platform | How to install | Tested? |
|---|---|---|
| Claude Code | Copy/clone the folder into `~/.claude/skills/requirements-engineering-assistant/` (personal) or `.claude/skills/...` (one project) | **Yes** (manual run in this session) |
| Codex | Uses the same `SKILL.md` format; install path documented from the official docs | **No**, marked as untested |
| Cursor | Install path documented from the official docs (recent versions); fallback is to reference `SKILL.md` from a rule | **No**, marked as untested |
| Any agent without skill support | Paste or reference `SKILL.md`; the scripts run anywhere with Python 3 | n/a |

Before writing the README I will check the official docs for the current Codex and Cursor install paths.

## 13. Known limitations (to be stated in the README)

- The vague-word and similarity checks are word lists and text similarity, not real
  understanding. They give false positives and miss things. The AI makes the final decision.
- Contradiction detection only catches simple cases (negation). Real conflicts are found by the AI.
- The quality score is a transparent guide, not an objective measurement.
- The quality of the result depends on the AI agent that runs the skill.
- Requires Python 3.9+ for validation and export. Without Python the skill still works, but nothing is validated.
- English only for the vague-word list in version 1.

## 14. Development phases

We build one phase at a time. At the end of each phase:
1. All tests from that phase (and earlier phases) pass.
2. I report what was built and the test results, then stop.
3. You check it. I commit and push **only when you say so**
   (author `GrowingRui <xiarui091@gmail.com>`, one commit per phase).
4. The next phase starts only after that.

---

### Phase 0: Project setup
**Goal:** a clean, versioned starting point.
- `git init`, `.gitignore`, `LICENSE` (MIT, GrowingRui), this `PLAN.md`.
- Folder structure from section 4.
- Draft files `model.py` and `checks.py` are kept; they are finished and tested in Phases 1 and 2.

**Done when:** the local repository is set up and ready for the first commit.

---

### Phase 1: Data model and validation
**Goal:** a reliable `requirements.json` format that the script can check.
- `scripts/reqkit/model.py`: fields, allowed values, ID rules, cross-reference checks,
  dependency cycles, origin rules (`approved` needs `confirmed`; `confirmed` needs a source).
- `schemas/requirements.schema.json`: JSON Schema mirror.
- Tests: `test_model.py`, `test_schema_sync.py`.
- Scenarios covered: **8** (dependencies) and **9** (incomplete acceptance criteria),
  plus invalid JSON, wrong types and the origin rules.

**Done when:** valid fixtures pass, every invalid fixture produces the expected error,
and the schema matches the Python model.

---

### Phase 2: Quality checks (lint)
**Goal:** the core differentiator, which is to find quality problems automatically.
- `scripts/reqkit/checks.py`: vague-word list, weak phrases, duplicate, overlap and
  contradiction candidates, traceability gaps, missing-information hints.
- Tests: `test_checks.py`.
- Scenarios covered: **2** (ambiguous), **3** (missing information), **4** (contradiction),
  **5** (duplicate), **6** (multiple roles), **7** (non-functional).

**Done when:** each scenario fixture triggers the expected finding, and a clean fixture
(scenario **1**) triggers none.

---

### Phase 3: Quality scoring and Markdown export
**Goal:** turn the JSON into a readable, professional document.
- `scripts/reqkit/quality.py`: computed scores, AI-judged scores, overall percentage,
  list of requirements needing improvement.
- `scripts/reqkit/render.py`: the 14 sections of `requirements.md` and the traceability matrix.
- Tests: `test_quality.py`, `test_render.py`. Every ID in the JSON appears in the Markdown,
  and nothing appears in the Markdown that isn't in the JSON.

**Done when:** a fixture exports to Markdown that is correct and consistent with its JSON.

---

### Phase 4: Command-line tool
**Goal:** one simple command for the agent (and humans) to use.
- `scripts/rea.py` with `init`, `scan`, `validate`, `lint`, `export`; text and `--json` output;
  exit codes 0 / 1 / 2; UTF-8 output that works on the Windows console.
- Tests: `test_cli.py`.

**Done when:** every command works on Windows from the terminal and all tests pass.

---

### Phase 5: Skill instructions
**Goal:** the agent knows exactly how to run the requirements workflow.
- `SKILL.md`: interactive and automatic modes, workflow steps, rules
  (no invented facts, origins, at most 3–7 questions per round, never edit source code).
- `references/`: data model guide, quality rubric, user story guidelines,
  acceptance criteria guidelines, clarification question guidelines.

**Done when:** SKILL.md is short and clear, and every script command it mentions exists and works.

---

### Phase 6: Example project (end-to-end test)
**Goal:** prove the whole skill works on a realistic project.
- `examples/rock-identification/input.md`: an informal description with deliberate problems.
- I follow SKILL.md myself in this session: analysis, clarification round
  (`clarifications.md`), then the final `requirements.json`, then the exported `requirements.md`.
- Scenario **10** (complete small project) is added as an automated test on this example.

**Done when:** the example validates, exports, and the findings match the deliberate problems.

---

### Phase 7: Documentation and release
**Goal:** ready to publish on GitHub.
- Check the current Codex and Cursor install instructions in their official docs.
- `README.md`: overview, features, architecture, installation per platform, usage,
  example, limitations, future work, license.
- Final checks: all tests, schema validation, JSON/Markdown consistency, a fresh install test
  in `~/.claude/skills/`, and a README review.
- Tag the first release (`v0.1.0`) on GitHub, **only after you confirm**.

**Done when:** the final report (features, test results, limitations, remaining work) is delivered.

## 15. Future improvements (not in version 1)

- Export to CSV or Jira/GitHub issues.
- Vague-word lists in more languages.
- Change history between clarification rounds (diff of requirements).
- Optional evaluation suite for people who want to test skill behaviour with an API key.
- Optional HTML report.
