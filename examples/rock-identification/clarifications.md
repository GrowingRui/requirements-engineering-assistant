# Clarification log: Rock Identification App

This log shows how the agent followed `SKILL.md` on [input.md](input.md) in interactive mode.
The project is a made-up example, so the answers in round 1 were written for the demonstration.
They are typical of what a non-technical project owner might say: some answers accept
the suggestion, some change it, one is "I don't know", and one adds information nobody
asked for.

## Step 1: Scan the description

`python scripts/rea.py scan examples/rock-identification/input.md`

```
input.md: 4 vague words or weak phrases found
  line 6, col 67: 'accurate' (vague) - an accuracy metric and target (e.g. top-1 accuracy on a defined test set)
  line 16, col 12: 'fast' (vague) - a measurable time target (e.g. response time at a percentile, under a stated load)
  line 16, col 21: 'easy to use' (vague) - a usability target (task, user group, success rate, time on task)
  line 20, col 33: 'if possible' (weak) - makes the requirement optional; state the condition or priority
```

## Steps 2–3: Extract, lint and review

The first extraction contained 5 functional and 4 non-functional requirements, 2 roles,
2 constraints and 2 assumptions. All were taken from the text. Nothing was invented: the
administrator and the admin requirement (FR-005) are `open`, because the description only
says "later maybe".

`rea.py lint` reported 18 warnings and 4 hints. Review:

| Lint finding | Decision |
|---|---|
| `ambiguous_term` NFR-002 "accurate", NFR-003 "fast", NFR-004 "easy to use" | Real. Recorded as ambiguity issues ISS-003, ISS-004, ISS-005 |
| `ambiguous_term` FR-001 "most" (in "most likely identification") | False alarm: "most likely" means the top-ranked result. Reworded after round 1 |
| `possibly_missing` file and image limits (FR-001, FR-003) | Real. ISS-007 |
| `possibly_missing` personal data and privacy (FR-004) | Real: FR-003 stores where a rock was found. ISS-008 |
| `possibly_missing` data storage (FR-003, FR-004) | Real: covered by ISS-008. After round 1 it led to ISS-012 (backup) |
| `possibly_missing` user roles and permissions (FR-005) | Real, but optional: ISS-009 (is the administrator in the first release?) |
| `no_user_story`, `not_verifiable` (all requirements) | Expected at this point. Stories and criteria come in step 8 |

Problems the script did not report, found by the agent:

| Problem | Issue |
|---|---|
| **Offline vs. cloud:** NFR-001 "works completely offline" vs. CON-001 "AI model in the cloud" | ISS-001, critical conflict |
| **Cost:** a cloud AI model costs money vs. CON-002 "don't want to pay for servers" | ISS-002, important conflict |
| **Duplicate:** FR-004 repeats FR-003 (input.md lines 9–11). The word overlap is only 35% because FR-003 has more detail, so the similarity check missed it | ISS-006, optional duplicate |
| Nothing says what happens when the app is unsure | ISS-010, optional |
| Children may use the app; no rules for young users | ISS-011, optional |

## Round 1: what the user saw

