# Requirements quality: reviewing findings and scoring

## 1. Reviewing lint candidates

`rea.py lint` reports warnings and hints. They come from word lists and text similarity, so
some are false alarms and some real problems are missed. For each finding:

1. Read the requirements it names.
2. Decide: **real problem** → record an issue; **false alarm** → ignore it (or reword so it no
   longer triggers, if the wording really is loose); **already covered** → nothing to do.
3. Then look for what the script cannot see (section 3).

| Code | Level | What to do if it is real |
|---|---|---|
| `ambiguous_term` | warning | Add a `fit_criterion` if you know the target; otherwise an `ambiguity` issue with a question. "at most 10 MB" style bounds are not vague. |
| `untestable_criterion` | warning | Rewrite the Given/When/Then step with an observable, measurable outcome. |
| `possible_duplicate` | warning | `duplicate` issue listing both IDs; suggest which one to keep. |
| `possible_contradiction` | warning | `conflict` issue if both cannot be true at once. A requirement and its explicit exception are not a conflict. |
| `possible_overlap` | hint | `overlap` issue only if the boundary between them is unclear. |
| `no_user_story` | warning | Write a story (step 8), or leave it if stories come later. |
| `not_verifiable` | warning | Add acceptance criteria or a `fit_criterion`. |
| `business_requirement_not_refined` | hint | Derive user/functional requirements from it, or raise `missing_information`. |
| `story_without_ac` | warning | Write acceptance criteria for the story. |
| `only_positive_ac` | hint | Add negative or boundary scenarios where failure is possible. |
| `approved_with_critical_issue` | warning | Resolve the issue, or set the requirement back to `needs_clarification`. |
| `possibly_missing` | hint | A topic (upload limits, privacy, offline use, ...) seems uncovered. Raise `missing_information` if it matters for this project; otherwise add it to `scope_out`. |
| `no_nfr` | hint | Ask about performance, security, usability, availability; suggest NFRs with origin `suggested`. |
| `roles_without_permissions` | hint | Ask what each role may and may not do; fill `permissions`. |

How the script treats recorded issues:
- An open or `accepted_risk` `ambiguity` issue on a requirement silences `ambiguous_term` for it.
  A **resolved** one does not: after the answer, reword the requirement or add a fit criterion.
- Any issue that names two requirements together silences the duplicate, contradiction and
  overlap candidates for that pair.

## 2. Issue severity

| Severity | Use when | Examples |
|---|---|---|
| `critical` | Cannot design or build correctly without the answer; or two requirements cannot both hold | Offline use vs. cloud-only model; who owns the data; unknown core user role |
| `important` | Can start, but the answer changes scope, cost or tests | Upload size limit, response-time target, retention period |
| `optional` | Nice to settle; a sensible default exists | Wording consistency, sort order, minor UI preferences |

## 3. Problems only you can find

- **Real conflicts** without negation words: "data stays on the device" vs. "share collections
  with friends".
- **Terminology:** the same thing under two names ("specimen", "sample", "rock"), or one word with
  two meanings. Record as `terminology`.
- **Missing actors or flows:** who creates accounts, who moderates content, what happens on error.
- **Hidden dependencies:** a feature that silently needs another one (sharing needs accounts).
  Record as `dependency` and add `depends_on`.
- **Compound requirements:** split "and"/"or" statements that could be delivered separately.
- **Solutions disguised as requirements:** "use Firebase" is a constraint only if the user
  insists; otherwise ask for the underlying need.

## 4. Quality scores

Each requirement (except `rejected`) gets 0–2 per characteristic. `null` means not applicable
and does not count. The overall percentage is points over applicable points. It is a guide, not
a certification.

### Judged by you (in `quality_assessments`, reason required)

| Characteristic | 2 | 1 | 0 |
|---|---|---|---|
| `clarity` | One reading only; clear actor, action and object; plain words | Understandable but loose wording, or two ideas in one statement | Unclear what is required or who does it |
| `completeness` | Conditions, limits and error cases that matter are stated | Some details still open (link the issue in the reason) | Key information missing; cannot be built as written |
| `feasibility` | Clearly achievable with ordinary technology and the stated constraints | Achievable with notable risk, cost or an unknown (name it) | Not achievable as stated, or contradicts a constraint |

Use `null` for feasibility when you have no basis to judge (e.g. an unknown external system), and
say so in the reason. Reasons are one sentence and specific: "Upload size limit still open
(ISS-004)", not "Could be more complete".

### Computed by the script (do not write these)

| Characteristic | 2 | 1 | 0 |
|---|---|---|---|
| Unambiguity | No vague words, or a fit criterion defines the target | Vague words, tracked in an unresolved ambiguity issue | Vague words, untracked |
| Verifiability | Has acceptance criteria or a fit criterion | Has a story but no criteria | Nothing. Business requirements: not applicable |
| Consistency | No open consistency issue | In an open conflict, duplicate, overlap or terminology issue | In an open **critical** conflict or duplicate |
| Traceability | Has a source and is linked up or down (parent, child, story, criterion) | Has a source only | No source |

`rea.py lint` prints the overall percentage, the requirements needing improvement, and the
requirements you have not scored yet.
