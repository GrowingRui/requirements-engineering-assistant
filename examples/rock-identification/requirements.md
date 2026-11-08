# Rock Identification App: Requirements Specification

> Generated from `requirements.json` by the Requirements Engineering Assistant. Edit the JSON and export again instead of editing this file.

## 1. Project Overview

A phone app for hobby rock and mineral collectors. A collector photographs a rock, the app identifies it with a cloud AI model and shows how confident it is, and the collector keeps a personal collection of their finds on the phone. The app must be usable in the field without signal.

- **Mode:** interactive
- **Clarification rounds completed:** 1
- **Requirements:** 12 (7 functional, 5 non-functional)
- **Open issues:** 3 (0 critical)
- **User stories:** 3; **acceptance criteria:** 11

## 2. Scope

### In scope

- Rock and mineral identification from a photo
- Personal collection of finds, stored on the phone
- Use in the field without signal

### Out of scope

- User accounts and cloud sync (first release)
- Administrator tools for correcting rock descriptions (later release)

## 3. Stakeholders and User Roles

| ID | Name | Description | Permissions | Origin |
|---|---|---|---|---|
| SH-001 | Collector | Hobby rockhound aged 8 or older who photographs, identifies and collects rocks and minerals, often in the field without signal. | identify rocks from photos; save finds to their own collection; view their own collection | confirmed |
| SH-002 | Administrator | Maintains the rock descriptions. Planned for a later release. | correct rock descriptions | confirmed |

## 4. Business Requirements

*Not yet available.*

## 5. Functional Requirements

### FR-001: Identify a rock from a photo

A collector shall be able to take or choose a photo of a rock or mineral and receive the name of the rock or mineral that the identification ranks first.

- **Priority:** must · **Status:** approved · **Origin:** confirmed
- **Source:** user input, input.md line 5; clarification round 1
- **Stakeholders:** SH-001 (Collector)

### FR-002: Show identification confidence

The app shall show its confidence in each identification it gives.

- **Priority:** must · **Status:** approved · **Origin:** confirmed
- **Source:** user input, input.md line 7; clarification round 1
- **Depends on:** FR-001
- **Stakeholders:** SH-001 (Collector)

### FR-003: Save a find to the collection

A collector shall be able to save an identified rock to their collection with its photo, its name and, if location access is allowed, the place where it was found.

- **Priority:** must · **Status:** approved · **Origin:** confirmed
- **Source:** user input, input.md lines 9-10; clarification round 1
- **Depends on:** FR-001
- **Stakeholders:** SH-001 (Collector)

### FR-004: Save identified rocks to the collection

A collector shall be able to save identified rocks to their personal collection.

- **Priority:** unset · **Status:** rejected · **Origin:** confirmed
- **Source:** user input, input.md line 11
- **Rationale:** Duplicate of FR-003 (ISS-006).
- **Stakeholders:** SH-001 (Collector)

### FR-005: Correct rock descriptions

An administrator shall be able to correct wrong rock descriptions in the rock database.

- **Priority:** wont · **Status:** deferred · **Origin:** confirmed
- **Source:** user input, input.md line 18; clarification round 1
- **Rationale:** The user wants this in a later release.
- **Stakeholders:** SH-002 (Administrator)

### FR-006: Identify offline photos later

When a photo is taken without an internet connection, the app shall keep it and identify it automatically once a connection is available, without the collector taking the photo again.

- **Priority:** must · **Status:** approved · **Origin:** confirmed
- **Source:** clarification round 1
- **Rationale:** Settles the conflict between offline use and the cloud model (ISS-001).
- **Depends on:** FR-001
- **Stakeholders:** SH-001 (Collector)

### FR-007: Photo sources, formats and size

The app shall accept photos from the camera or the phone's gallery in JPEG, PNG or HEIC format of at most 20 MB, and refuse any other photo with a message that states the allowed formats and size.

- **Priority:** unset · **Status:** approved · **Origin:** confirmed
- **Source:** clarification round 1
- **Stakeholders:** SH-001 (Collector)