```
Requirements found (9):
  FR-001  Identify a rock from a photo
  FR-002  Show identification confidence
  FR-003  Save a find to the collection
  FR-004  Save identified rocks to the collection   (same as FR-003, see below)
  FR-005  Correct rock descriptions (administrator, "later maybe")
  NFR-001 Offline use in the field
  NFR-002 Identification accuracy
  NFR-003 Speed
  NFR-004 Ease of use
Issues: 1 critical, 6 important, 4 optional

Round 1: 7 questions (1 critical, 6 important)

Offline use and costs
1. [ISS-001, critical] NFR-001 says the app works completely offline, but CON-001 says
   identification uses an AI model in the cloud, which needs internet.
   In the field without signal, which parts must still work?
   Suggested: taking photos and viewing the collection work offline; photos taken offline
   are identified automatically once the phone is back online.
2. [ISS-002, important] A cloud AI model costs money every month (CON-001, CON-002).
   What is the most you are willing to pay per month for hosting and the AI service?
   Suggested: use a service with a free tier and cap spending at 20 EUR per month.

Collection and privacy
3. [ISS-008, important] FR-003 stores where each rock was found. Where is the collection
   stored, and who may see the find locations?
   Suggested: only on the phone, no user account in the first release; a find location is
   saved only if the collector allows location access, and it never leaves the phone.

Photos
4. [ISS-007, important] Which photos can be used (FR-001), and how large may they be?
   Suggested: from the camera or the gallery; JPEG, PNG or HEIC; at most 10 MB.

Measurable targets
5. [ISS-003, important] NFR-002 "accurate": how often must the app name the right rock?
   Suggested: the correct name is among the top 3 suggestions for at least 85% of photos
   in a test set of the 100 most common rocks and minerals.
6. [ISS-004, important] NFR-003 "fast": what is the longest acceptable wait for a result:
   2 s, 5 s or 10 s?
   Suggested: 95% of results within 5 seconds of taking the photo, on a 4G connection.
7. [ISS-005, important] NFR-004 "easy to use, even for kids": from what age must children
   manage the app without help?
   Suggested: at least 8 of 10 first-time users aged 10 or older identify and save a rock
   without help within 2 minutes.

Not asked:
- FR-004 says the same as FR-003, so I merged it into FR-003 (ISS-006).
- Assumed, tell me if wrong: collectors have a smartphone with a camera (ASM-001);
  the app is for Android and iOS (ASM-002).
- Left open for later: the administrator (ISS-009), what to show when the app is unsure
  (ISS-010), and rules for young users (ISS-011).

Reply with answers, "ok" to accept all suggestions, or "enough" to stop asking.
```

## Round 1: example answers

> 1. Yes, like that. I just don't want to take the photo again.
> 2. 10 EUR a month at most.
> 3. ok
> 4. ok, but allow up to 20 MB. New phones take big photos.
> 5. No idea what's realistic. Let whoever builds it decide after testing.
> 6. ok
> 7. Make it 8 and up. My nephew is 8.
>
> The must-haves are identifying, showing how sure it is, saving, and offline.
> The admin can wait for a later version.

## Applying the answers

| Answer | Change in `requirements.json` | Issue |
|---|---|---|
| 1 | NFR-001 reworded: taking photos and viewing the collection work without internet. New FR-006: photos taken offline are identified automatically later | ISS-001 resolved |
| 2 | CON-002 now says costs must not exceed 10 EUR per month | ISS-002 resolved |
| 3 | New CON-003 (collection only on the phone, no accounts) and NFR-005 (location only with permission, never leaves the phone). FR-003 updated. "User accounts and cloud sync" added to `scope_out` | ISS-008 resolved |
| 4 | New FR-007: camera or gallery; JPEG, PNG or HEIC; at most 20 MB (the user changed the suggested 10 MB) | ISS-007 resolved |
| 5 | NFR-002 unchanged and still unmeasurable; status `needs_clarification` | ISS-003 `accepted_risk` |
| 6 | NFR-003 gets a fit criterion: 95% within 5 s on 4G | ISS-004 resolved |
| 7 | NFR-004 gets a fit criterion with age 8 or older (the user changed the suggested age) | ISS-005 resolved |
| Extra | Priority `must` for FR-001, FR-002, FR-003, NFR-001. FR-005 and the administrator confirmed for a later release: FR-005 `deferred`, priority `wont` | ISS-009 resolved |
| Merge | FR-004 `rejected` as a duplicate of FR-003. The user saw this and did not object | ISS-006 resolved |

Every changed or new item is `confirmed` with source `clarification round 1`. The
assumptions ASM-001 and ASM-002 stay `assumed`: the user did not comment on them, and
silence is not confirmation.

Other priorities:
- NFR-003 and NFR-004 are `must` because input.md line 16 says "It must be fast and easy to use".
- NFR-002, NFR-005 and FR-007 stay `unset`, because the user gave no priority for them.

A new problem came from answer 3: a collection kept only on the phone is lost if the phone
is lost. This was recorded as ISS-012 (optional, open).

## Why the agent stopped after one round

No critical or important issues are still open. The remaining open issues are optional
(ISS-010, ISS-011, ISS-012). The document lists them under "Ambiguities and Open Questions".
The agent then wrote user stories, acceptance criteria and quality judgements (step 8), ran
`validate`, `lint` and `export` (step 9), and produced [requirements.md](requirements.md).
