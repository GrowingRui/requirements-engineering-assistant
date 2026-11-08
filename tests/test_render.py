"""Tests for reqkit.render: requirements.json -> requirements.md.

The main property: the Markdown is consistent with the JSON. Every ID in the
JSON appears in the Markdown, no ID appears in the Markdown that is not in the
JSON, and the traceability matrix shows exactly the links recorded in the JSON.
"""

import glob
import os
import re
import unittest

from support import FIXTURES_DIR, load_fixture

from reqkit.model import LIST_SECTIONS, validate
from reqkit.render import NOT_AVAILABLE, SECTION_TITLES, InvalidDocument, render_markdown

ID_IN_TEXT = re.compile(r"(?<![A-Za-z0-9-])[A-Z]{2,4}-\d{3,}(?![0-9])")


def json_ids(doc):
    return {item["id"] for section in LIST_SECTIONS for item in doc.get(section, []) if "id" in item}


def section(md, number):
    """The text of section ``number`` (without its heading)."""
    start = md.index(f"\n## {number}. {SECTION_TITLES[number - 1]}\n")
    end = md.find("\n## ", start + 1)
    return md[start:end if end != -1 else len(md)].split("\n", 2)[2]


def table_row(text, first_cell):
    """Cells of the table row whose first cell is ``first_cell``."""
    line = next(l for l in text.splitlines() if l.startswith(f"| {first_cell} |"))
    return [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]


def rich_document():
    """valid_full.json plus a user requirement, a conflict and a rejected requirement."""
    doc = load_fixture("valid_full.json")
    doc["requirements"].insert(1, {
        "id": "UR-001", "type": "user", "title": "Find a room quickly",
        "description": "Students need to see which rooms are free right now.",
        "priority": "should", "origin": "confirmed", "status": "draft", "source": "user input",
    })
    doc["requirements"].append({
        "id": "FR-003", "type": "functional", "title": "Waiting list",
        "description": "Students shall be able to join a waiting list for a taken room.",
        "priority": "could", "origin": "suggested", "status": "rejected", "source": "",
    })
    doc["requirements"][2]["derived_from"] = ["BR-001", "UR-001"]  # FR-001
    doc["issues"].append({
        "id": "ISS-003", "kind": "conflict", "severity": "critical", "status": "open",
        "requirement_ids": ["FR-001", "FR-003"], "description": "Booking limit vs. waiting list.",
        "question": "Does a waiting-list place count towards the limit?",
        "suggestion": "Yes, it counts as one booking.",
    })
    doc["rules"][1]["statement"] = "Login uses SSO | no local passwords."
    return doc


class ConsistencyWithJsonTest(unittest.TestCase):
    def all_valid_fixtures(self):
        paths = sorted(glob.glob(os.path.join(FIXTURES_DIR, "valid_*.json")))
        paths += sorted(glob.glob(os.path.join(FIXTURES_DIR, "lint_*.json")))
        docs = [(os.path.basename(p), load_fixture(os.path.basename(p))) for p in paths]
        return docs + [("rich", rich_document())]

    def test_every_json_id_appears_and_nothing_else(self):
        for name, doc in self.all_valid_fixtures():
            with self.subTest(name):
                self.assertEqual([f for f in validate(doc) if f.level == "error"], [])
                md = render_markdown(doc)
                self.assertEqual(set(ID_IN_TEXT.findall(md)), json_ids(doc))

    def test_all_text_content_appears(self):
        doc = rich_document()
        md = render_markdown(doc)
        for r in doc["requirements"]:
            self.assertIn(r["title"], md)
            self.assertIn(r["description"], md)
        for r in doc["rules"]:
            self.assertIn(r["statement"].replace("|", "\\|"), md)
        for i in doc["issues"]:
            self.assertIn(i["description"], md)
        for ac in doc["acceptance_criteria"]:
            for line in ac["given"] + ac["when"] + ac["then"]:
                self.assertIn(line, md)
        for s in doc["stakeholders"]:
            for p in s["permissions"]:
                self.assertIn(p, md)

    def test_output_is_deterministic(self):
        self.assertEqual(render_markdown(rich_document()), render_markdown(rich_document()))


class StructureTest(unittest.TestCase):
    def test_fourteen_sections_in_order(self):
        md = render_markdown(load_fixture("valid_full.json"))
        headings = re.findall(r"^## (\d+)\. (.+)$", md, re.MULTILINE)
        self.assertEqual(headings, [(str(n), t) for n, t in enumerate(SECTION_TITLES, start=1)])
        self.assertTrue(md.startswith("# Library Room Booking: Requirements Specification\n"))
        self.assertTrue(md.endswith("\n") and not md.endswith("\n\n"))

    def test_empty_sections_say_not_available(self):
        md = render_markdown(load_fixture("valid_minimal.json"))
        for number in (2, 3, 4, 6, 7, 8, 11, 12):
            self.assertEqual(section(md, number).strip(), NOT_AVAILABLE, SECTION_TITLES[number - 1])
        self.assertIn("No conflicts", section(md, 10))

    def test_invalid_document_is_refused(self):
        with self.assertRaises(InvalidDocument) as ctx:
            render_markdown(load_fixture("invalid_dependencies.json"))
        self.assertTrue(ctx.exception.findings)
        self.assertTrue(all(f.level == "error" for f in ctx.exception.findings))


