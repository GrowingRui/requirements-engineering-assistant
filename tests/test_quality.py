"""Tests for reqkit.quality: computed and judged scores (PLAN.md section 7).

Also covers the scoring side of scenarios 2 (ambiguity), 4 (a conflict lowers
the consistency score) and 7 (a fit criterion makes an NFR verifiable).
"""

import json
import unittest

from support import load_fixture

from reqkit.model import validate
from reqkit.quality import assess


def req(doc, rid):
    return next(r for r in doc["requirements"] if r["id"] == rid)


def score(doc, rid, characteristic):
    return assess(doc).get(rid).scores[characteristic]


def issue(iid, kind, severity, status, ids, **extra):
    data = {"id": iid, "kind": kind, "severity": severity, "status": status,
            "requirement_ids": ids, "description": f"{kind} issue"}
    if status != "open":
        data["resolution"] = "Handled."
    data.update(extra)
    return data


class FullDocumentTest(unittest.TestCase):
    def setUp(self):
        self.doc = load_fixture("valid_full.json")
        self.report = assess(self.doc)

    def test_every_requirement_is_scored_in_document_order(self):
        self.assertEqual([r.requirement_id for r in self.report.requirements],
                         ["BR-001", "FR-001", "FR-002", "NFR-001"])

    def test_clear_complete_requirement_gets_full_score(self):  # scenario 1
        fr = self.report.get("FR-001")
        self.assertEqual({c: s.value for c, s in fr.scores.items()}, dict.fromkeys(fr.scores, 2))
        self.assertEqual(fr.percent, 100.0)
        self.assertEqual(fr.weak, [])

    def test_overall_percentage_counts_only_applicable_points(self):
        # BR-001: 3 computed (verifiability n/a) = 6; FR-001: 7 x 2 = 14;
        # FR-002: 4 computed = 8; NFR-001: 6 applicable (feasibility null), 9 of 12.
        self.assertEqual(self.report.max_points, 40)
        self.assertEqual(self.report.points, 37)
        self.assertAlmostEqual(self.report.percent, 92.5)

    def test_needs_improvement_and_not_assessed(self):
        self.assertEqual([r.requirement_id for r in self.report.needs_improvement], ["NFR-001"])
        self.assertEqual(self.report.get("NFR-001").weak, ["completeness", "traceability"])
        self.assertEqual([r.requirement_id for r in self.report.not_assessed], ["BR-001", "FR-002"])

    def test_report_serialises_to_json(self):
        data = json.loads(json.dumps(self.report.as_dict()))
        self.assertEqual(data["points"], 37)
        self.assertEqual(data["needs_improvement"], ["NFR-001"])
        self.assertEqual(data["requirements"][1]["scores"]["clarity"]["method"], "judged")

    def test_rejected_requirement_is_not_scored(self):
        req(self.doc, "NFR-001")["status"] = "rejected"
        self.assertIsNone(assess(self.doc).get("NFR-001"))


class UnambiguityTest(unittest.TestCase):  # scenario 2
    def setUp(self):
        self.doc = load_fixture("lint_ambiguous.json")

    def test_untracked_vague_words_score_zero(self):
        s = score(self.doc, "FR-001", "unambiguity")
        self.assertEqual(s.value, 0)
        self.assertIn("'fast'", s.reason)

    def test_open_ambiguity_issue_scores_one(self):
        self.doc["issues"] = [issue("ISS-001", "ambiguity", "important", "open", ["FR-001"])]
        self.assertEqual(validate(self.doc), [])
        s = score(self.doc, "FR-001", "unambiguity")
        self.assertEqual(s.value, 1)
        self.assertIn("ISS-001", s.reason)

    def test_resolved_issue_with_vague_text_scores_zero(self):
        self.doc["issues"] = [issue("ISS-001", "ambiguity", "important", "resolved", ["FR-001"])]
        self.assertEqual(score(self.doc, "FR-001", "unambiguity").value, 0)

    def test_fit_criterion_scores_two(self):
        self.assertEqual(score(self.doc, "NFR-001", "unambiguity").value, 2)
        req(self.doc, "FR-001")["fit_criterion"] = "Result within 3 s for 95% of photos"
        self.assertEqual(score(self.doc, "FR-001", "unambiguity").value, 2)


class VerifiabilityTest(unittest.TestCase):
    def setUp(self):
        self.doc = load_fixture("valid_full.json")

    def test_story_without_criteria_scores_one(self):
        self.doc["acceptance_criteria"] = [a for a in self.doc["acceptance_criteria"] if a["story_id"] != "US-002"]
        self.assertEqual(score(self.doc, "FR-002", "verifiability").value, 1)

    def test_nothing_scores_zero(self):
        self.doc["acceptance_criteria"] = [a for a in self.doc["acceptance_criteria"] if a["story_id"] != "US-002"]
        self.doc["user_stories"] = [s for s in self.doc["user_stories"] if s["id"] != "US-002"]
        self.assertEqual(score(self.doc, "FR-002", "verifiability").value, 0)

    def test_fit_criterion_makes_nfr_verifiable(self):  # scenario 7
        doc = load_fixture("lint_nfr.json")
        self.assertEqual(score(doc, "NFR-001", "verifiability").value, 0)
        req(doc, "NFR-001")["fit_criterion"] = "95% of results within 3 s on a 4G connection"
        self.assertEqual(score(doc, "NFR-001", "verifiability").value, 2)

    def test_business_requirement_is_not_applicable(self):
        s = score(self.doc, "BR-001", "verifiability")
        self.assertIsNone(s.value)
        self.assertTrue(s.assessed)


