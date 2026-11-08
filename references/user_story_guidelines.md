# User stories

## Format

`As a <role>, I want <goal>, so that <benefit>.`

In the JSON this is split into `role`, `goal` and `benefit`:

```json
{"id": "US-003", "role": "Collector", "goal": "photograph a rock and get its likely identity",
 "benefit": "I learn what I found without an expert", "requirement_ids": ["FR-001", "FR-002"],
 "priority": "must"}
```

- `role`: a stakeholder name from `stakeholders` where possible. Avoid "user" when a more
  specific role exists.
- `goal`: what they do, in their words, without UI details ("get its likely identity", not
  "tap the blue button").
- `benefit`: the real reason. If you can only write "so that I can do it", the story may not be
  needed, or the benefit belongs to another role.
- `priority`: normally the highest priority among its requirements.

## Which stories to write

- Every `functional` and `user` requirement that is not `deferred` or `rejected` should be
  covered by at least one story.
- One story may cover several closely related requirements; one requirement may appear in
  several stories.
- Non-functional requirements usually need no own story. Verify them with a `fit_criterion`, or
  with acceptance criteria on the stories they affect.
- Do not write stories for `rejected` requirements.
- Base stories only on what is in `requirements`. If a story needs behaviour no requirement
  describes, add the requirement first (origin `assumed` or `suggested`).

## INVEST check

| Letter | Question | If not |
|---|---|---|
| Independent | Can it be built without another story being done first? | Note the order in `description`, or merge |
| Negotiable | Does it describe the need, not a fixed design? | Remove UI and technology details |
| Valuable | Does the role get something useful? | Reword the benefit or merge into another story |
| Estimable | Does the team know enough to size it? | Raise an issue for what is missing |
| Small | Can it be done in a few days? | Split it (below) |
| Testable | Can you write acceptance criteria? | Clarify the goal; raise an ambiguity issue |

## Splitting large stories

Split along one of these lines, keeping each part valuable:
- by workflow step (capture photo / see result / save to collection);
- by business rule or variation (free user / premium user);
- by data type or input (photo from camera / from gallery);
- by happy path vs. error handling;
- by operation (create / view / edit / delete).

Avoid splitting by technical layer (database story, API story, UI story).
