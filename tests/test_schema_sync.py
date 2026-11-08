"""The JSON Schema file must stay in sync with the Python data model.

1. The file on disk equals what model.json_schema() generates.
2. Behaviour check: a small interpreter for the schema keywords we use agrees
   with model.validate() on every fixture and on a set of mutated documents.
   (The jsonschema package is not required; if it is installed it is used too.)
"""

import json
import os
import re
import unittest

from support import ROOT, load_fixture

from reqkit import model
from reqkit.model import json_schema, validate

SCHEMA_PATH = os.path.join(ROOT, *model.SCHEMA_FILE.split("/"))
REGENERATE = "python scripts/reqkit/model.py"

# Errors that a JSON Schema can express. Everything else (references, unique IDs,
# cycles, duplicate assessments) is only checked by validate().
SCHEMA_EXPRESSIBLE = {
    "type", "missing_field", "id_prefix", "id_type_mismatch",
    "unconfirmed_approval", "unsourced_confirmation",
}

_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: type(v) is int,
}


def _equal(a, b):
    return type(a) is type(b) and a == b


def schema_errors(instance, schema, root=None, path="$"):
    """Minimal draft 2020-12 evaluator for the keywords json_schema() emits."""
    root = root if root is not None else schema
    out = []
    if "$ref" in schema:
        name = schema["$ref"].split("/")[-1]
        out += schema_errors(instance, root["$defs"][name], root, path)
    if "type" in schema and not _TYPES[schema["type"]](instance):
        return out + [f"{path}: type"]
    if "enum" in schema and not any(_equal(instance, e) for e in schema["enum"]):
        out.append(f"{path}: enum")
    if "const" in schema and not _equal(instance, schema["const"]):
        out.append(f"{path}: const")
    if "pattern" in schema and isinstance(instance, str) and not re.search(schema["pattern"], instance):
        out.append(f"{path}: pattern")
    if "minimum" in schema and type(instance) is int and instance < schema["minimum"]:
        out.append(f"{path}: minimum")
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            out.append(f"{path}: minItems")
        if "items" in schema:
            for i, item in enumerate(instance):
                out += schema_errors(item, schema["items"], root, f"{path}[{i}]")
    if isinstance(instance, dict):
        for name in schema.get("required", []):
            if name not in instance:
                out.append(f"{path}.{name}: required")
        props = schema.get("properties", {})
        for name, value in instance.items():
            if name in props:
                out += schema_errors(value, props[name], root, f"{path}.{name}")
            elif "additionalProperties" in schema:
                out += schema_errors(value, schema["additionalProperties"], root, f"{path}.{name}")
            if "propertyNames" in schema:
                out += schema_errors(name, schema["propertyNames"], root, f"{path}.{name}(key)")
    for sub in schema.get("allOf", []):
        out += schema_errors(instance, sub, root, path)
    if "if" in schema and not schema_errors(instance, schema["if"], root, path):
        out += schema_errors(instance, schema.get("then", {}), root, path)
    return out


def model_rejects(doc):
    return any(f.level == "error" and f.code in SCHEMA_EXPRESSIBLE for f in validate(doc))


