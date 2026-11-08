# Acceptance criteria

Each criterion is one scenario in Given/When/Then form, linked to one story (`story_id`) and to
the requirements it verifies (`requirement_ids`).

```json
{"id": "AC-004", "story_id": "US-002", "requirement_ids": ["FR-003"],
 "title": "Photo too large", "type": "negative",
 "given": ["the collector is on the identification screen"],
 "when": ["they select a 15 MB photo"],
 "then": ["the photo is not uploaded",
          "the message \"Photos must be 10 MB or smaller\" is shown"]}
```

## Steps

- `given`: the starting state. Concrete data, not "some rocks exist" but "the collection has 3 rocks".
- `when`: one user action or event. If you need several, the scenario may be two scenarios.
- `then`: observable outcomes a tester can check: what is shown, stored, sent, or refused.

Each list has at least one entry. Several entries are joined with "and".

## Types

| Type | Covers | Example |
|---|---|---|
| `positive` | The normal, successful path | Valid photo → identification shown |
| `negative` | Invalid input, missing permission, failure of a dependency | Wrong format, no network, not logged in |
| `boundary` | Values at and just past a limit | Exactly 10 MB accepted; 10.1 MB refused |

Aim for at least one positive scenario per story, plus negative and boundary scenarios wherever
the requirement has limits, permissions, input, or something that can fail.

## Make outcomes testable

`then` steps must not use vague words such as "quickly", "correctly", "user-friendly", "properly"
or "appropriate message". `rea.py lint` flags many of them (and weak phrases like "etc." in any
step) as `untestable_criterion`, but not all, so check the wording yourself.

| Instead of | Write |
|---|---|
| the result appears quickly | the result appears within 5 seconds |
| an appropriate error is shown | the message "No internet connection. Try again later." is shown |
| the rock is identified correctly | the top suggestion and its confidence (0–100%) are shown |
| it works on most phones | it works on Android 10+ and iOS 15+ |

If you do not know the number or the rule, do not invent it: raise or reuse an issue, write the
criterion with the open value marked (e.g. "within the agreed time limit (ISS-005)"), and keep the
requirement `needs_clarification`.

## Coverage

- Every story should have at least one criterion (`story_without_ac` otherwise).
- Every functional or non-functional requirement should be verified by a criterion or by a
  `fit_criterion` (`not_verifiable` otherwise).
- List in `requirement_ids` only requirements the scenario actually checks.
