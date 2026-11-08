"""Tests for reqkit.model: structure, IDs, references, dependencies, origin rules.

Scenarios from PLAN.md section 10: 8 (dependencies), 9 (incomplete acceptance
criteria), plus invalid JSON, wrong types and the origin rules.
"""

import os
import tempfile
import unittest

from support import codes, errors, fixture_path, load_fixture

from reqkit import model
from reqkit.model import has_errors, load_document, new_document, parse_document, validate


def error_at(findings, code, path):
    return any(f.level == "error" and f.code == code and f.path == path for f in findings)


class ValidDocumentsTest(unittest.TestCase):
    def test_full_fixture_has_no_findings(self):
        self.assertEqual(validate(load_fixture("valid_full.json")), [])

    def test_minimal_fixture_has_no_findings(self):
        self.assertEqual(validate(load_fixture("valid_minimal.json")), [])

    def test_new_document_is_valid(self):
        for mode in model.MODES:
            doc = new_document("Demo", mode=mode)
            self.assertEqual(validate(doc), [], mode)
            self.assertEqual(doc["schema_version"], model.SCHEMA_VERSION)

    def test_new_document_rejects_bad_arguments(self):
        with self.assertRaises(ValueError):
            new_document("Demo", mode="batch")
        with self.assertRaises(ValueError):
            new_document("  ")

    def test_empty_optional_lists_are_valid(self):
        doc = load_fixture("valid_minimal.json")
        doc["requirements"] = []
        self.assertEqual(validate(doc), [])


class StructureTest(unittest.TestCase):
    def test_top_level_must_be_object(self):
        for value in ([], "text", 3, None):
            findings = validate(value)
            self.assertEqual(codes(findings), ["type"], value)
            self.assertEqual(findings[0].path, "$")

    def test_missing_required_top_level_fields(self):
        findings = validate({})
        for name in ("schema_version", "project", "requirements"):
            self.assertTrue(error_at(findings, "missing_field", f"$.{name}"), name)

    def test_missing_required_requirement_field(self):
        doc = load_fixture("valid_minimal.json")
        del doc["requirements"][0]["priority"]
        self.assertTrue(error_at(validate(doc), "missing_field", "$.requirements[0].priority"))

    def test_wrong_types_fixture(self):
        findings = validate(load_fixture("invalid_types.json"))
        expected = [
            ("type", "$.issues"),
            ("type", "$.project.name"),
            ("type", "$.project.mode"),
            ("type", "$.project.clarification_round"),
            ("type", "$.requirements[0].id"),
            ("type", "$.requirements[0].title"),
            ("type", "$.requirements[0].priority"),
            ("type", "$.requirements[0].depends_on"),
            ("missing_field", "$.requirements[1].source"),
            ("type", "$.requirements[2]"),
            ("id_type_mismatch", "$.requirements[1].id"),
        ]
        for code, path in expected:
            self.assertTrue(error_at(findings, code, path), f"{code} at {path}")
        self.assertEqual(len(errors(findings)), len(expected))

    def test_enum_rejects_non_strings(self):
        doc = load_fixture("valid_minimal.json")
        doc["requirements"][0]["type"] = ["functional"]  # unhashable: must not crash
        doc["requirements"][0]["origin"] = None
        findings = validate(doc)
        self.assertTrue(error_at(findings, "type", "$.requirements[0].type"))
        self.assertTrue(error_at(findings, "type", "$.requirements[0].origin"))

    def test_booleans_are_not_integers(self):
        doc = load_fixture("valid_minimal.json")
        doc["project"]["clarification_round"] = True
        self.assertTrue(error_at(validate(doc), "type", "$.project.clarification_round"))

    def test_list_items_must_be_non_empty_strings(self):
        doc = load_fixture("valid_full.json")
        doc["project"]["scope_in"] = ["ok", "", 3]
        findings = validate(doc)
        self.assertTrue(error_at(findings, "type", "$.project.scope_in[1]"))
        self.assertTrue(error_at(findings, "type", "$.project.scope_in[2]"))

    def test_unknown_field_is_a_warning(self):
        doc = load_fixture("valid_minimal.json")
        doc["requirements"][0]["owner"] = "Ann"
        findings = validate(doc)
        self.assertEqual(codes(findings), ["unknown_field"])
        self.assertEqual(findings[0].level, "warning")
        self.assertFalse(has_errors(findings))

    def test_other_schema_version_is_a_warning(self):
        doc = load_fixture("valid_minimal.json")
        doc["schema_version"] = "2.0"
        findings = validate(doc)
        self.assertEqual(codes(findings), ["schema_version"])
        self.assertFalse(has_errors(findings))

    def test_garbage_shapes_never_raise(self):
        base = load_fixture("valid_full.json")
        garbage = [None, 0, True, 1.5, "x", [], {}, ["x"], [None], {"a": 1}]
        for section in model.LIST_SECTIONS:
            for idx in range(len(base.get(section, []))):
                for fname in list(base[section][idx]):
                    for value in garbage:
                        doc = load_fixture("valid_full.json")
                        doc[section][idx][fname] = value
                        try:
                            validate(doc)
                        except Exception as exc:  # pragma: no cover - failure path
                            self.fail(f"{section}[{idx}].{fname}={value!r} raised {exc!r}")
            for value in garbage:
                doc = load_fixture("valid_full.json")
                doc[section] = value
                validate(doc)
                doc = load_fixture("valid_full.json")
                doc[section] = [value]
                validate(doc)


