# Clarification questions

## Choosing questions

Each round asks **3 to 7 questions**. Fewer if fewer matter; never more.

Pick in this order:
1. Open `critical` issues (conflicts first, then missing core information).
2. Open `important` issues that affect several requirements.
3. Open `important` issues that affect one requirement.
4. `optional` issues only if there is room and they are quick to answer.

Skip a question when:
- the user already answered it (re-read the description and earlier rounds);
- a safe default exists and getting it wrong is cheap: record it as `assumed` instead and
  mention it in the round summary;
- it is a design or implementation choice the team can make later.

## Grouping

Put related questions together under a short heading (for example "Photos", "Accounts",
"Offline use"). A question that settles several issues counts once.

## Phrasing

Each question:
- is about one thing and can be answered in a sentence;
- names the requirement or issue it settles (`FR-003`, `ISS-002`);
- offers a **suggested answer** the user can accept with "yes" or "ok";
- offers concrete options when the space is small ("A, B or C?").

Avoid questions that only ask for confirmation of something vague ("Should it be fast?").
Ask for the number or the rule ("What is the longest acceptable wait for a result: 2 s, 5 s, 10 s?").

## Round format

```
Round 1: 5 questions (2 critical, 3 important)

Offline use
1. [ISS-001, critical] FR-004 says identification works offline, but NFR-002 needs a cloud model.
   Which should win?
   Suggested: identification needs internet; the collection is viewable offline.

Photos
2. [ISS-003, important] What is the largest photo users can upload, and which formats?
   Suggested: up to 10 MB, JPEG, PNG or HEIC.
...

Reply with answers, "ok" to accept all suggestions, or "enough" to stop asking.
```

Before the questions, show one line per requirement found and the issue counts by severity.

## Applying the answers

`N` below is `project.clarification_round`, which you increased when you asked the round.

For every answered question:
- the issue: `status: "resolved"` and `resolution` with the answer in one sentence;
- the affected requirements and rules: update the text or `fit_criterion`, set
  `origin: "confirmed"` and `source: "clarification round N"`;
- new facts become new items with `origin: "confirmed"` and the same source;
- "ok" to a suggestion counts as confirmation of that suggestion only.

If the user declines or does not know:
- keep the issue `open`, or set `accepted_risk` with a `resolution` such as
  "User accepts the risk; decide during design.";
- keep the item `assumed` or `open`.

Run `rea.py lint` afterwards: answers often create new requirements that need review.

## When to stop

Stop asking when any of these is true:
- no open `critical` or `important` issues remain;
- the user says "enough", "continue", "just write it" or similar;
- the last round produced no new information.

Everything still open is listed under "Ambiguities and Open Questions" in the exported document.
