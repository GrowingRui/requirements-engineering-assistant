# Requirements Engineering Assistant

An **Agent Skill** that turns informal software ideas into structured, testable requirements,
and checks their quality: ambiguity, missing information, conflicts, duplicates and
requirements that cannot be tested.

You describe an app in your own words. The AI agent you already use (Claude Code, Codex,
Cursor, ...) loads this skill, asks you a few focused questions, and writes a requirements
document with user stories, Given/When/Then acceptance criteria, a quality score per
requirement and a traceability matrix.

- **Free and zero-install.** Python standard library only. No API keys, no paid services, no `pip install`.
- **One source of truth.** The agent writes `requirements.json`; the script generates
  `requirements.md` from it, so the two can never disagree.
- **Honest about uncertainty.** Every item is marked `confirmed`, `assumed`, `suggested` or
  `open`. The script refuses to let an assumption be approved as if the user had confirmed it.

## Contents

- [Features](#features)
- [How it works](#how-it-works)
- [Installation](#installation)
- [Usage](#usage)
- [Example](#example)
- [Command-line tool](#command-line-tool)
- [Limitations](#limitations)
- [Development](#development)
- [Future work](#future-work)
- [License](#license)

## Features

**Requirements extraction**
- Functional, non-functional, business and user requirements; business rules, constraints and
  assumptions; stakeholders and their permissions; scope in and out.
- Each item records where it came from (`source`) and how certain it is (`origin`).

**Quality analysis** (the main feature)
- Vague words and weak phrases ("fast", "user-friendly", "if possible") that have no measurable
  target.
- Possible duplicates, overlaps and simple contradictions.
- Topics that are probably missing, for example photo uploads with no size or format limits, or
  personal data with no privacy rules.
- Traceability gaps: requirements with no user story, stories with no acceptance criteria,
  requirements that cannot be verified.
- Broken references, circular dependencies and invalid origins.

The script only reports **candidates**. The agent confirms or dismisses each one, adds problems
the script cannot see (real conflicts, unclear terms, missing actors), and records the real ones
as issues with a severity, a clarification question and a suggested answer.

**Clarification rounds**
- Interactive mode (default): 3–7 questions per round, most important first, each with a
  suggested answer you can simply accept. Progress is saved in the JSON, so you can stop and
  continue later.
- Automatic mode ("just analyse it"): no questions. Unresolved items are listed as open questions.

**Output**
- User stories (INVEST), acceptance criteria with positive, negative and boundary cases.
- A quality score from 0 to 2 for seven characteristics per requirement. Four are computed by the
  script (unambiguity, verifiability, consistency, traceability); three are judged by the agent
  (clarity, completeness, feasibility), always with a written reason.
- A requirements traceability matrix that shows only links that exist in the data.

The generated `requirements.md` has 14 sections: overview, scope, stakeholders, business,
functional and non-functional requirements, business rules and constraints, assumptions,
ambiguities and open questions, conflict analysis, user stories, acceptance criteria, quality
assessment and traceability matrix.

## How it works

| Part | Done by | Responsibility |
|---|---|---|
| Understanding and judgement | The AI agent, following [SKILL.md](SKILL.md) | Reads the description, extracts requirements, judges ambiguity, asks questions, writes stories and criteria |
| Deterministic checks | [scripts/rea.py](scripts/rea.py) (Python, standard library) | Validates the data, checks IDs and links, flags vague words, finds duplicate candidates, computes scores, generates the Markdown |

```
 your description ──► agent ──► requirements.json ──► rea.py lint ──► agent reviews findings
                        ▲                                                    │
                        └──────────── clarification questions ◄──────────────┘
                                             │ (when done)
                                             ▼
                              rea.py validate ──► rea.py export ──► requirements.md
```

Repository layout:

```
SKILL.md                    Instructions the agent follows (workflow, modes, rules)
scripts/rea.py              Command-line entry point
scripts/reqkit/             model.py (data model + validation), checks.py (lint),
                            quality.py (scores), render.py (Markdown export)
references/                 Guides the agent loads only when it needs them
schemas/                    JSON Schema mirror of the data model
examples/rock-identification/  A complete worked example
tests/                      unittest suite
```

The data model is defined once in [scripts/reqkit/model.py](scripts/reqkit/model.py) and
explained field by field in [references/data_model.md](references/data_model.md).
[schemas/requirements.schema.json](schemas/requirements.schema.json) mirrors it for other tools,
and a test fails if the two drift apart.

## Installation

You need an AI agent that supports Agent Skills and, for validation and export, **Python 3.9 or
newer** (`python`, `python3` or `py -3`). Nothing else is installed.

A skill is just a folder that contains `SKILL.md`. Clone (or download and unzip) this repository
into the agent's skills folder, keeping the folder name `requirements-engineering-assistant`.

### Claude Code

Personal (all projects):

```bash
git clone https://github.com/GrowingRui/requirements-engineering-assistant.git ~/.claude/skills/requirements-engineering-assistant
```

One project only: clone into `.claude/skills/requirements-engineering-assistant` inside the project.
On Windows, `~` is your user folder, for example `C:\Users\<you>\.claude\skills\`.

### Codex

Codex reads skills from `~/.agents/skills/` (personal) and `.agents/skills/` (repository).
See the [Codex skills documentation](https://learn.chatgpt.com/docs/build-skills).

```bash
git clone https://github.com/GrowingRui/requirements-engineering-assistant.git ~/.agents/skills/requirements-engineering-assistant
```

### Cursor

Cursor reads skills from `~/.cursor/skills/` or `~/.agents/skills/` (personal) and
`.cursor/skills/` or `.agents/skills/` (project). It also loads skills from the Claude Code and
Codex folders above, so one install can serve several agents. See the
[Cursor skills documentation](https://cursor.com/docs/skills).

```bash
git clone https://github.com/GrowingRui/requirements-engineering-assistant.git ~/.cursor/skills/requirements-engineering-assistant
```

### Other agents

Point the agent at `SKILL.md` (paste it, or reference it from the agent's rules or instructions
file). The script runs anywhere with Python 3.

### Tested platforms

| Platform | Status |
|---|---|
| Claude Code | Tested (Windows 11, Python 3.12) |
| Codex | Not tested. Install paths taken from the official documentation (November 2026) |
| Cursor | Not tested. Install paths taken from the official documentation (November 2026) |

## Usage

Start a conversation in your agent and describe what you want to build. The skill is picked
up automatically when you ask for requirements; you can also name it, for example with
`/requirements-engineering-assistant` in Claude Code.

> I want an app where hobby rock collectors photograph a rock and the app tells them what it is.
> It should be fast and work offline in the mountains. Please write the requirements.

The agent will:

1. extract the requirements and show them, one line each;
2. list the problems it found, critical first;
3. ask 3–7 clarification questions, each with a suggested answer;
4. after your answers, update the requirements and repeat if important issues remain;
5. write user stories, acceptance criteria and quality judgements;
6. validate everything and export the document.

Say **"just analyse it"** or **"no questions"** for automatic mode, and **"enough"** at any time
to stop asking questions. The files are written to `requirements/` in the current project
unless you name another folder. The skill never edits your source code.

## Example

[examples/rock-identification/](examples/rock-identification/) is a complete run of the skill on
a deliberately messy description of a rock identification app:

| File | Content |
|---|---|
| [input.md](examples/rock-identification/input.md) | The informal description, with vague words, missing details, a contradiction and a duplicate |
| [clarifications.md](examples/rock-identification/clarifications.md) | What the agent found, the questions it asked and the answers |
| [requirements.json](examples/rock-identification/requirements.json) | The final data |
| [requirements.md](examples/rock-identification/requirements.md) | The generated requirements document |

The agent found the offline-versus-cloud-model conflict, the cost conflict, the duplicate, and the
missing photo limits and privacy rules. It turned "fast", "accurate" and "easy to use" into
measurable targets or open questions.

## Command-line tool

The agent runs the script for you, but you can also use it directly:

```bash
mkdir requirements
python scripts/rea.py init --name "My App" --out requirements/requirements.json
python scripts/rea.py scan idea.md
python scripts/rea.py validate requirements/requirements.json
python scripts/rea.py lint requirements/requirements.json
python scripts/rea.py export requirements/requirements.json
```

| Command | Purpose |
|---|---|
| `init` | Create an empty, valid `requirements.json` (`--mode automatic` for automatic mode) |
| `scan` | Flag vague words in a free-text description, with line numbers (`-` reads standard input) |
| `validate` | Check structure, IDs, references, dependency cycles and origin rules |
| `lint` | Validation, quality warnings and hints, and quality scores |
| `export` | Write `requirements.md` next to the JSON (`--out DIR` for another folder); refuses if the JSON is invalid |

Add `--json` to any command for machine-readable output.
Exit codes: `0` OK, `1` validation errors, `2` usage or file errors.

Sample `lint` output for the example:

```
examples/rock-identification/requirements.json: valid (0 errors, 1 warning, 0 hints)
  warning  [not_verifiable] requirement NFR-002: NFR-002 has no acceptance criterion and no fit criterion, so it cannot be verified.
Warnings and hints are candidates: confirm real problems as issues, dismiss the rest.
Quality: 88.5% (131/148 applicable points, 11 requirements)
Needs improvement:
  NFR-002    33%  clarity 0/2, completeness 0/2, unambiguity 1/2, verifiability 0/2, traceability 1/2
  FR-005     70%  clarity 1/2, completeness 0/2
  ...
```

(NFR-002, identification accuracy, stays weak on purpose: the user did not know a realistic
target, so the ambiguity is recorded as an accepted risk instead of an invented number.)

## Limitations

- The vague-word, duplicate and contradiction checks use word lists and text similarity, not
  real understanding. They produce false positives and miss things. The agent makes the final
  decision, and contradiction detection only catches simple negations; real conflicts are found
  by the agent.
- The quality score is a transparent guide, not an objective measurement or an industry
  certification.
- The result is only as good as the AI agent that runs the skill.
- Validation and export need Python 3.9+. Without Python the agent still writes both files by
  hand, but nothing is validated, and it says so.
- The vague-word list is English only.
- Tested with Claude Code only. Codex and Cursor support follows their documentation but has not
  been tried.

## Development

Run the tests (no installation needed):

```bash
python -m unittest discover -s tests
```

pytest also works if you have it. One test compares the JSON Schema against an external
validator and is skipped unless the optional `jsonschema` package is installed.

The tests cover the data model and its schema, every quality check, scoring, Markdown export, the
command-line tool, the consistency of `SKILL.md` and the references with the code, and the
complete example.

## Future work

- Export to CSV or to Jira / GitHub issues.
- Vague-word lists in more languages.
- Change history between clarification rounds.
- An optional evaluation suite for people who want to test the skill's behaviour with an API key.
- An optional HTML report.

## License

[MIT](LICENSE) © GrowingRui