## 6. Non-Functional Requirements

### NFR-001: Offline use in the field

Taking photos and viewing the collection shall work without an internet connection.

- **Priority:** must · **Status:** approved · **Origin:** confirmed
- **Source:** user input, input.md lines 13-14; clarification round 1
- **Stakeholders:** SH-001 (Collector)

### NFR-002: Identification accuracy

Identification results shall be accurate.

- **Priority:** unset · **Status:** needs_clarification · **Origin:** confirmed
- **Source:** user input, input.md line 6
- **Rationale:** The user wants trustworthy results but does not know a realistic target (ISS-003).
- **Stakeholders:** SH-001 (Collector)

### NFR-003: Identification speed

The app shall show an identification result within 5 seconds of the photo being taken when a connection is available.

- **Priority:** must · **Status:** approved · **Origin:** confirmed
- **Source:** user input, input.md line 16; clarification round 1
- **Fit criterion:** 95% of identifications on a 4G connection show a result within 5 seconds of the photo being taken.
- **Stakeholders:** SH-001 (Collector)

### NFR-004: Usable by first-time collectors aged 8+

First-time collectors aged 8 or older shall be able to identify a rock and save it to their collection without help.

- **Priority:** must · **Status:** approved · **Origin:** confirmed
- **Source:** user input, input.md line 16; clarification round 1
- **Fit criterion:** In a usability test, at least 8 of 10 first-time users aged 8 or older identify a rock and save it to their collection without help within 2 minutes.
- **Stakeholders:** SH-001 (Collector)

### NFR-005: Find locations stay private

The app shall record a find location only after the collector allows location access, and shall never send find locations off the phone.

- **Priority:** unset · **Status:** approved · **Origin:** confirmed
- **Source:** clarification round 1
- **Stakeholders:** SH-001 (Collector)

## 7. Business Rules and Constraints

| ID | Kind | Statement | Origin | Source | Related |
|---|---|---|---|---|---|
| CON-001 | constraint | Identification uses an AI model that runs in the cloud. | confirmed | user input, input.md line 6 | FR-001, FR-006, NFR-002 |
| CON-002 | constraint | Hosting and AI service costs must not exceed 10 EUR per month. | confirmed | user input, input.md line 20; clarification round 1 | CON-001 |
| CON-003 | constraint | The collection is stored only on the phone; the first release has no user accounts. | confirmed | clarification round 1 | FR-003, NFR-005 |

## 8. Assumptions

| ID | Statement | Origin | Source | Related |
|---|---|---|---|---|
| ASM-001 | Collectors use a smartphone with a camera. | assumed (not confirmed) | - | FR-001 |
| ASM-002 | The app is a mobile app for Android and iOS. | assumed (not confirmed) | - | - |

## 9. Ambiguities and Open Questions

### Open

#### ISS-010: missing information (optional, open)

- **Affects:** FR-002
- **Description:** Nothing says what the app does when it is unsure about an identification.
- **Question:** What should the app show when its confidence is low?
- **Suggestion (not confirmed):** Below 60% confidence, show the top 3 candidates and say that the result is uncertain.

#### ISS-011: missing information (optional, open)

- **Affects:** NFR-004
- **Description:** Children may use the app, but no rules for young users are stated.
- **Question:** Are there extra rules for young users, such as parental consent before saving find locations?
- **Suggestion (not confirmed):** No extra rules in the first release, because there are no accounts and find locations never leave the phone.

#### ISS-012: missing information (optional, open)

- **Affects:** FR-003, CON-003
- **Description:** Because the collection is stored only on the phone (CON-003), it is lost if the phone is lost or replaced.
- **Missing information:** Whether collectors need a backup or export of their collection.
- **Question:** Should collectors be able to back up or export their collection?
- **Suggestion (not confirmed):** Not in the first release; consider an export of photos and a list of finds in a later release.

### Resolved or accepted

#### ISS-003: ambiguity (important, accepted risk)

