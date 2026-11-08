"""Tests for reqkit.checks: vague words, similarity, lint findings.

Scenarios from PLAN.md section 10: 1 (clean), 2 (ambiguous), 3 (missing
information), 4 (contradiction), 5 (duplicate), 6 (multiple roles),
7 (non-functional). Each scenario has a fixture tests/fixtures/lint_*.json.
"""

import glob
import os
import unittest

from support import FIXTURES_DIR, codes, load_fixture

from reqkit import checks
from reqkit.checks import find_terms, lint, scan_text, similarity
from reqkit.model import validate


def found(findings, code, ids=None):
    """True if a finding with this code (and exactly these ids, if given) exists."""
    return any(f.code == code and (ids is None or tuple(f.ids) == tuple(ids)) for f in findings)


def topics(findings):
    return [f.message for f in findings if f.code == "possibly_missing"]


def req(doc, rid):
    return next(r for r in doc["requirements"] if r["id"] == rid)


class FixturesAreValidTest(unittest.TestCase):
    def test_lint_fixtures_pass_structural_validation(self):
        paths = sorted(glob.glob(os.path.join(FIXTURES_DIR, "lint_*.json")))
        self.assertGreaterEqual(len(paths), 6)
        for path in paths:
            name = os.path.basename(path)
            self.assertEqual(validate(load_fixture(name)), [], name)


class TermScannerTest(unittest.TestCase):
    def test_finds_vague_and_weak_terms(self):
        terms = {(t.term, t.kind) for t in find_terms("It must be FAST, secure, etc. and/or cheap.")}
        self.assertEqual(terms, {("fast", "vague"), ("secure", "vague"), ("etc", "weak"), ("and/or", "weak")})

    def test_whole_words_only(self):
        self.assertEqual(find_terms("Breakfast is served steadfastly to fewer people."), [])

    def test_longest_phrase_wins(self):
        self.assertEqual([t.term for t in find_terms("The app is easy to use.")], ["easy to use"])

    def test_common_words_are_not_flagged(self):
        self.assertEqual(find_terms("Show the available rooms."), [])

    def test_scan_text_reports_line_and_column(self):
        results = scan_text("First line is fine.\nThe app should be fast.")
        self.assertEqual(len(results), 1)
        hit = results[0]
        self.assertEqual((hit["line"], hit["column"], hit["term"]), (2, 19, "fast"))
        self.assertEqual(hit["context"], "The app should be fast.")
        self.assertIn("time", hit["missing"])


class KeywordMatchTest(unittest.TestCase):
    def test_whole_word_with_inflections(self):
        self.assertTrue(checks._contains_any("Photos are uploaded nightly.", ["upload"]))
        self.assertTrue(checks._contains_any("Users log in first.", ["log in"]))

    def test_no_match_inside_other_words(self):
        self.assertFalse(checks._contains_any("Keep the aisle clear and maintain it.", ["ai"]))
        self.assertFalse(checks._contains_any("Export in a formal format.", ["form"]))

    def test_star_makes_prefix(self):
        self.assertTrue(checks._contains_any("Input validation is required.", ["valid*"]))
        self.assertFalse(checks._contains_any("Input validation is required.", ["valid"]))


class SimilarityTest(unittest.TestCase):
    def test_identical_text(self):
        self.assertEqual(similarity("Users can export reports.", "Users can export reports."), 1.0)

    def test_negation_is_ignored(self):
        self.assertEqual(similarity("The app shall store photos.", "The app shall not store photos."), 1.0)

    def test_inflections_match(self):
        self.assertGreaterEqual(similarity("Identify rocks from photos.", "Rock identification from a photo."), 0.99)

    def test_unrelated_text_scores_low(self):
        a = "Cancel a booking. A student shall be able to cancel their own booking until its start time."
        b = "Booking response time. Booking confirmation shall be shown within the response-time target."
        self.assertLess(similarity(a, b), checks.OVERLAP_THRESHOLD)

    def test_empty_text(self):
        self.assertEqual(similarity("", "anything"), 0.0)