class IdTest(unittest.TestCase):
    def test_duplicate_id_across_sections(self):
        doc = load_fixture("valid_full.json")
        doc["requirements"][2]["id"] = "FR-001"
        findings = validate(doc)
        self.assertTrue(error_at(findings, "duplicate_id", "$.requirements[2].id"))

    def test_prefix_must_match_section(self):
        doc = load_fixture("valid_full.json")
        doc["user_stories"][0]["id"] = "FR-900"
        findings = validate(doc)
        self.assertTrue(error_at(findings, "id_prefix", "$.user_stories[0].id"))

    def test_requirement_prefix_must_match_type(self):
        doc = load_fixture("valid_minimal.json")
        doc["requirements"][0]["type"] = "non_functional"
        self.assertTrue(error_at(validate(doc), "id_type_mismatch", "$.requirements[0].id"))

    def test_rule_prefix_must_match_kind(self):
        doc = load_fixture("valid_full.json")
        doc["rules"][1]["kind"] = "assumption"  # CON-001
        self.assertTrue(error_at(validate(doc), "id_type_mismatch", "$.rules[1].id"))

    def test_id_format(self):
        for bad in ("FR-1", "fr-001", "FR001", "X-001", "FR-001a"):
            doc = load_fixture("valid_minimal.json")
            doc["requirements"][0]["id"] = bad
            self.assertTrue(error_at(validate(doc), "type", "$.requirements[0].id"), bad)
        doc = load_fixture("valid_minimal.json")
        doc["requirements"][0]["id"] = "FR-1234"
        self.assertEqual(validate(doc), [])


class ReferenceTest(unittest.TestCase):
    def test_unknown_stakeholder(self):
        doc = load_fixture("valid_full.json")
        doc["requirements"][1]["stakeholders"] = ["SH-009"]
        self.assertTrue(error_at(validate(doc), "broken_reference", "$.requirements[1].stakeholders[0]"))

    def test_unknown_parent_requirement(self):
        doc = load_fixture("valid_full.json")
        doc["requirements"][1]["derived_from"] = ["BR-404"]
        self.assertTrue(error_at(validate(doc), "broken_reference", "$.requirements[1].derived_from[0]"))

    def test_self_derivation(self):
        doc = load_fixture("valid_full.json")
        doc["requirements"][1]["derived_from"] = ["FR-001"]
        self.assertIn("self_derivation", codes(validate(doc), "error"))

    def test_derivation_from_functional_is_a_warning(self):
        doc = load_fixture("valid_full.json")
        doc["requirements"][2]["derived_from"] = ["FR-001"]
        findings = validate(doc)
        self.assertEqual(codes(findings), ["derivation"])
        self.assertFalse(has_errors(findings))

    def test_issue_may_reference_rules(self):
        doc = load_fixture("valid_full.json")
        doc["issues"][1]["requirement_ids"] = ["ASM-001"]
        self.assertEqual(validate(doc), [])

    def test_issue_unknown_reference(self):
        doc = load_fixture("valid_full.json")
        doc["issues"][0]["requirement_ids"] = ["FR-777"]
        self.assertTrue(error_at(validate(doc), "broken_reference", "$.issues[0].requirement_ids[0]"))

    def test_rule_related_unknown(self):
        doc = load_fixture("valid_full.json")
        doc["rules"][0]["related"] = ["US-404"]
        self.assertTrue(error_at(validate(doc), "broken_reference", "$.rules[0].related[0]"))

    def test_story_unknown_requirement(self):
        doc = load_fixture("valid_full.json")
        doc["user_stories"][0]["requirement_ids"] = ["FR-404"]
        self.assertTrue(error_at(validate(doc), "broken_reference", "$.user_stories[0].requirement_ids[0]"))

    def test_story_without_requirement_is_a_warning(self):
        doc = load_fixture("valid_full.json")
        doc["user_stories"][0]["requirement_ids"] = []
        findings = validate(doc)
        self.assertEqual(codes(findings), ["untraced_story"])

    def test_malformed_reference_reported_once(self):
        doc = load_fixture("valid_full.json")
        doc["requirements"][2]["depends_on"] = ["bad id"]
        findings = validate(doc)
        self.assertEqual(codes(findings), ["type"])

    def test_conflict_needs_two_items(self):
        doc = load_fixture("valid_full.json")
        doc["issues"][1]["kind"] = "conflict"
        self.assertEqual(codes(validate(doc)), ["single_sided_conflict"])

    def test_resolved_issue_needs_resolution(self):
        doc = load_fixture("valid_full.json")
        del doc["issues"][0]["resolution"]
        self.assertEqual(codes(validate(doc)), ["missing_resolution"])


