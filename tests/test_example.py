"""Scenario 10: the complete rock-identification example (examples/rock-identification/).

The example was produced by following SKILL.md on input.md. These tests check that:
- the deliberate problems in input.md are detected (by the script or recorded as issues);
- the final requirements.json validates, and lint leaves only the one expected warning;
- the committed requirements.md is exactly what `rea.py export` generates from the JSON;
- the clarification log and the JSON agree with each other.
"""

import io
import json
import os
import re
import shutil
import tempfile
import unittest

from support import ROOT

import rea
from reqkit.checks import lint, scan_text
from reqkit.model import LIST_SECTIONS, validate
from reqkit.quality import assess
from reqkit.render import render_markdown

EXAMPLE_DIR = os.path.join(ROOT, "examples", "rock-identification")
ID_IN_TEXT = re.compile(r"(?<![A-Za-z0-9-])[A-Z]{2,4}-\d{3,}(?![0-9])")


def read(name):
    with open(os.path.join(EXAMPLE_DIR, name), encoding="utf-8") as fh:
        return fh.read()


def load_example():
    return json.loads(read("requirements.json"))


def json_ids(doc):
    return {item["id"] for section in LIST_SECTIONS for item in doc.get(section, []) if "id" in item}


class ExampleFilesTest(unittest.TestCase):
    def test_all_files_exist(self):
        for name in ("input.md", "clarifications.md", "requirements.json", "requirements.md"):
            with self.subTest(name):
                self.assertTrue(os.path.isfile(os.path.join(EXAMPLE_DIR, name)))


class DeliberateProblemsTest(unittest.TestCase):
    """input.md contains vague words, missing details, a contradiction and a duplicate."""

    def setUp(self):
        self.doc = load_example()
        self.issues = self.doc["issues"]
        self.reqs = {r["id"]: r for r in self.doc["requirements"]}

    def issues_of(self, kind, *ids):
        return [i for i in self.issues if i["kind"] == kind and set(ids) <= set(i["requirement_ids"])]

    def test_scan_flags_the_vague_words(self):
        terms = {hit["term"] for hit in scan_text(read("input.md"))}
        self.assertEqual(terms, {"accurate", "fast", "easy to use", "if possible"})

    def test_offline_vs_cloud_conflict_is_critical(self):
        found = self.issues_of("conflict", "NFR-001", "CON-001")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["severity"], "critical")

    def test_duplicate_is_recorded_and_rejected(self):
        self.assertEqual(len(self.issues_of("duplicate", "FR-003", "FR-004")), 1)
        self.assertEqual(self.reqs["FR-004"]["status"], "rejected")

    def test_vague_requirements_have_ambiguity_issues(self):
        for rid in ("NFR-002", "NFR-003", "NFR-004"):
            with self.subTest(rid):
                self.assertEqual(len(self.issues_of("ambiguity", rid)), 1)

    def test_missing_information_is_recorded(self):
        self.assertTrue(self.issues_of("missing_information", "FR-001"))  # photo limits
        self.assertTrue(self.issues_of("missing_information", "FR-003"))  # location privacy, storage

    def test_resolved_ambiguities_got_fit_criteria(self):
        for rid in ("NFR-003", "NFR-004"):
            with self.subTest(rid):
                self.assertTrue(self.reqs[rid].get("fit_criterion"))


class FinalDocumentTest(unittest.TestCase):
    def setUp(self):
        self.doc = load_example()

    def test_validates_without_errors_or_warnings(self):
        self.assertEqual(validate(self.doc), [])

    def test_lint_leaves_only_the_accepted_accuracy_gap(self):
        # The user did not know an accuracy target (ISS-003, accepted risk), so NFR-002
        # stays unverifiable. Nothing else should be left.
        findings = [(f.code, f.ids) for f in lint(self.doc)]
        self.assertEqual(findings, [("not_verifiable", ("NFR-002",))])

    def test_every_requirement_is_assessed(self):
        report = assess(self.doc)
        self.assertEqual([r.requirement_id for r in report.not_assessed], [])
        self.assertGreater(report.percent, 80)

    def test_no_open_critical_or_important_issues(self):
        left = [i["id"] for i in self.doc["issues"]
                if i["status"] == "open" and i["severity"] in ("critical", "important")]
        self.assertEqual(left, [])

    def test_assumptions_stay_assumed(self):
        for rule in self.doc["rules"]:
            if rule["kind"] == "assumption":
                with self.subTest(rule["id"]):
                    self.assertEqual(rule["origin"], "assumed")

    def test_sources_cite_only_completed_rounds(self):
        rounds = self.doc["project"]["clarification_round"]
        items = self.doc["stakeholders"] + self.doc["requirements"] + self.doc["rules"]
        for item in items:
            for n in re.findall(r"clarification round (\d+)", item.get("source", "")):
                with self.subTest(item["id"]):
                    self.assertLessEqual(int(n), rounds)


class MarkdownMatchesJsonTest(unittest.TestCase):
    def setUp(self):
        self.doc = load_example()
        self.md = read("requirements.md")

    def test_committed_markdown_is_current(self):
        self.assertEqual(self.md, render_markdown(self.doc),
                         "requirements.md is stale or hand-edited: run rea.py export again")

    def test_every_json_id_appears_and_nothing_else(self):
        self.assertEqual(set(ID_IN_TEXT.findall(self.md)), json_ids(self.doc))

    def test_cli_export_reproduces_the_file(self):
        tmp = tempfile.mkdtemp(prefix="rea-example-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        out, err = io.StringIO(), io.StringIO()
        code = rea.main(["export", os.path.join(EXAMPLE_DIR, "requirements.json"), "--out", tmp],
                        out=out, err=err)
        self.assertEqual(code, 0, err.getvalue())
        with open(os.path.join(tmp, "requirements.md"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), self.md)


class ClarificationLogTest(unittest.TestCase):
    def test_log_mentions_every_issue(self):
        log = read("clarifications.md")
        for issue in load_example()["issues"]:
            with self.subTest(issue["id"]):
                self.assertIn(issue["id"], log)

    def test_log_ids_exist_in_json(self):
        log = read("clarifications.md")
        self.assertLessEqual(set(ID_IN_TEXT.findall(log)), json_ids(load_example()))


if __name__ == "__main__":
    unittest.main()