class Scenario1CleanTest(unittest.TestCase):
    def test_complete_document_has_no_findings(self):
        self.assertEqual(lint(load_fixture("valid_full.json")), [])

    def test_minimal_document_reports_only_real_gaps(self):
        findings = lint(load_fixture("valid_minimal.json"))
        self.assertEqual(codes(findings), ["no_nfr", "no_user_story", "not_verifiable"])
        # "export ... as a PDF file" is not about uploads.
        self.assertEqual(topics(findings), [])


class Scenario2AmbiguousTest(unittest.TestCase):
    def setUp(self):
        self.doc = load_fixture("lint_ambiguous.json")

    def test_vague_requirement_flagged(self):
        findings = lint(self.doc)
        self.assertTrue(found(findings, "ambiguous_term", ["FR-001"]))
        message = next(f.message for f in findings if f.code == "ambiguous_term")
        self.assertIn("'fast'", message)
        self.assertIn("'user-friendly'", message)

    def test_fit_criterion_refines_vague_wording(self):
        # NFR-001 says "etc." but has a fit criterion.
        self.assertFalse(found(lint(self.doc), "ambiguous_term", ["NFR-001"]))
        req(self.doc, "FR-001")["fit_criterion"] = "Result shown within 3 s for 95% of photos"
        self.assertFalse(found(lint(self.doc), "ambiguous_term"))

    def test_open_ambiguity_issue_counts_as_tracked(self):
        self.doc["issues"] = [{
            "id": "ISS-001", "kind": "ambiguity", "severity": "important", "status": "open",
            "requirement_ids": ["FR-001"], "description": "'fast' and 'user-friendly' are not measurable.",
        }]
        self.assertEqual(validate(self.doc), [])
        self.assertFalse(found(lint(self.doc), "ambiguous_term"))

    def test_resolved_issue_with_vague_text_is_still_flagged(self):
        self.doc["issues"] = [{
            "id": "ISS-001", "kind": "ambiguity", "severity": "important", "status": "resolved",
            "requirement_ids": ["FR-001"], "description": "'fast' is not measurable.",
            "resolution": "User gave a 3 s target.",
        }]
        self.assertTrue(found(lint(self.doc), "ambiguous_term", ["FR-001"]))

    def test_rejected_requirement_ignored(self):
        req(self.doc, "FR-001")["status"] = "rejected"
        self.assertFalse(found(lint(self.doc), "ambiguous_term"))

    def test_vague_outcome_in_acceptance_criterion(self):
        findings = lint(self.doc)
        self.assertTrue(found(findings, "untestable_criterion", ["AC-001"]))
        self.assertFalse(found(findings, "untestable_criterion", ["AC-002"]))

    def test_vague_word_in_given_is_allowed_but_weak_phrase_is_not(self):
        ac = self.doc["acceptance_criteria"][1]
        ac["given"] = ["the network is fast"]
        self.assertFalse(found(lint(self.doc), "untestable_criterion", ["AC-002"]))
        ac["given"] = ["the photo is JPEG, PNG, etc."]
        self.assertTrue(found(lint(self.doc), "untestable_criterion", ["AC-002"]))


class Scenario3MissingInformationTest(unittest.TestCase):
    def setUp(self):
        self.doc = load_fixture("lint_missing_info.json")

    def test_topic_hints(self):
        messages = topics(lint(self.doc))
        for topic in ("authentication", "file and image limits", "error handling", "data storage"):
            self.assertTrue(any(topic in m for m in messages), topic)
        self.assertFalse(any("payments" in m for m in messages))

    def test_hint_names_the_requirements(self):
        hint = next(f for f in lint(self.doc) if f.code == "possibly_missing" and "file and image" in f.message)
        self.assertEqual(hint.ids, ("FR-001",))
        self.assertEqual(hint.level, "hint")

    def test_covered_topic_is_not_hinted(self):
        self.doc["rules"] = [{
            "id": "CON-001", "kind": "constraint", "statement": "Photos are JPEG or PNG, at most 10 MB.",
            "origin": "confirmed", "source": "clarification round 1",
        }]
        self.assertEqual(validate(self.doc), [])
        self.assertFalse(any("file and image" in m for m in topics(lint(self.doc))))

    def test_out_of_scope_topic_is_not_hinted(self):
        self.doc["project"]["scope_out"] = ["Account login (the app is anonymous)"]
        self.assertFalse(any("authentication" in m for m in topics(lint(self.doc))))

    def test_approved_requirement_with_open_critical_issue(self):
        self.assertTrue(found(lint(self.doc), "approved_with_critical_issue", ["FR-002"]))
        self.doc["issues"][0]["status"] = "resolved"
        self.doc["issues"][0]["resolution"] = "Only invited users can open the link."
        self.assertFalse(found(lint(self.doc), "approved_with_critical_issue"))