class DependencyTest(unittest.TestCase):
    """Scenario 8: broken reference, self-dependency and cycle."""

    def setUp(self):
        self.findings = validate(load_fixture("invalid_dependencies.json"))

    def test_expected_errors_only(self):
        self.assertEqual(codes(self.findings),
                         ["broken_reference", "dependency_cycle", "self_dependency"])

    def test_broken_reference(self):
        self.assertTrue(error_at(self.findings, "broken_reference", "$.requirements[3].depends_on[1]"))

    def test_self_dependency_not_also_a_cycle(self):
        cycles = [f for f in self.findings if f.code == "dependency_cycle"]
        self.assertEqual(len(cycles), 1)
        self.assertNotIn("FR-004", cycles[0].ids)

    def test_cycle_reported_once_with_its_members(self):
        cycle = next(f for f in self.findings if f.code == "dependency_cycle")
        self.assertEqual(cycle.ids, ("FR-001", "FR-002", "FR-003"))
        self.assertIn("FR-001 -> FR-002 -> FR-003 -> FR-001", cycle.message)

    def test_two_node_cycle(self):
        doc = load_fixture("valid_full.json")
        doc["requirements"][1]["depends_on"] = ["FR-002"]  # FR-002 already depends on FR-001
        cycles = [f for f in validate(doc) if f.code == "dependency_cycle"]
        self.assertEqual([c.ids for c in cycles], [("FR-001", "FR-002")])

    def test_diamond_is_not_a_cycle(self):
        doc = load_fixture("invalid_dependencies.json")
        reqs = doc["requirements"]
        reqs[0]["depends_on"] = ["FR-002", "FR-003"]
        reqs[1]["depends_on"] = ["FR-004"]
        reqs[2]["depends_on"] = ["FR-004"]
        reqs[3]["depends_on"] = []
        self.assertEqual(validate(doc), [])

    def test_long_chain_has_no_recursion_limit(self):
        doc = new_document("Chain")
        n = 3000
        for i in range(1, n + 1):
            doc["requirements"].append({
                "id": f"FR-{i:04d}", "type": "functional", "title": f"R{i}",
                "description": "Step.", "priority": "must", "origin": "assumed",
                "status": "draft", "source": "",
                "depends_on": [f"FR-{i + 1:04d}"] if i < n else ["FR-0001"],
            })
        cycles = [f for f in validate(doc) if f.code == "dependency_cycle"]
        self.assertEqual(len(cycles), 1)
        self.assertEqual(len(cycles[0].ids), n)


class AcceptanceCriteriaTest(unittest.TestCase):
    """Scenario 9: incomplete acceptance criteria."""

    def setUp(self):
        self.findings = validate(load_fixture("invalid_acceptance_criteria.json"))

    def test_empty_given_when_then_rejected(self):
        for step in ("given", "when", "then"):
            self.assertTrue(error_at(self.findings, "type", f"$.acceptance_criteria[0].{step}"), step)

    def test_blank_step_rejected(self):
        self.assertTrue(error_at(self.findings, "type", "$.acceptance_criteria[1].then[0]"))

    def test_unknown_story_rejected(self):
        self.assertTrue(error_at(self.findings, "broken_reference", "$.acceptance_criteria[2].story_id"))

    def test_missing_then_rejected(self):
        self.assertTrue(error_at(self.findings, "missing_field", "$.acceptance_criteria[3].then"))

    def test_nothing_else_reported(self):
        self.assertEqual(len(self.findings), 6)