- **Affects:** NFR-002
- **Description:** 'Accurate' has no measurable target, so nobody can test whether the identification is good enough.
- **Missing information:** An accuracy metric, a target value and the test set.
- **Question:** How often must the app name the right rock?
- **Suggestion (not confirmed):** The correct name is among the top 3 suggestions for at least 85% of photos in a test set of the 100 most common rocks and minerals.
- **Resolution:** The user does not know a realistic target and accepts the risk; the developers set it after testing candidate models.

#### ISS-004: ambiguity (important, resolved)

- **Affects:** NFR-003
- **Description:** 'Fast' had no time target.
- **Missing information:** A response-time target and the conditions it applies to.
- **Question:** What is the longest acceptable wait for an identification result: 2 s, 5 s or 10 s?
- **Suggestion (not confirmed):** 95% of identifications return a result within 5 seconds of taking the photo on a 4G connection.
- **Resolution:** Suggestion accepted: 95% of results within 5 seconds on 4G (NFR-003 fit criterion).

#### ISS-005: ambiguity (important, resolved)

- **Affects:** NFR-004
- **Description:** 'Easy to use, even for kids' named no task, age or success rate.
- **Missing information:** The user group (age), the task and a success rate.
- **Question:** From what age must children manage the app without help?
- **Suggestion (not confirmed):** In a usability test, at least 8 of 10 first-time users aged 10 or older identify a rock and save it to their collection without help within 2 minutes.
- **Resolution:** Suggestion accepted with the age changed to 8 or older (NFR-004 fit criterion).

#### ISS-007: missing information (important, resolved)

- **Affects:** FR-001
- **Description:** Photo sources, formats and size limits were not stated.
- **Missing information:** Allowed photo sources, file formats and maximum file size.
- **Question:** Which photos can be used, and how large may they be?
- **Suggestion (not confirmed):** Photos from the camera or the phone's gallery; JPEG, PNG or HEIC; at most 10 MB.
- **Resolution:** Camera or gallery; JPEG, PNG or HEIC; at most 20 MB (FR-007).

#### ISS-008: missing information (important, resolved)

- **Affects:** FR-003
- **Description:** FR-003 stores where a rock was found, which is personal location data, and it was not stated where the collection is kept (on the phone or in an online account).
- **Missing information:** Storage location of the collection, need for accounts, and privacy of find locations.
- **Question:** Where is the collection stored, and who may see the find locations?
- **Suggestion (not confirmed):** The collection is stored only on the phone, with no user account in the first release; a find location is saved only if the collector allows location access, and it never leaves the phone.
- **Resolution:** Suggestion accepted (CON-003, NFR-005).

#### ISS-009: missing information (optional, resolved)

- **Affects:** FR-005
- **Description:** The administrator role was mentioned as 'later maybe'; it was unclear whether it belongs to the first release.
- **Question:** Is the administrator part of the first release?
- **Suggestion (not confirmed):** No; the administrator is planned for a later release.
- **Resolution:** The user said the admin can wait for a later version; FR-005 deferred.

### Items not yet confirmed by the user

| ID | Kind | Item | Origin | Status |
|---|---|---|---|---|
| ASM-001 | assumption | Collectors use a smartphone with a camera. | assumed (not confirmed) | - |
| ASM-002 | assumption | The app is a mobile app for Android and iOS. | assumed (not confirmed) | - |

## 10. Conflict and Consistency Analysis

### Resolved or accepted

#### ISS-001: conflict (critical, resolved)

- **Affects:** NFR-001, CON-001
- **Description:** NFR-001 said the app works completely offline in the field, but CON-001 says identification runs on an AI model in the cloud, which needs an internet connection. Both cannot hold.
- **Question:** In the field without signal, which parts must still work?
- **Suggestion (not confirmed):** Taking photos and viewing the collection work offline; photos taken offline are identified automatically once the phone is back online.
- **Resolution:** Taking photos and viewing the collection work offline (NFR-001); offline photos are identified automatically later (FR-006).

