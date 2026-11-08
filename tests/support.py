"""Shared test helpers: puts scripts/ on sys.path and loads fixtures.

Works with ``python -m unittest discover -s tests`` and with pytest.
"""

import copy
import json
import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TESTS_DIR)
SCRIPTS_DIR = os.path.join(ROOT, "scripts")
FIXTURES_DIR = os.path.join(TESTS_DIR, "fixtures")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


def fixture_path(name):
    return os.path.join(FIXTURES_DIR, name)


def load_fixture(name):
    """A fresh (deep-copied) parsed fixture, safe to mutate."""
    with open(fixture_path(name), encoding="utf-8") as fh:
        return copy.deepcopy(json.load(fh))


def codes(findings, level=None):
    """Sorted list of finding codes, optionally only one level."""
    return sorted(f.code for f in findings if level is None or f.level == level)


def errors(findings):
    return [f for f in findings if f.level == "error"]
