"""Tests for scripts/rea.py, the command-line tool.

Most tests call ``rea.main()`` in-process with captured streams. A few run the
script as a subprocess to check real exit codes, running from another working
directory, and UTF-8 output through a pipe (the Windows default is a legacy
code page).
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from support import ROOT, SCRIPTS_DIR, fixture_path, load_fixture

import rea
from reqkit.model import new_document, validate
from reqkit.render import render_markdown

REA = os.path.join(SCRIPTS_DIR, "rea.py")

VAGUE_INPUT = (
    "# Rock app\n"
    "\n"
    "Users take a photo of a rock.\n"
    "The app should be fast and easy to use.\n"
)


def run(*argv):
    """Run rea.main in-process. Returns (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    code = rea.main(list(argv), out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def run_json(*argv):
    code, out, err = run(*argv, "--json")
    return code, json.loads(out), err


def run_process(*argv, cwd=None):
    """Run rea.py as a real process; output decoded as UTF-8."""
    env = dict(os.environ)
    env.pop("PYTHONIOENCODING", None)
    env.pop("PYTHONUTF8", None)
    proc = subprocess.run([sys.executable, REA, *argv], cwd=cwd or ROOT, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    return proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8")


class TempDirTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rea-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def path(self, *parts):
        return os.path.join(self.tmp, *parts)

    def write(self, name, text):
        with open(self.path(name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        return self.path(name)

    def write_json(self, name, doc):
        return self.write(name, json.dumps(doc, indent=2, ensure_ascii=False))

    def read(self, name):
        with open(self.path(name), encoding="utf-8") as fh:
            return fh.read()


# --- Usage ----------------------------------------------------------------------


class UsageTest(unittest.TestCase):
    def test_no_command_is_usage_error(self):
        code, out, err = run()
        self.assertEqual(code, 2)
        self.assertIn("usage:", err)

    def test_unknown_command_is_usage_error(self):
        code, _, err = run("frobnicate")
        self.assertEqual(code, 2)
        self.assertIn("invalid choice", err)

    def test_missing_argument_is_usage_error(self):
        code, _, err = run("validate")
        self.assertEqual(code, 2)
        self.assertIn("file", err)

    def test_help_lists_all_commands(self):
        code, out, _ = run("--help")
        self.assertEqual(code, 0)
        for command in ("init", "scan", "validate", "lint", "export"):
            self.assertIn(command, out)

    def test_version(self):
        code, out, _ = run("--version")
        self.assertEqual(code, 0)
        self.assertIn(rea.__version__, out)


# --- init -------------------------------------------------------------------------


class InitTest(TempDirTest):
    def test_creates_valid_empty_document(self):
        target = self.path("requirements.json")
        code, out, err = run("init", "--name", "Room booking", "--out", target)
        self.assertEqual((code, err), (0, ""))
        self.assertIn("Created", out)
        doc = json.loads(self.read("requirements.json"))
        self.assertEqual(doc, new_document("Room booking"))
        self.assertEqual(validate(doc), [])

    def test_mode_and_overview(self):
        target = self.path("r.json")
        code, _, _ = run("init", "--name", "X", "--mode", "automatic", "--overview", "An app.", "--out", target)
        self.assertEqual(code, 0)
        doc = json.loads(self.read("r.json"))
        self.assertEqual(doc["project"]["mode"], "automatic")
        self.assertEqual(doc["project"]["overview"], "An app.")

    def test_invalid_mode_is_usage_error(self):
        code, _, err = run("init", "--name", "X", "--mode", "manual", "--out", self.path("r.json"))
        self.assertEqual(code, 2)
        self.assertIn("invalid choice", err)
        self.assertFalse(os.path.exists(self.path("r.json")))

    def test_blank_name_is_usage_error(self):
        code, _, err = run("init", "--name", "  ", "--out", self.path("r.json"))
        self.assertEqual(code, 2)
        self.assertIn("name", err)
        self.assertFalse(os.path.exists(self.path("r.json")))

    def test_refuses_to_overwrite_without_force(self):
        target = self.write("requirements.json", '{"keep": true}')
        code, _, err = run("init", "--name", "X", "--out", target)
        self.assertEqual(code, 2)
        self.assertIn("already exists", err)
        self.assertEqual(json.loads(self.read("requirements.json")), {"keep": True})

        code, _, _ = run("init", "--name", "X", "--out", target, "--force")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(self.read("requirements.json"))["project"]["name"], "X")

    def test_missing_directory_is_file_error(self):
        code, _, err = run("init", "--name", "X", "--out", self.path("no", "such", "dir", "r.json"))
        self.assertEqual(code, 2)
        self.assertIn("does not exist", err)

    def test_json_output(self):
        target = self.path("r.json")
        code, data, _ = run_json("init", "--name", "X", "--out", target)
        self.assertEqual(code, 0)
        self.assertEqual(data, {"command": "init", "file": target, "created": True})


# --- scan -------------------------------------------------------------------------


class ScanTest(TempDirTest):
    def test_reports_vague_words_with_line_numbers(self):
        src = self.write("input.md", VAGUE_INPUT)
        code, out, _ = run("scan", src)
        self.assertEqual(code, 0)
        self.assertIn("line 4", out)
        self.assertIn("'fast'", out)
        self.assertIn("'easy to use'", out)
        self.assertNotIn("line 3", out)

    def test_json_output(self):
        src = self.write("input.md", VAGUE_INPUT)
        code, data, _ = run_json("scan", src)
        self.assertEqual(code, 0)
        self.assertEqual(data["command"], "scan")
        terms = {(m["line"], m["term"]) for m in data["matches"]}
        self.assertIn((4, "fast"), terms)
        self.assertIn((4, "easy to use"), terms)
        self.assertEqual(data["count"], len(data["matches"]))

    def test_clean_text(self):
        src = self.write("input.md", "Users upload a JPEG photo of at most 10 MB.\n")
        code, out, _ = run("scan", src)
        self.assertEqual(code, 0)
        self.assertIn("no vague words", out)

    def test_reads_standard_input(self):
        old = sys.stdin
        sys.stdin = io.StringIO(VAGUE_INPUT)
        try:
            code, data, _ = run_json("scan", "-")
        finally:
            sys.stdin = old
        self.assertEqual(code, 0)
        self.assertEqual(data["file"], "<stdin>")
        self.assertTrue(data["matches"])

    def test_missing_file_is_file_error(self):
        code, out, err = run("scan", self.path("missing.md"))
        self.assertEqual((code, out), (2, ""))
        self.assertIn("file not found", err)

    def test_non_utf8_file_is_file_error(self):
        with open(self.path("latin1.md"), "wb") as fh:
            fh.write("café is fast".encode("latin-1"))
        code, _, err = run("scan", self.path("latin1.md"))
        self.assertEqual(code, 2)
        self.assertIn("not UTF-8", err)


# --- validate ---------------------------------------------------------------------


class ValidateTest(TempDirTest):
    def test_valid_document(self):
        code, out, _ = run("validate", fixture_path("valid_full.json"))
        self.assertEqual(code, 0)
        self.assertIn("valid (0 errors", out)

    def test_invalid_document(self):
        code, out, _ = run("validate", fixture_path("invalid_dependencies.json"))
        self.assertEqual(code, 1)
        self.assertIn("INVALID", out)
        for error_code in ("broken_reference", "self_dependency", "dependency_cycle"):
            self.assertIn(error_code, out)

    def test_every_invalid_fixture_exits_1(self):
        for name in ("invalid_acceptance_criteria.json", "invalid_dependencies.json", "invalid_json.json",
                     "invalid_origin.json", "invalid_types.json"):
            with self.subTest(name):
                code, data, _ = run_json("validate", fixture_path(name))
                self.assertEqual(code, 1)
                self.assertFalse(data["valid"])
                self.assertGreater(data["counts"]["error"], 0)

    def test_invalid_json_reports_position(self):
        code, data, _ = run_json("validate", fixture_path("invalid_json.json"))
        self.assertEqual(code, 1)
        self.assertEqual([f["code"] for f in data["findings"]], ["invalid_json"])
        self.assertIn("line", data["findings"][0]["path"])

    def test_json_output_matches_model(self):
        doc = load_fixture("invalid_origin.json")
        code, data, _ = run_json("validate", fixture_path("invalid_origin.json"))
        self.assertEqual(code, 1)
        self.assertEqual(data["findings"], [f.as_dict() for f in validate(doc)])
        self.assertEqual(set(data["counts"]), {"error", "warning", "hint"})

    def test_warnings_do_not_fail(self):
        doc = load_fixture("valid_minimal.json")
        doc["requirements"][0].update(origin="open", status="draft", source="")
        path = self.write_json("r.json", doc)
        code, data, _ = run_json("validate", path)
        self.assertEqual(code, 0)
        self.assertTrue(data["valid"])
        self.assertIn("open_not_flagged", [f["code"] for f in data["findings"]])

    def test_utf8_bom_accepted(self):
        with open(self.path("bom.json"), "w", encoding="utf-8-sig") as fh:
            json.dump(load_fixture("valid_minimal.json"), fh)
        code, _, _ = run("validate", self.path("bom.json"))
        self.assertEqual(code, 0)

    def test_missing_file_is_file_error(self):
        code, out, err = run("validate", self.path("nope.json"))
        self.assertEqual((code, out), (2, ""))
        self.assertIn("file not found", err)

    def test_directory_is_file_error(self):
        code, _, err = run("validate", self.tmp)
        self.assertEqual(code, 2)
        self.assertIn("directory", err)


# --- lint -------------------------------------------------------------------------


class LintTest(TempDirTest):
    def test_clean_document(self):
        code, out, _ = run("lint", fixture_path("valid_full.json"))
        self.assertEqual(code, 0)
        self.assertIn("0 warnings, 0 hints", out)
        self.assertIn("Quality:", out)

    def test_warnings_are_reported_but_exit_0(self):
        code, out, _ = run("lint", fixture_path("lint_ambiguous.json"))
        self.assertEqual(code, 0)
        self.assertIn("ambiguous_term", out)
        self.assertIn("candidates", out)
        self.assertIn("Needs improvement", out)

    def test_hints_are_reported(self):
        code, data, _ = run_json("lint", fixture_path("lint_roles.json"))
        self.assertEqual(code, 0)
        self.assertGreater(data["counts"]["hint"], 0)
        self.assertTrue(all(f["level"] in ("warning", "hint") for f in data["findings"]))

    def test_json_includes_quality_report(self):
        code, data, _ = run_json("lint", fixture_path("valid_full.json"))
        self.assertEqual(code, 0)
        quality = data["quality"]
        self.assertEqual(set(quality), {"points", "max_points", "percent", "requirements",
                                        "needs_improvement", "not_assessed"})
        doc = load_fixture("valid_full.json")
        scored = [r["id"] for r in doc["requirements"] if r["status"] != "rejected"]
        self.assertEqual([r["requirement_id"] for r in quality["requirements"]], scored)

    def test_invalid_document_skips_checks_and_scores(self):
        code, out, _ = run("lint", fixture_path("invalid_dependencies.json"))
        self.assertEqual(code, 1)
        self.assertIn("dependency_cycle", out)
        self.assertIn("skipped", out)
        self.assertNotIn("Quality:", out)

        code, data, _ = run_json("lint", fixture_path("invalid_dependencies.json"))
        self.assertEqual(code, 1)
        self.assertIsNone(data["quality"])

    def test_empty_document(self):
        path = self.write_json("r.json", new_document("Empty"))
        code, out, _ = run("lint", path)
        self.assertEqual(code, 0)
        self.assertIn("no requirements to score", out)


# --- export -----------------------------------------------------------------------


class ExportTest(TempDirTest):
    def test_writes_markdown_next_to_json(self):
        doc = load_fixture("valid_full.json")
        path = self.write_json("requirements.json", doc)
        code, out, _ = run("export", path)
        self.assertEqual(code, 0)
        self.assertIn("requirements.md", out)
        self.assertEqual(self.read("requirements.md"), render_markdown(doc))

    def test_out_directory(self):
        os.mkdir(self.path("docs"))
        code, data, _ = run_json("export", fixture_path("valid_full.json"), "--out", self.path("docs"))
        self.assertEqual(code, 0)
        self.assertTrue(data["exported"])
        self.assertEqual(data["output"], self.path("docs", "requirements.md"))
        self.assertTrue(os.path.isfile(self.path("docs", "requirements.md")))

    def test_writes_lf_line_endings(self):
        run("export", fixture_path("valid_minimal.json"), "--out", self.tmp)
        with open(self.path("requirements.md"), "rb") as fh:
            self.assertNotIn(b"\r\n", fh.read())

    def test_refuses_invalid_document(self):
        code, out, _ = run("export", fixture_path("invalid_origin.json"), "--out", self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("not exported", out)
        self.assertFalse(os.path.exists(self.path("requirements.md")))

        code, data, _ = run_json("export", fixture_path("invalid_origin.json"), "--out", self.tmp)
        self.assertEqual(code, 1)
        self.assertFalse(data["exported"])
        self.assertTrue(all(f["level"] == "error" for f in data["findings"]))

    def test_refused_export_keeps_existing_markdown(self):
        self.write("requirements.md", "previous version\n")
        run("export", fixture_path("invalid_types.json"), "--out", self.tmp)
        self.assertEqual(self.read("requirements.md"), "previous version\n")

    def test_missing_out_directory_is_file_error(self):
        code, _, err = run("export", fixture_path("valid_full.json"), "--out", self.path("missing"))
        self.assertEqual(code, 2)
        self.assertIn("does not exist", err)


# --- Real process: exit codes, working directory, UTF-8 --------------------------


class ProcessTest(TempDirTest):
    def test_exit_codes(self):
        self.assertEqual(run_process("validate", fixture_path("valid_full.json"))[0], 0)
        self.assertEqual(run_process("validate", fixture_path("invalid_dependencies.json"))[0], 1)
        self.assertEqual(run_process("validate", self.path("missing.json"))[0], 2)
        self.assertEqual(run_process("no-such-command")[0], 2)

    def test_runs_from_any_working_directory(self):
        code, out, err = run_process("lint", fixture_path("valid_full.json"), cwd=self.tmp)
        self.assertEqual((code, err), (0, ""))
        self.assertIn("Quality:", out)

    def test_non_ascii_output_through_pipe(self):
        name = "Café – 岩石 ✓"
        doc = load_fixture("valid_minimal.json")
        doc["project"]["name"] = name
        doc["requirements"][0]["title"] = "Fast résumé upload"
        path = self.write_json("requirements.json", doc)

        code, out, err = run_process("validate", "--json", path)
        self.assertEqual((code, err), (0, ""))
        self.assertTrue(json.loads(out)["valid"])

        code, out, _ = run_process("scan", self.write("input.md", "Le résumé doit être fast ✓\n"))
        self.assertEqual(code, 0)
        self.assertIn("résumé", out)
        self.assertIn("✓", out)

        code, _, _ = run_process("export", path)
        self.assertEqual(code, 0)
        self.assertIn(name, self.read("requirements.md"))

    def test_init_then_validate_then_export(self):
        code, _, _ = run_process("init", "--name", "Demo", cwd=self.tmp)
        self.assertEqual(code, 0)
        self.assertEqual(run_process("validate", "requirements.json", cwd=self.tmp)[0], 0)
        self.assertEqual(run_process("lint", "requirements.json", cwd=self.tmp)[0], 0)
        self.assertEqual(run_process("export", "requirements.json", cwd=self.tmp)[0], 0)
        self.assertTrue(os.path.isfile(self.path("requirements.md")))


if __name__ == "__main__":
    unittest.main()