#### ISS-002: conflict (important, resolved)

- **Affects:** CON-001, CON-002
- **Description:** A cloud AI model has running costs, but CON-002 said the owner does not want to pay for servers.
- **Question:** What is the most you are willing to pay per month for hosting and the AI service?
- **Suggestion (not confirmed):** Use a hosted AI service with a free tier and cap spending at 20 EUR per month.
- **Resolution:** Costs are capped at 10 EUR per month (CON-002).

#### ISS-006: duplicate (optional, resolved)

- **Affects:** FR-003, FR-004
- **Description:** FR-004 repeats FR-003 (input.md lines 9-11 say the same thing twice); FR-003 is the more detailed one.
- **Suggestion (not confirmed):** Keep FR-003 and reject FR-004.
- **Resolution:** FR-004 rejected and merged into FR-003; the user was told in round 1 and did not object.

## 11. User Stories

| ID | User story | Priority | Requirements | Notes |
|---|---|---|---|---|
| US-001 | As a Collector, I want to photograph a rock and see its name and how sure the app is, so that I can name my finds without asking an expert. | must | FR-001, FR-002, FR-007 | - |
| US-002 | As a Collector, I want to save a find with its photo, name and the place I found it, so that I remember what I found and where. | must | FR-003 | - |
| US-003 | As a Collector, I want to take photos in the field without signal and get them identified later, so that I never miss a find just because there is no signal. | must | FR-006 | Needs US-001 (identification) first. |

## 12. Acceptance Criteria

### US-001: photograph a rock and see its name and how sure the app is

#### AC-001: Identify a rock from a camera photo (positive)

*Requirements: FR-001, FR-002, NFR-003*

- **Given** the phone has a 4G connection
- **And** the collector has the camera open in the app
- **When** they take a photo of a piece of quartz
- **Then** a rock or mineral name is shown within 5 seconds
- **And** a confidence value from 0% to 100% is shown next to the name

#### AC-002: Identify a rock from a gallery photo (positive)

*Requirements: FR-001, FR-007*

- **Given** the phone's gallery contains a 4 MB JPEG photo of a rock
- **And** the phone has an internet connection
- **When** the collector chooses that photo in the app
- **Then** the photo is accepted
- **And** a rock or mineral name and its confidence are shown

#### AC-003: Photo of exactly 20 MB is accepted (boundary)

*Requirements: FR-007*

- **Given** the gallery contains a HEIC photo of exactly 20 MB
- **When** the collector chooses that photo
- **Then** the photo is accepted for identification

#### AC-004: Photo larger than 20 MB is refused (boundary)

*Requirements: FR-007*

- **Given** the gallery contains a JPEG photo of 20.1 MB
- **When** the collector chooses that photo
- **Then** the photo is not sent for identification
- **And** the message "Photos must be JPEG, PNG or HEIC and 20 MB or smaller." is shown

#### AC-005: Unsupported format is refused (negative)

*Requirements: FR-007*

- **Given** the gallery contains a 2 MB GIF image
- **When** the collector chooses that image
- **Then** the image is not sent for identification
- **And** the message "Photos must be JPEG, PNG or HEIC and 20 MB or smaller." is shown

#### AC-008: No location is sent for identification (negative)

*Requirements: NFR-005*

- **Given** the collector has allowed location access
- **And** the camera stores GPS coordinates in its photos
- **When** a photo is sent to the AI service for identification
- **Then** the data sent contains no GPS coordinates or other location

### US-002: save a find with its photo, name and the place I found it

#### AC-006: Save a find with its location (positive)

*Requirements: FR-003, NFR-005*

- **Given** a rock has been identified as quartz
- **And** the collector has allowed location access
- **When** they save the find
- **Then** the collection contains a new entry with the photo, the name "quartz" and the current location

#### AC-007: Save a find without location access (negative)

*Requirements: FR-003, NFR-005*

- **Given** a rock has been identified as quartz
- **And** the collector has refused location access
- **When** they save the find
- **Then** the collection contains a new entry with the photo and the name "quartz"
- **And** the entry has no location