class ConsistencyTest(unittest.TestCase):  # scenario 4
    def setUp(self):
        self.doc = load_fixture("lint_contradiction.json")

    def test_no_issue_scores_two(self):
        self.assertEqual(score(self.doc, "FR-001", "consistency").value, 2)

    def test_open_critical_conflict_scores_zero_on_both_sides(self):
        self.doc["issues"] = [issue("ISS-001", "conflict", "critical", "open", ["FR-001", "FR-002"])]
        self.assertEqual(validate(self.doc), [])
        for rid in ("FR-001", "FR-002"):
            self.assertEqual(score(self.doc, rid, "consistency").value, 0, rid)

    def test_non_critical_conflict_or_critical_overlap_scores_one(self):
        self.doc["issues"] = [issue("ISS-001", "conflict", "important", "open", ["FR-001", "FR-002"])]
        self.assertEqual(score(self.doc, "FR-001", "consistency").value, 1)
        self.doc["issues"] = [issue("ISS-001", "overlap", "critical", "open", ["FR-001", "FR-002"])]
        self.assertEqual(score(self.doc, "FR-001", "consistency").value, 1)

    def test_resolved_conflict_scores_two(self):
        self.doc["issues"] = [issue("ISS-001", "conflict", "critical", "resolved", ["FR-001", "FR-002"])]
        self.assertEqual(score(self.doc, "FR-001", "consistency").value, 2)

    def test_conflict_lowers_overall_percentage(self):
        before = assess(self.doc).percent
        self.doc["issues"] = [issue("ISS-001", "conflict", "critical", "open", ["FR-001", "FR-002"])]
        self.assertLess(assess(self.doc).percent, before)

    def test_ambiguity_issue_does_not_affect_consistency(self):
        self.doc["issues"] = [issue("ISS-001", "ambiguity", "critical", "open", ["FR-001"])]
        self.assertEqual(score(self.doc, "FR-001", "consistency").value, 2)


class TraceabilityTest(unittest.TestCase):
    def setUp(self):
        self.doc = load_fixture("valid_full.json")

    def test_no_source_scores_zero(self):
        self.assertEqual(score(self.doc, "NFR-001", "traceability").value, 0)

    def test_source_without_links_scores_one(self):
        req(self.doc, "NFR-001")["source"] = "user input"
        self.assertEqual(score(self.doc, "NFR-001", "traceability").value, 1)

    def test_child_requirement_counts_as_link(self):
        s = score(self.doc, "BR-001", "traceability")
        self.assertEqual(s.value, 2)
        self.assertIn("FR-001", s.reason)

    def test_parent_story_and_criteria_count_as_links(self):
        self.assertIn("BR-001, US-001, AC-001, AC-002", score(self.doc, "FR-001", "traceability").reason)


class JudgedScoresTest(unittest.TestCase):
    def setUp(self):
        self.doc = load_fixture("valid_full.json")

    def test_reason_is_taken_from_the_assessment(self):
        s = score(self.doc, "FR-001", "clarity")
        self.assertEqual((s.value, s.method, s.reason), (2, "judged", "Single action with a clear actor and object."))

    def test_null_score_is_not_applicable(self):
        s = score(self.doc, "NFR-001", "feasibility")
        self.assertIsNone(s.value)
        self.assertTrue(s.assessed)

    def test_missing_assessment_is_not_assessed(self):
        s = score(self.doc, "FR-002", "clarity")
        self.assertIsNone(s.value)
        self.assertFalse(s.assessed)

    def test_judged_zero_counts_against_requirement(self):
        self.doc["quality_assessments"][0]["scores"]["feasibility"] = 0
        fr = assess(self.doc).get("FR-001")
        self.assertEqual((fr.points, fr.max_points), (12, 14))
        self.assertIn("feasibility", fr.weak)


class EdgeCaseTest(unittest.TestCase):
    def test_document_without_requirements(self):
        report = assess({"schema_version": "1.0", "project": {"name": "X", "overview": "", "mode": "automatic"},
                         "requirements": []})
        self.assertEqual(report.requirements, [])
        self.assertIsNone(report.percent)

    def test_malformed_documents_do_not_raise(self):
        for doc in ({}, [], None, "text", load_fixture("invalid_types.json"),
                    load_fixture("invalid_dependencies.json"), load_fixture("invalid_acceptance_criteria.json")):
            assess(doc)


if __name__ == "__main__":
    unittest.main()