class SectionContentTest(unittest.TestCase):
    def setUp(self):
        self.doc = rich_document()
        self.md = render_markdown(self.doc)

    def test_requirements_are_grouped_by_type(self):
        self.assertIn("UR-001", section(self.md, 4))
        self.assertIn("### User requirements", section(self.md, 4))
        self.assertIn("FR-003", section(self.md, 5))
        self.assertNotIn("FR-001", ID_IN_TEXT.findall(section(self.md, 6)))

    def test_single_type_needs_no_subheading(self):
        md = render_markdown(load_fixture("valid_full.json"))
        self.assertTrue(section(md, 4).strip().startswith("### BR-001: Fair room usage"))

    def test_unconfirmed_items_are_labelled(self):
        self.assertIn("**Origin:** suggested (not confirmed)", section(self.md, 6))
        unconfirmed = section(self.md, 9).split("### Items not yet confirmed by the user", 1)[1]
        for rid in ("NFR-001", "FR-003", "ASM-001"):
            self.assertIn(f"| {rid} |", unconfirmed)
        self.assertNotIn("| FR-001 |", unconfirmed)

    def test_suggestions_are_marked_not_confirmed(self):
        self.assertIn("**Suggestion (not confirmed):** Yes, it counts as one booking.", section(self.md, 10))
        self.assertNotIn("**Suggestion:**", self.md)

    def test_issues_are_split_by_kind(self):
        self.assertIn("ISS-003", section(self.md, 10))
        self.assertNotIn("ISS-003", section(self.md, 9))
        self.assertIn("ISS-002", section(self.md, 9))

    def test_rules_and_assumptions_are_separate(self):
        self.assertIn("BRL-001", section(self.md, 7))
        self.assertNotIn("ASM-001", section(self.md, 7))
        self.assertIn("ASM-001", section(self.md, 8))

    def test_pipe_in_text_does_not_break_the_table(self):
        self.assertEqual(len(table_row(section(self.md, 7), "CON-001")), 6)

    def test_story_sentence(self):
        self.assertIn("As a student, I want to book a study room for a time slot, so that I have a quiet "
                      "place to study.", section(self.md, 11))

    def test_acceptance_criteria_use_given_when_then(self):
        text = section(self.md, 12)
        self.assertIn("#### AC-001: Book a free room (positive)", text)
        self.assertIn("- **Given** I am logged in as a student\n- **And** room R1 is free", text)

    def test_quality_section_shows_scores_and_reasons(self):
        text = section(self.md, 13)
        self.assertIn("**Overall:", text)
        self.assertNotIn("| FR-003 |", text)  # rejected: not scored
        self.assertEqual(table_row(text, "FR-001")[-1], "86%")  # consistency 0 from the open critical conflict
        self.assertIn("- **FR-001** (86%): consistency 0 (In open critical conflict or duplicate issue ISS-003)",
                      text)
        self.assertIn("- **Clarity** (judged, 2): Single action with a clear actor and object.", text)
        self.assertIn("- **Clarity** (judged, ?): Not assessed yet.", text)


class TraceabilityMatrixTest(unittest.TestCase):
    HEADERS = ["Requirement", "Status", "Derived from", "Refined by", "Depends on",
               "User stories", "Acceptance criteria", "Open issues", "Gaps"]

    def setUp(self):
        self.doc = rich_document()
        self.matrix = section(render_markdown(self.doc), 14)

    def row(self, rid):
        return dict(zip(self.HEADERS, table_row(self.matrix, rid)))

    def test_one_row_per_requirement(self):
        rows = [l for l in self.matrix.splitlines() if re.match(r"^\| [A-Z]+-\d+ \|", l)]
        self.assertEqual(len(rows), len(self.doc["requirements"]))

    def test_links_match_the_json_exactly(self):
        for r in self.doc["requirements"]:
            rid = r["id"]
            row = self.row(rid)
            expected = {
                "Derived from": r.get("derived_from", []),
                "Refined by": [c["id"] for c in self.doc["requirements"] if rid in c.get("derived_from", [])],
                "Depends on": r.get("depends_on", []),
                "User stories": [s["id"] for s in self.doc["user_stories"] if rid in s["requirement_ids"]],
                "Acceptance criteria": [a["id"] for a in self.doc["acceptance_criteria"]
                                        if rid in a["requirement_ids"]],
                "Open issues": [i["id"] for i in self.doc["issues"]
                                if i["status"] == "open" and rid in i["requirement_ids"]],
            }
            for column, ids in expected.items():
                self.assertEqual(row[column], ", ".join(ids) or "-", f"{rid} {column}")

    def test_gaps(self):
        self.assertEqual(self.row("FR-001")["Gaps"], "-")
        self.assertEqual(self.row("NFR-001")["Gaps"], "not confirmed, no source")
        self.assertEqual(self.row("UR-001")["Gaps"], "no user story")
        self.assertEqual(self.row("FR-003")["Gaps"], "-")  # rejected

    def test_deferred_requirement_has_no_coverage_gaps(self):
        self.doc["user_stories"] = [s for s in self.doc["user_stories"] if s["id"] != "US-002"]
        self.doc["acceptance_criteria"] = [a for a in self.doc["acceptance_criteria"] if a["story_id"] != "US-002"]
        md = render_markdown(self.doc)
        self.assertEqual(table_row(section(md, 14), "FR-002")[-1], "no user story, not verifiable")
        next(r for r in self.doc["requirements"] if r["id"] == "FR-002")["status"] = "deferred"
        md = render_markdown(self.doc)
        self.assertEqual(table_row(section(md, 14), "FR-002")[-1], "-")


if __name__ == "__main__":
    unittest.main()
