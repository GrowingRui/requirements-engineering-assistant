"""Tests that SKILL.md, references/ and README.md stay in sync with the code.

Checks the SKILL.md front matter and length, that every ``rea.py`` command and
option mentioned in the docs exists, that the documented workflow commands
run, that every link resolves, that every finding code and data model field is
documented, and that the example in data_model.md is valid.
"""

import io
import json
import os
import re
import shlex
import shutil
import tempfile
import unittest

from support import ROOT, SCRIPTS_DIR

import rea
from reqkit.model import LIST_SECTIONS, PROJECT_FIELDS, TOP_LEVEL_FIELDS, validate

SKILL_PATH = os.path.join(ROOT, "SKILL.md")
REFERENCES_DIR = os.path.join(ROOT, "references")
REFERENCE_FILES = (
    "data_model.md",
    "requirements_quality.md",
    "user_story_guidelines.md",
    "acceptance_criteria_guidelines.md",
    "clarification_guidelines.md",
)
MAX_SKILL_LINES = 200
INLINE_CODE = re.compile(r"`([^`\n]+)`")
LINK = re.compile(r"\]\(([^)\s]+)\)")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def doc_paths():
    return [SKILL_PATH] + [os.path.join(REFERENCES_DIR, name) for name in REFERENCE_FILES]


def all_docs_text():
    return "\n".join(read(p) for p in doc_paths())


def front_matter(text):
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return None
    fields = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    return fields


def rea_invocations(text):
    """Token lists of inline code spans that run rea.py, optional [parts] removed."""
    calls = []
    for span in INLINE_CODE.findall(text):
        if "rea.py" not in span:
            continue
        span = re.sub(r"\[[^\]]*\]", " ", span)
        tokens = shlex.split(span)
        start = next(i for i, t in enumerate(tokens) if t.endswith("rea.py"))
        if tokens[start + 1:]:  # a bare "scripts/rea.py" is a path, not a call
            calls.append(tokens[start + 1:])
    return calls


def subcommand_options():
    """{subcommand: set of option strings}."""
    parser = rea.build_parser()
    sub = next(a for a in parser._actions if a.__class__.__name__ == "_SubParsersAction")
    return {name: {opt for action in p._actions for opt in action.option_strings}
            for name, p in sub.choices.items()}


def emitted_codes():
    """Every finding code the validator and linter can produce."""
    found = set()
    for name in ("model.py", "checks.py"):
        source = read(os.path.join(SCRIPTS_DIR, "reqkit", name))
        found |= set(re.findall(r'Finding\(\s*"(?:error|warning|hint)",\s*"([a-z_]+)"', source))
    return found


class SkillFileTest(unittest.TestCase):
    def setUp(self):
        self.text = read(SKILL_PATH)

    def test_front_matter(self):
        fields = front_matter(self.text)
        self.assertIsNotNone(fields, "SKILL.md must start with a --- front matter block")
        self.assertEqual(fields.get("name"), "requirements-engineering-assistant")
        self.assertRegex(fields["name"], r"^[a-z0-9-]{1,64}$")
        description = fields.get("description", "")
        self.assertTrue(description, "description is required")
        self.assertLessEqual(len(description), 1024)

    def test_is_short(self):
        self.assertLessEqual(len(self.text.splitlines()), MAX_SKILL_LINES)

    def test_states_core_rules(self):
        lowered = self.text.lower()
        for phrase in ("never invent facts", "3–7 questions", "never edit", "interactive", "automatic"):
            self.assertIn(phrase, lowered)
        for origin in ("confirmed", "assumed", "suggested", "open"):
            self.assertIn(f"`{origin}`", self.text)