class Scenario4ContradictionTest(unittest.TestCase):
    def setUp(self):
        self.doc = load_fixture("lint_contradiction.json")

    def test_negated_pair_is_flagged(self):
        findings = lint(self.doc)
        self.assertTrue(found(findings, "possible_contradiction", ["FR-001", "FR-002"]))
        self.assertFalse(found(findings, "possible_duplicate"))

    def test_plain_negation_contradiction(self):
        req(self.doc, "FR-001")["description"] = "The app shall store the original photos in the user collection."
        req(self.doc, "FR-002")["description"] = "The app shall not store the original photos in the user collection."
        self.assertTrue(found(lint(self.doc), "possible_contradiction", ["FR-001", "FR-002"]))

    def test_tracked_conflict_is_not_reported_again(self):
        self.doc["issues"] = [{
            "id": "ISS-001", "kind": "conflict", "severity": "critical", "status": "open",
            "requirement_ids": ["FR-001", "FR-002"], "description": "Offline vs. cloud model.",
        }]
        self.assertFalse(found(lint(self.doc), "possible_contradiction"))

    def test_related_requirements_are_not_a_conflict(self):
        req(self.doc, "FR-002")["depends_on"] = ["FR-001"]
        self.assertEqual(validate(self.doc), [])
        self.assertFalse(found(lint(self.doc), "possible_contradiction"))


class Scenario5DuplicateTest(unittest.TestCase):
    def setUp(self):
        self.doc = load_fixture("lint_duplicate.json")

    def test_duplicate_pair_flagged(self):
        findings = lint(self.doc)
        self.assertTrue(found(findings, "possible_duplicate", ["FR-001", "FR-002"]))
        pair_codes = ("possible_duplicate", "possible_overlap", "possible_contradiction")
        self.assertFalse(any(f.code in pair_codes and "FR-003" in f.ids for f in findings))

    def test_tracked_duplicate_not_reported(self):
        self.doc["issues"] = [{
            "id": "ISS-001", "kind": "duplicate", "severity": "important", "status": "open",
            "requirement_ids": ["FR-002", "FR-001"], "description": "Same requirement twice.",
        }]
        self.assertFalse(found(lint(self.doc), "possible_duplicate"))

    def test_rejected_duplicate_not_reported(self):
        req(self.doc, "FR-002")["status"] = "rejected"
        self.assertFalse(found(lint(self.doc), "possible_duplicate"))

    def test_partial_overlap_is_a_hint(self):
        req(self.doc, "FR-002")["title"] = "Identify mineral"
        req(self.doc, "FR-002")["description"] = (
            "The app shall identify the mineral type from a photo and show its hardness."
        )
        findings = lint(self.doc)
        self.assertFalse(found(findings, "possible_duplicate"))
        overlap = [f for f in findings if f.code == "possible_overlap"]
        self.assertEqual([f.ids for f in overlap], [("FR-001", "FR-002")])
        self.assertEqual(overlap[0].level, "hint")

    def test_short_requirements_sharing_two_words_are_not_paired(self):
        req(self.doc, "FR-001")["title"] = "Save rock to collection"
        req(self.doc, "FR-001")["description"] = "The user shall be able to save a rock to their collection."
        self.assertFalse(any("FR-003" in f.ids for f in lint(self.doc) if f.code.startswith("possible_")))