### US-003: take photos in the field without signal and get them identified later

#### AC-009: Take a photo and browse the collection without signal (positive)

*Requirements: FR-006, NFR-001*

- **Given** the phone has no internet connection
- **And** the collection contains 3 saved finds
- **When** the collector takes a photo of a rock
- **And** then opens the collection
- **Then** the new photo is kept and marked "waiting for identification"
- **And** all 3 saved finds are shown with their photos and names

#### AC-010: Waiting photo is identified when the connection returns (positive)

*Requirements: FR-006*

- **Given** one photo is marked "waiting for identification"
- **When** the phone gets an internet connection
- **Then** the photo is identified without the collector taking it again
- **And** its name and confidence are shown and the "waiting for identification" mark is removed

#### AC-011: Connection lost during identification (negative)

*Requirements: FR-006*

- **Given** a waiting photo is being sent for identification
- **When** the internet connection drops before a result arrives
- **Then** the photo stays marked "waiting for identification"
- **And** it is sent again the next time a connection is available

## 13. Requirements Quality Assessment

Each characteristic is scored 0 (poor), 1 (partial) or 2 (good); *n/a* means not applicable and *?* means not assessed yet. Neither counts against the requirement. Unambiguity, verifiability, consistency and traceability are computed by the script; clarity, completeness and feasibility are judged by the AI agent, with a reason. The score is a guide, not a certification. Rejected requirements are not scored.

**Overall: 89%** (131 of 148 applicable points)

| Requirement | Clarity | Completeness | Consistency | Unambiguity | Verifiability | Feasibility | Traceability | Score |
|---|---|---|---|---|---|---|---|---|
| FR-001 | 2 | 2 | 2 | 2 | 2 | 1 | 2 | 93% |
| FR-002 | 2 | 1 | 2 | 2 | 2 | 2 | 2 | 93% |
| FR-003 | 2 | 1 | 2 | 2 | 2 | 2 | 2 | 93% |
| FR-005 | 1 | 0 | 2 | 2 | n/a | n/a | 2 | 70% |
| FR-006 | 2 | 1 | 2 | 2 | 2 | 2 | 2 | 93% |
| FR-007 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 100% |
| NFR-001 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 100% |
| NFR-002 | 0 | 0 | 2 | 1 | 0 | n/a | 1 | 33% |
| NFR-003 | 2 | 2 | 2 | 2 | 2 | 1 | 2 | 93% |
| NFR-004 | 2 | 2 | 2 | 2 | 2 | 2 | 1 | 93% |
| NFR-005 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 100% |

### Requirements needing improvement

- **NFR-002** (33%): clarity 0 ("Accurate" has no metric, so it can be read in many ways); completeness 0 (No target or test set; the user accepted leaving it open (ISS-003)); unambiguity 1 (Uses 'accurate'; tracked as ambiguity issue ISS-003); verifiability 0 (No acceptance criterion, fit criterion or user story); traceability 1 (Has a source but is not linked to any parent, child, story or criterion)
- **FR-005** (70%): clarity 1 ("Wrong rock descriptions" does not say who decides what is wrong); completeness 0 (Deferred: where the descriptions come from and how corrections reach the app are not defined)
- **FR-001** (93%): feasibility 1 (Depends on finding a cloud AI service that identifies rocks within the 10 EUR monthly budget (CON-002))
- **FR-002** (93%): completeness 1 (Behaviour for low-confidence results is still open (ISS-010))
- **FR-003** (93%): completeness 1 (Backup or export of the collection is still open (ISS-012))
- **FR-006** (93%): completeness 1 (No limit is set on how many waiting photos may be kept)
- **NFR-003** (93%): feasibility 1 (Upload of photos up to 20 MB over 4G within 5 seconds may require resizing before upload)
- **NFR-004** (93%): traceability 1 (Has a source but is not linked to any parent, child, story or criterion)

### Score reasons

#### FR-001