class OriginRulesTest(unittest.TestCase):
    def setUp(self):
        self.findings = validate(load_fixture("invalid_origin.json"))

    def test_approved_requires_confirmed(self):
        self.assertTrue(error_at(self.findings, "unconfirmed_approval", "$.requirements[0].status"))
        self.assertTrue(error_at(self.findings, "unconfirmed_approval", "$.requirements[2].status"))

    def test_confirmed_requires_source(self):
        self.assertTrue(error_at(self.findings, "unsourced_confirmation", "$.requirements[1].source"))
        self.assertTrue(error_at(self.findings, "unsourced_confirmation", "$.rules[0].source"))

    def test_exact_findings(self):
        self.assertEqual(codes(self.findings), ["unconfirmed_approval"] * 2 + ["unsourced_confirmation"] * 2)

    def test_confirmed_with_source_may_be_approved(self):
        doc = load_fixture("invalid_origin.json")
        req = doc["requirements"][0]
        req["origin"], req["source"] = "confirmed", "clarification round 1"
        findings = validate(doc)
        self.assertFalse(error_at(findings, "unconfirmed_approval", "$.requirements[0].status"))

    def test_open_origin_should_need_clarification(self):
        doc = load_fixture("valid_minimal.json")
        doc["requirements"][0]["origin"] = "open"
        findings = validate(doc)
        self.assertEqual(codes(findings), ["open_not_flagged"])
        self.assertEqual(findings[0].level, "warning")
        doc["requirements"][0]["status"] = "needs_clarification"
        self.assertEqual(validate(doc), [])

    def test_confirmed_assumption_is_a_warning(self):
        doc = load_fixture("valid_full.json")
        doc["rules"][2].update(origin="confirmed", source="round 1")
        self.assertEqual(codes(validate(doc)), ["confirmed_assumption"])


class QualityAssessmentTest(unittest.TestCase):
    def test_only_judged_characteristics_allowed(self):
        doc = load_fixture("valid_full.json")
        doc["quality_assessments"][0]["scores"]["verifiability"] = 2
        self.assertTrue(error_at(validate(doc), "type", "$.quality_assessments[0].scores.verifiability"))

    def test_score_range(self):
        for bad in (3, -1, 1.5, True, "2"):
            doc = load_fixture("valid_full.json")
            doc["quality_assessments"][0]["scores"]["clarity"] = bad
            self.assertTrue(error_at(validate(doc), "type", "$.quality_assessments[0].scores.clarity"), bad)

    def test_null_score_needs_no_reason(self):
        doc = load_fixture("valid_full.json")
        self.assertIsNone(doc["quality_assessments"][1]["scores"]["feasibility"])
        self.assertEqual(validate(doc), [])

    def test_score_without_reason_is_a_warning(self):
        doc = load_fixture("valid_full.json")
        del doc["quality_assessments"][0]["reasons"]["clarity"]
        self.assertEqual(codes(validate(doc)), ["unexplained_score"])

    def test_unknown_and_duplicate_assessment(self):
        doc = load_fixture("valid_full.json")
        qa = doc["quality_assessments"]
        qa.append(dict(qa[0]))
        qa.append({"requirement_id": "FR-404", "scores": {}, "reasons": {}})
        findings = validate(doc)
        self.assertTrue(error_at(findings, "duplicate_assessment", "$.quality_assessments[2].requirement_id"))
        self.assertTrue(error_at(findings, "broken_reference", "$.quality_assessments[3].requirement_id"))


class LoadingTest(unittest.TestCase):
    def test_invalid_json_fixture(self):
        doc, findings = load_document(fixture_path("invalid_json.json"))
        self.assertIsNone(doc)
        self.assertEqual(codes(findings), ["invalid_json"])
        self.assertEqual(findings[0].path, "line 3, column 32")

    def test_empty_text_is_invalid_json(self):
        doc, findings = parse_document("")
        self.assertIsNone(doc)
        self.assertEqual(codes(findings), ["invalid_json"])

    def test_bom_is_accepted(self):
        doc, findings = parse_document("﻿" + '{"a": 1}')
        self.assertEqual((doc, findings), ({"a": 1}, []))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bom.json")
            with open(path, "w", encoding="utf-8-sig") as fh:
                fh.write('{"b": 2}')
            self.assertEqual(load_document(path), ({"b": 2}, []))

    def test_missing_file_raises_oserror(self):
        with self.assertRaises(OSError):
            load_document(fixture_path("does_not_exist.json"))

    def test_valid_fixture_loads(self):
        doc, findings = load_document(fixture_path("valid_full.json"))
        self.assertEqual(findings, [])
        self.assertEqual(validate(doc), [])


class FindingTest(unittest.TestCase):
    def test_as_dict(self):
        f = model.Finding("error", "x", "$.a", "msg", ("FR-001",))
        self.assertEqual(f.as_dict(), {"level": "error", "code": "x", "path": "$.a",
                                       "message": "msg", "ids": ["FR-001"]})


if __name__ == "__main__":
    unittest.main()