class Scenario6RolesTest(unittest.TestCase):
    def setUp(self):
        self.doc = load_fixture("lint_roles.json")

    def test_roles_without_permissions(self):
        findings = [f for f in lint(self.doc) if f.code == "roles_without_permissions"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].ids, ("SH-002", "SH-003"))

    def test_hint_disappears_when_all_roles_have_permissions(self):
        self.doc["stakeholders"][1]["permissions"] = ["edit the reference catalogue"]
        self.doc["stakeholders"][2]["permissions"] = ["view identifications of own students"]
        self.assertFalse(found(lint(self.doc), "roles_without_permissions"))

    def test_single_role_needs_no_permissions(self):
        self.doc["stakeholders"] = self.doc["stakeholders"][1:2]
        req(self.doc, "FR-001")["stakeholders"] = ["SH-002"]
        self.assertFalse(found(lint(self.doc), "roles_without_permissions"))

    def test_admin_requirement_triggers_permissions_topic(self):
        self.assertTrue(any("user roles and permissions" in m for m in topics(lint(self.doc))))
        self.doc["stakeholders"][1]["permissions"] = ["edit catalogue entries (requires the admin permission)"]
        self.assertFalse(any("user roles and permissions" in m for m in topics(lint(self.doc))))


class Scenario7NonFunctionalTest(unittest.TestCase):
    def setUp(self):
        self.doc = load_fixture("lint_nfr.json")

    def test_vague_nfr_is_ambiguous_and_unverifiable(self):
        findings = lint(self.doc)
        for rid in ("NFR-001", "NFR-002"):
            self.assertTrue(found(findings, "ambiguous_term", [rid]), rid)
            self.assertTrue(found(findings, "not_verifiable", [rid]), rid)
        self.assertFalse(found(findings, "no_nfr"))
        self.assertFalse(found(findings, "no_user_story"))  # NFRs do not need stories

    def test_fit_criterion_makes_nfr_verifiable(self):
        req(self.doc, "NFR-001")["fit_criterion"] = "95% of results within 3 s on a 4G connection"
        req(self.doc, "NFR-002")["fit_criterion"] = "99.5% monthly availability"
        findings = lint(self.doc)
        self.assertFalse(found(findings, "ambiguous_term"))
        self.assertFalse(found(findings, "not_verifiable"))

    def test_document_without_nfr_gets_hint(self):
        self.assertTrue(found(lint(load_fixture("lint_contradiction.json")), "no_nfr"))


class TraceabilityTest(unittest.TestCase):
    def setUp(self):
        self.doc = load_fixture("valid_full.json")

    def test_story_without_acceptance_criteria(self):
        self.doc["acceptance_criteria"] = [ac for ac in self.doc["acceptance_criteria"] if ac["story_id"] != "US-002"]
        self.assertEqual(codes(lint(self.doc)), ["not_verifiable", "story_without_ac"])

    def test_story_with_only_positive_scenarios(self):
        self.doc["acceptance_criteria"] = [ac for ac in self.doc["acceptance_criteria"] if ac["id"] != "AC-002"]
        self.assertTrue(found(lint(self.doc), "only_positive_ac", ["US-001"]))

    def test_business_requirement_not_refined(self):
        req(self.doc, "FR-001").pop("derived_from")
        self.assertTrue(found(lint(self.doc), "business_requirement_not_refined", ["BR-001"]))

    def test_deferred_requirement_skips_traceability_gaps(self):
        self.doc["user_stories"] = [s for s in self.doc["user_stories"] if s["id"] != "US-002"]
        self.doc["acceptance_criteria"] = [ac for ac in self.doc["acceptance_criteria"] if ac["story_id"] != "US-002"]
        self.assertTrue(found(lint(self.doc), "no_user_story", ["FR-002"]))
        req(self.doc, "FR-002")["status"] = "deferred"
        req(self.doc, "FR-002")["origin"] = "assumed"
        self.assertEqual(lint(self.doc), [])


class RobustnessTest(unittest.TestCase):
    def test_malformed_documents_do_not_raise(self):
        for doc in ({}, [], None, "text", load_fixture("invalid_types.json"),
                    load_fixture("invalid_dependencies.json"), load_fixture("invalid_acceptance_criteria.json")):
            lint(doc)

    def test_finding_order_is_deterministic(self):
        doc = load_fixture("lint_missing_info.json")
        self.assertEqual([f.as_dict() for f in lint(doc)], [f.as_dict() for f in lint(doc)])


if __name__ == "__main__":
    unittest.main()