- **Clarity** (judged, 2): One actor, one action and one result.
- **Completeness** (judged, 2): Photo sources and limits are settled in FR-007.
- **Consistency** (computed, 2): No open conflict, duplicate, overlap or terminology issue.
- **Unambiguity** (computed, 2): No vague words found.
- **Verifiability** (computed, 2): Has acceptance criteria: AC-001, AC-002.
- **Feasibility** (judged, 1): Depends on finding a cloud AI service that identifies rocks within the 10 EUR monthly budget (CON-002).
- **Traceability** (computed, 2): Has a source and is linked to US-001, AC-001, AC-002.

#### FR-002

- **Clarity** (judged, 2): Clear what must be shown and when.
- **Completeness** (judged, 1): Behaviour for low-confidence results is still open (ISS-010).
- **Consistency** (computed, 2): No open conflict, duplicate, overlap or terminology issue.
- **Unambiguity** (computed, 2): No vague words found.
- **Verifiability** (computed, 2): Has acceptance criteria: AC-001.
- **Feasibility** (judged, 2): Identification models return a confidence value with each result.
- **Traceability** (computed, 2): Has a source and is linked to US-001, AC-001.

#### FR-003

- **Clarity** (judged, 2): Saved fields and the location condition are stated.
- **Completeness** (judged, 1): Backup or export of the collection is still open (ISS-012).
- **Consistency** (computed, 2): No open conflict, duplicate, overlap or terminology issue.
- **Unambiguity** (computed, 2): No vague words found.
- **Verifiability** (computed, 2): Has acceptance criteria: AC-006, AC-007.
- **Feasibility** (judged, 2): Local storage of photos and a few fields is standard on phones.
- **Traceability** (computed, 2): Has a source and is linked to US-002, AC-006, AC-007.

#### FR-005

- **Clarity** (judged, 1): "Wrong rock descriptions" does not say who decides what is wrong.
- **Completeness** (judged, 0): Deferred: where the descriptions come from and how corrections reach the app are not defined.
- **Consistency** (computed, 2): No open conflict, duplicate, overlap or terminology issue.
- **Unambiguity** (computed, 2): No vague words found.
- **Verifiability** (computed, n/a): Not applicable while deferred.
- **Feasibility** (judged, n/a): No basis to judge until the source of the rock descriptions is known.
- **Traceability** (computed, 2): Has a source; links are not expected while deferred.

#### FR-006

- **Clarity** (judged, 2): Trigger, action and the no-retake condition are explicit.
- **Completeness** (judged, 1): No limit is set on how many waiting photos may be kept.
- **Consistency** (computed, 2): No open conflict, duplicate, overlap or terminology issue.
- **Unambiguity** (computed, 2): No vague words found.
- **Verifiability** (computed, 2): Has acceptance criteria: AC-009, AC-010, AC-011.
- **Feasibility** (judged, 2): A local queue with retry on reconnect is a common mobile pattern.
- **Traceability** (computed, 2): Has a source and is linked to US-003, AC-009, AC-010, AC-011.

#### FR-007

- **Clarity** (judged, 2): Sources, formats, size and refusal behaviour are listed.
- **Completeness** (judged, 2): Covers accepted and refused photos.
- **Consistency** (computed, 2): No open conflict, duplicate, overlap or terminology issue.
- **Unambiguity** (computed, 2): No vague words found.
- **Verifiability** (computed, 2): Has acceptance criteria: AC-002, AC-003, AC-004, AC-005.
- **Feasibility** (judged, 2): Format and size checks are simple to implement.
- **Traceability** (computed, 2): Has a source and is linked to US-001, AC-002, AC-003, AC-004, AC-005.

#### NFR-001

- **Clarity** (judged, 2): Names exactly which functions work offline.
- **Completeness** (judged, 2): Offline identification is handled by FR-006.
- **Consistency** (computed, 2): No open conflict, duplicate, overlap or terminology issue.
- **Unambiguity** (computed, 2): No vague words found.
- **Verifiability** (computed, 2): Has acceptance criteria: AC-009.
- **Feasibility** (judged, 2): Camera and local storage need no connection.
- **Traceability** (computed, 2): Has a source and is linked to AC-009.