class CommandsTest(unittest.TestCase):
    def test_every_mentioned_command_and_option_exists(self):
        options = subcommand_options()
        for path in doc_paths():
            for tokens in rea_invocations(read(path)):
                with self.subTest(file=os.path.basename(path), command=" ".join(tokens)):
                    if tokens[0] == "COMMAND":
                        continue
                    self.assertIn(tokens[0], options)
                    for token in tokens[1:]:
                        if token.startswith("--"):
                            self.assertIn(token, options[tokens[0]])

    def test_every_command_is_documented_in_skill(self):
        mentioned = {tokens[0] for tokens in rea_invocations(read(SKILL_PATH))}
        self.assertEqual(set(subcommand_options()), mentioned - {"COMMAND"})

    def test_documented_workflow_runs(self):
        # The fullest mention of each command (the table row), not "run `rea.py lint`".
        commands = {}
        for tokens in rea_invocations(read(SKILL_PATH)):
            if len(tokens) > len(commands.get(tokens[0], [])):
                commands[tokens[0]] = tokens
        work = tempfile.mkdtemp()
        old_cwd = os.getcwd()
        try:
            os.chdir(work)
            os.mkdir("requirements")
            with open("input.md", "w", encoding="utf-8") as fh:
                fh.write("Users upload a photo. The app must be fast.\n")
            for name in ("init", "scan", "validate", "lint", "export"):
                out, err = io.StringIO(), io.StringIO()
                code = rea.main(list(commands[name]), out=out, err=err)
                self.assertEqual(code, 0, f"{name}: {out.getvalue()}{err.getvalue()}")
            self.assertTrue(os.path.isfile(os.path.join("requirements", "requirements.md")))
        finally:
            os.chdir(old_cwd)
            shutil.rmtree(work, ignore_errors=True)


class LinksTest(unittest.TestCase):
    def test_links_resolve(self):
        for path in doc_paths():
            base = os.path.dirname(path)
            for target in LINK.findall(read(path)):
                if target.startswith(("http://", "https://", "#")):
                    continue
                with self.subTest(file=os.path.basename(path), link=target):
                    self.assertTrue(os.path.isfile(os.path.join(base, target.split("#")[0])))

    def test_every_reference_is_linked_from_skill(self):
        links = set(LINK.findall(read(SKILL_PATH)))
        on_disk = {name for name in os.listdir(REFERENCES_DIR) if name.endswith(".md")}
        self.assertEqual(on_disk, set(REFERENCE_FILES))
        for name in REFERENCE_FILES:
            self.assertIn(f"references/{name}", links)


README_PATH = os.path.join(ROOT, "README.md")
FENCED_REA = re.compile(r"^python\s+scripts/rea\.py\s+(.+)$", re.MULTILINE)


class ReadmeTest(unittest.TestCase):
    def setUp(self):
        self.text = read(README_PATH)

    def test_shell_examples_use_real_commands_and_options(self):
        options = subcommand_options()
        calls = [shlex.split(m) for m in FENCED_REA.findall(self.text)]
        self.assertEqual({tokens[0] for tokens in calls}, set(options))
        for tokens in calls:
            with self.subTest(command=" ".join(tokens)):
                for token in tokens[1:]:
                    if token.startswith("--"):
                        self.assertIn(token, options[tokens[0]])

    def test_documented_options_exist(self):
        all_options = set().union(*subcommand_options().values())
        for option in set(re.findall(r"`(--[a-z-]+)", self.text)):
            with self.subTest(option=option):
                self.assertIn(option, all_options)

    def test_links_resolve(self):
        for target in LINK.findall(self.text):
            if target.startswith(("http://", "https://", "#")):
                continue
            with self.subTest(link=target):
                self.assertTrue(os.path.exists(os.path.join(ROOT, target.split("#")[0])))

    def test_anchors_exist(self):
        headings = {re.sub(r"[^a-z0-9 -]", "", h.lower()).replace(" ", "-")
                    for h in re.findall(r"^#{2,3} (.+)$", self.text, re.MULTILINE)}
        for anchor in re.findall(r"\]\(#([^)]+)\)", self.text):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, headings)


class ReferenceContentTest(unittest.TestCase):
    def test_every_finding_code_is_documented(self):
        documented = set(INLINE_CODE.findall(all_docs_text()))
        codes = emitted_codes()
        self.assertGreater(len(codes), 20)
        self.assertEqual(sorted(codes - documented), [])

    def test_every_field_is_documented(self):
        documented = set(INLINE_CODE.findall(read(os.path.join(REFERENCES_DIR, "data_model.md"))))
        tables = [TOP_LEVEL_FIELDS, PROJECT_FIELDS, *LIST_SECTIONS.values()]
        missing = sorted({name for table in tables for name in table} - documented)
        self.assertEqual(missing, [])

    def test_data_model_example_is_valid(self):
        text = read(os.path.join(REFERENCES_DIR, "data_model.md"))
        blocks = re.findall(r"```json\n(.*?)```", text, re.DOTALL)
        self.assertEqual(len(blocks), 1)
        findings = validate(json.loads(blocks[0]))
        self.assertEqual([f.as_dict() for f in findings], [])


if __name__ == "__main__":
    unittest.main()