def _mutations():
    """(label, document) pairs: each breaks one schema-expressible rule, or none."""
    def m(name, fn, fixture="valid_full.json"):
        doc = load_fixture(fixture)
        fn(doc)
        return name, doc

    return [
        m("unchanged", lambda d: None),
        m("minimal", lambda d: None, "valid_minimal.json"),
        m("new_document", lambda d: d.clear() or d.update(model.new_document("X"))),
        m("unknown field allowed", lambda d: d["requirements"][0].update(extra=1)),
        m("missing project", lambda d: d.pop("project")),
        m("missing title", lambda d: d["requirements"][0].pop("title")),
        m("blank title", lambda d: d["requirements"][0].update(title="  ")),
        m("bad enum", lambda d: d["requirements"][0].update(priority="high")),
        m("bad mode", lambda d: d["project"].update(mode="batch")),
        m("negative round", lambda d: d["project"].update(clarification_round=-1)),
        m("bool round", lambda d: d["project"].update(clarification_round=True)),
        m("bad id", lambda d: d["requirements"][0].update(id="BR-1")),
        m("wrong section prefix", lambda d: d["user_stories"][0].update(id="FR-900")),
        m("type/prefix mismatch", lambda d: d["requirements"][1].update(type="non_functional")),
        m("kind/prefix mismatch", lambda d: d["rules"][1].update(kind="assumption")),
        m("approved suggestion", lambda d: d["requirements"][3].update(status="approved")),
        m("confirmed without source", lambda d: d["requirements"][1].update(source="")),
        m("confirmed rule without source", lambda d: d["rules"][0].update(source=" ")),
        m("empty given", lambda d: d["acceptance_criteria"][0].update(given=[])),
        m("blank then item", lambda d: d["acceptance_criteria"][0].update(then=[""])),
        m("bad score key", lambda d: d["quality_assessments"][0]["scores"].update(traceability=2)),
        m("bad score value", lambda d: d["quality_assessments"][0]["scores"].update(clarity=3)),
        m("bool score", lambda d: d["quality_assessments"][0]["scores"].update(clarity=True)),
        m("null score", lambda d: d["quality_assessments"][0]["scores"].update(clarity=None)),
        m("non-string reason", lambda d: d["quality_assessments"][0]["reasons"].update(clarity=1)),
        m("section not a list", lambda d: d.update(issues={})),
        m("item not an object", lambda d: d["requirements"].append("x")),
        m("id list item bad", lambda d: d["requirements"][2].update(depends_on=["fr-1"])),
        m("permissions blank", lambda d: d["stakeholders"][0].update(permissions=[""])),
        # Not expressible in a schema: both should accept the structure.
        m("broken reference", lambda d: d["requirements"][2].update(depends_on=["FR-404"])),
        m("duplicate id", lambda d: d["requirements"][2].update(id="FR-001")),
    ]


class SchemaFileTest(unittest.TestCase):
    def test_file_matches_model(self):
        with open(SCHEMA_PATH, encoding="utf-8") as fh:
            on_disk = json.load(fh)
        self.assertEqual(on_disk, json_schema(),
                         f"schemas/requirements.schema.json is out of date; run: {REGENERATE}")

    def test_file_text_is_canonical(self):
        # Universal newlines: a checkout with core.autocrlf=true still passes.
        with open(SCHEMA_PATH, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), model.schema_text(), f"run: {REGENERATE}")

    def test_dialect_and_defs(self):
        schema = json_schema()
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        for section in model.LIST_SECTIONS:
            ref = schema["properties"][section]["items"]["$ref"]
            self.assertIn(ref.split("/")[-1], schema["$defs"])

    def test_every_model_field_is_in_schema(self):
        defs = json_schema()["$defs"]
        tables = dict(model.LIST_SECTIONS, project=model.PROJECT_FIELDS)
        for section, fields in tables.items():
            target = defs[model._SECTION_DEFS[section]]
            self.assertEqual(set(target["properties"]), set(fields), section)
            self.assertEqual(set(target["required"]),
                             {n for n, f in fields.items() if f.required}, section)


class SchemaBehaviourTest(unittest.TestCase):
    def test_fixtures_agree(self):
        for name in sorted(os.listdir(os.path.join(ROOT, "tests", "fixtures"))):
            if not name.endswith(".json") or name == "invalid_json.json":
                continue
            doc = load_fixture(name)
            with self.subTest(fixture=name):
                self.assertEqual(bool(schema_errors(doc, json_schema())), model_rejects(doc),
                                 schema_errors(doc, json_schema()))

    def test_mutations_agree(self):
        schema = json_schema()
        for label, doc in _mutations():
            with self.subTest(case=label):
                self.assertEqual(bool(schema_errors(doc, schema)), model_rejects(doc),
                                 schema_errors(doc, schema))

    def test_mutations_cover_both_outcomes(self):
        results = {model_rejects(doc) for _, doc in _mutations()}
        self.assertEqual(results, {True, False})


try:
    import jsonschema  # optional, only if the developer already has it
except ImportError:  # pragma: no cover - the normal, zero-install case
    jsonschema = None


@unittest.skipIf(jsonschema is None, "jsonschema not installed (optional)")
class ExternalValidatorTest(unittest.TestCase):
    def test_schema_is_valid_and_agrees(self):
        schema = json_schema()
        validator_cls = jsonschema.Draft202012Validator
        validator_cls.check_schema(schema)
        validator = validator_cls(schema)
        for label, doc in _mutations():
            with self.subTest(case=label):
                self.assertEqual(not validator.is_valid(doc), model_rejects(doc))


if __name__ == "__main__":
    unittest.main()