#### NFR-002

- **Clarity** (judged, 0): "Accurate" has no metric, so it can be read in many ways.
- **Completeness** (judged, 0): No target or test set; the user accepted leaving it open (ISS-003).
- **Consistency** (computed, 2): No open conflict, duplicate, overlap or terminology issue.
- **Unambiguity** (computed, 1): Uses 'accurate'; tracked as ambiguity issue ISS-003.
- **Verifiability** (computed, 0): No acceptance criterion, fit criterion or user story.
- **Feasibility** (judged, n/a): Cannot be judged without a target.
- **Traceability** (computed, 1): Has a source but is not linked to any parent, child, story or criterion.

#### NFR-003

- **Clarity** (judged, 2): Time limit and condition are stated.
- **Completeness** (judged, 2): Fit criterion gives percentile, time and network type.
- **Consistency** (computed, 2): No open conflict, duplicate, overlap or terminology issue.
- **Unambiguity** (computed, 2): No vague words found.
- **Verifiability** (computed, 2): Has acceptance criteria (AC-001) and a fit criterion.
- **Feasibility** (judged, 1): Upload of photos up to 20 MB over 4G within 5 seconds may require resizing before upload.
- **Traceability** (computed, 2): Has a source and is linked to AC-001.

#### NFR-004

- **Clarity** (judged, 2): User group, task and condition are stated.
- **Completeness** (judged, 2): Fit criterion gives sample size, success rate and time limit.
- **Consistency** (computed, 2): No open conflict, duplicate, overlap or terminology issue.
- **Unambiguity** (computed, 2): No vague words found.
- **Verifiability** (computed, 2): Has a fit criterion.
- **Feasibility** (judged, 2): A two-step task is achievable with a simple interface.
- **Traceability** (computed, 1): Has a source but is not linked to any parent, child, story or criterion.

#### NFR-005

- **Clarity** (judged, 2): Two clear conditions on recording and sending location.
- **Completeness** (judged, 2): Covers consent and data leaving the phone, including photo metadata (AC-008).
- **Consistency** (computed, 2): No open conflict, duplicate, overlap or terminology issue.
- **Unambiguity** (computed, 2): No vague words found.
- **Verifiability** (computed, 2): Has acceptance criteria: AC-006, AC-007, AC-008.
- **Feasibility** (judged, 2): Location permission and removing GPS data from photos are standard.
- **Traceability** (computed, 2): Has a source and is linked to AC-006, AC-007, AC-008.

## 14. Requirements Traceability Matrix

Only links recorded in `requirements.json` are shown.

| Requirement | Status | Derived from | Refined by | Depends on | User stories | Acceptance criteria | Open issues | Gaps |
|---|---|---|---|---|---|---|---|---|
| FR-001 | approved | - | - | - | US-001 | AC-001, AC-002 | - | - |
| FR-002 | approved | - | - | FR-001 | US-001 | AC-001 | ISS-010 | - |
| FR-003 | approved | - | - | FR-001 | US-002 | AC-006, AC-007 | ISS-012 | - |
| FR-004 | rejected | - | - | - | - | - | - | - |
| FR-005 | deferred | - | - | - | - | - | - | - |
| FR-006 | approved | - | - | FR-001 | US-003 | AC-009, AC-010, AC-011 | - | - |
| FR-007 | approved | - | - | - | US-001 | AC-002, AC-003, AC-004, AC-005 | - | - |
| NFR-001 | approved | - | - | - | - | AC-009 | - | - |
| NFR-002 | needs_clarification | - | - | - | - | - | - | not verifiable |
| NFR-003 | approved | - | - | - | - | AC-001 | - | - |
| NFR-004 | approved | - | - | - | - | - | ISS-011 | - |
| NFR-005 | approved | - | - | - | - | AC-006, AC-007, AC-008 | - | - |
