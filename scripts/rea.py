#!/usr/bin/env python3
"""rea: command-line tool of the Requirements Engineering Assistant skill.

Commands:
  init      create an empty, valid requirements.json
  scan      flag vague words in a free-text description (e.g. input.md)
  validate  check structure, IDs, references, dependency cycles, origin rules
  lint      validation + quality warnings + hints + quality scores
  export    generate requirements.md (refuses if the JSON is invalid)

Exit codes: 0 OK, 1 validation errors, 2 usage or file errors.
Standard library only; Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, TextIO

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reqkit import __version__  # noqa: E402
from reqkit.checks import lint as lint_document  # noqa: E402
from reqkit.checks import scan_text  # noqa: E402
from reqkit.model import MODES, Finding, has_errors, load_document, new_document, validate  # noqa: E402
from reqkit.quality import QualityReport, assess  # noqa: E402
from reqkit.render import render_markdown  # noqa: E402

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_USAGE = 2

DEFAULT_FILE = "requirements.json"
MARKDOWN_NAME = "requirements.md"
LEVELS = ("error", "warning", "hint")


class FileProblem(Exception):
    """A file could not be read or written (exit code 2)."""


# --- Output helpers -----------------------------------------------------------


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def _counts(findings: Sequence[Finding]) -> Dict[str, int]:
    return {level: sum(1 for f in findings if f.level == level) for level in LEVELS}


def _summary(counts: Dict[str, int], levels: Sequence[str] = LEVELS) -> str:
    return ", ".join(_plural(counts[level], level) for level in levels)


def _print_findings(findings: Sequence[Finding], out: TextIO) -> None:
    ordered = sorted(findings, key=lambda f: LEVELS.index(f.level) if f.level in LEVELS else len(LEVELS))
    for f in ordered:
        print(f"  {f.level:<7}  [{f.code}] {f.path}: {f.message}", file=out)


def _print_json(data: Dict[str, Any], out: TextIO) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False), file=out)


def _fail(message: str, err: TextIO) -> int:
    print(f"rea: error: {message}", file=err)
    return EXIT_USAGE


# --- File helpers -------------------------------------------------------------


def _load(path: str) -> tuple:
    """(doc, findings) or FileProblem for unreadable files."""
    if os.path.isdir(path):
        raise FileProblem(f"{path} is a directory, expected a JSON file")
    try:
        return load_document(path)
    except FileNotFoundError:
        raise FileProblem(f"file not found: {path}") from None
    except UnicodeDecodeError:
        raise FileProblem(f"{path} is not UTF-8 text") from None
    except OSError as exc:
        raise FileProblem(f"cannot read {path}: {exc.strerror or exc}") from None


def _read_text(path: str) -> str:
    try:
        if path == "-":
            return sys.stdin.read()
        if os.path.isdir(path):
            raise FileProblem(f"{path} is a directory, expected a text file")
        with open(path, "r", encoding="utf-8-sig") as fh:
            return fh.read()
    except FileNotFoundError:
        raise FileProblem(f"file not found: {path}") from None
    except UnicodeDecodeError:
        raise FileProblem(f"{path} is not UTF-8 text") from None
    except OSError as exc:
        raise FileProblem(f"cannot read {path}: {exc.strerror or exc}") from None


def _write_text(path: str, text: str) -> None:
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    except OSError as exc:
        raise FileProblem(f"cannot write {path}: {exc.strerror or exc}") from None


# --- Commands -----------------------------------------------------------------


def cmd_init(args: argparse.Namespace, out: TextIO, err: TextIO) -> int:
    path = args.out
    if os.path.exists(path) and not args.force:
        return _fail(f"{path} already exists (use --force to overwrite)", err)
    try:
        doc = new_document(args.name, mode=args.mode, overview=args.overview)
    except ValueError as exc:
        return _fail(str(exc), err)
    parent = os.path.dirname(os.path.abspath(path))
    if not os.path.isdir(parent):
        return _fail(f"directory does not exist: {parent}", err)
    _write_text(path, json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    if args.json:
        _print_json({"command": "init", "file": path, "created": True}, out)
    else:
        print(f"Created {path} for project '{args.name}' ({args.mode} mode).", file=out)
    return EXIT_OK


def cmd_scan(args: argparse.Namespace, out: TextIO, err: TextIO) -> int:
    results = scan_text(_read_text(args.file))
    name = "<stdin>" if args.file == "-" else args.file
    if args.json:
        _print_json({"command": "scan", "file": name, "count": len(results), "matches": results}, out)
        return EXIT_OK
    if not results:
        print(f"{name}: no vague words or weak phrases found.", file=out)
        return EXIT_OK
    print(f"{name}: {_plural(len(results), 'vague word or weak phrase')} found", file=out)
    for r in results:
        print(f"  line {r['line']}, col {r['column']}: '{r['term']}' ({r['kind']}) - {r['missing']}", file=out)
        print(f"      {r['context']}", file=out)
    print("These are candidates: ask the user for measurable values where they matter.", file=out)
    return EXIT_OK


def cmd_validate(args: argparse.Namespace, out: TextIO, err: TextIO) -> int:
    doc, findings = _load(args.file)
    if doc is not None:
        findings = validate(doc)
    counts = _counts(findings)
    valid = counts["error"] == 0
    if args.json:
        _print_json({"command": "validate", "file": args.file, "valid": valid,
                     "counts": counts, "findings": [f.as_dict() for f in findings]}, out)
    else:
        status = "valid" if valid else "INVALID"
        print(f"{args.file}: {status} ({_summary(counts, ('error', 'warning'))})", file=out)
        _print_findings(findings, out)
    return EXIT_OK if valid else EXIT_INVALID


def _print_quality(report: QualityReport, out: TextIO) -> None:
    if not report.requirements:
        print("Quality: no requirements to score yet.", file=out)
        return
    percent = "n/a" if report.percent is None else f"{report.percent:.1f}%"
    print(f"Quality: {percent} ({report.points}/{report.max_points} applicable points, "
          f"{_plural(len(report.requirements), 'requirement')})", file=out)
    weak = report.needs_improvement
    if weak:
        print("Needs improvement:", file=out)
        for r in weak:
            pct = "n/a" if r.percent is None else f"{r.percent:.0f}%"
            details = ", ".join(f"{c} {r.scores[c].value}/2" for c in r.weak)
            print(f"  {r.requirement_id:<9} {pct:>4}  {details}", file=out)
    pending = report.not_assessed
    if pending:
        print("Not yet scored by the agent:", file=out)
        for r in pending:
            print(f"  {r.requirement_id:<9} {', '.join(r.not_assessed)}", file=out)


def cmd_lint(args: argparse.Namespace, out: TextIO, err: TextIO) -> int:
    doc, findings = _load(args.file)
    report: Optional[QualityReport] = None
    if doc is not None:
        findings = validate(doc)
        if not has_errors(findings):
            findings = findings + lint_document(doc)
            report = assess(doc)
    counts = _counts(findings)
    valid = counts["error"] == 0
    if args.json:
        _print_json({"command": "lint", "file": args.file, "valid": valid, "counts": counts,
                     "findings": [f.as_dict() for f in findings],
                     "quality": report.as_dict() if report is not None else None}, out)
        return EXIT_OK if valid else EXIT_INVALID
    status = "valid" if valid else "INVALID"
    print(f"{args.file}: {status} ({_summary(counts)})", file=out)
    _print_findings(findings, out)
    if report is None:
        print("Quality checks and scores skipped: fix the errors first.", file=out)
        return EXIT_INVALID
    if counts["warning"] or counts["hint"]:
        print("Warnings and hints are candidates: confirm real problems as issues, dismiss the rest.",
              file=out)
    _print_quality(report, out)
    return EXIT_OK


def cmd_export(args: argparse.Namespace, out: TextIO, err: TextIO) -> int:
    doc, findings = _load(args.file)
    if doc is not None:
        findings = validate(doc)
    if has_errors(findings):
        if args.json:
            _print_json({"command": "export", "file": args.file, "exported": False, "output": None,
                         "counts": _counts(findings),
                         "findings": [f.as_dict() for f in findings if f.level == "error"]}, out)
        else:
            errors = [f for f in findings if f.level == "error"]
            print(f"{args.file}: not exported, {_plural(len(errors), 'validation error')}", file=out)
            _print_findings(errors, out)
        return EXIT_INVALID
    out_dir = args.out if args.out is not None else (os.path.dirname(args.file) or ".")
    if not os.path.isdir(out_dir):
        return _fail(f"output directory does not exist: {out_dir}", err)
    target = os.path.join(out_dir, MARKDOWN_NAME)
    _write_text(target, render_markdown(doc))
    if args.json:
        _print_json({"command": "export", "file": args.file, "exported": True, "output": target,
                     "counts": _counts(findings), "findings": [f.as_dict() for f in findings]}, out)
    else:
        print(f"Wrote {target}", file=out)
        if findings:
            print(f"Note: {_plural(len(findings), 'validation warning')} (run 'validate' for details).",
                  file=out)
    return EXIT_OK


# --- Argument parsing ---------------------------------------------------------


class _Parser(argparse.ArgumentParser):
    """ArgumentParser that writes help and errors to the streams given to ``main``."""

    out_stream: Optional[TextIO] = None
    err_stream: Optional[TextIO] = None

    def _print_message(self, message: str, file: Optional[TextIO] = None) -> None:
        if not message:
            return
        if file is sys.stdout and self.out_stream is not None:
            file = self.out_stream
        elif file is not sys.stdout and self.err_stream is not None:
            file = self.err_stream
        (file or sys.stderr).write(message)


def build_parser(out: Optional[TextIO] = None, err: Optional[TextIO] = None) -> argparse.ArgumentParser:
    parser = _Parser(prog="rea.py", description="Requirements Engineering Assistant: validate, lint, "
                     "score and export requirements.json.",
                     epilog="Exit codes: 0 OK, 1 validation errors, 2 usage or file errors.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND", parser_class=_Parser)
    sub.required = True

    def json_flag(p: argparse.ArgumentParser) -> None:
        p.add_argument("--json", action="store_true", help="machine-readable JSON output")

    p = sub.add_parser("init", help="create an empty, valid requirements.json")
    p.add_argument("--name", required=True, help="project name")
    p.add_argument("--mode", choices=MODES, default="interactive", help="workflow mode (default: interactive)")
    p.add_argument("--overview", default="", help="one-paragraph project overview")
    p.add_argument("--out", default=DEFAULT_FILE, help=f"file to create (default: {DEFAULT_FILE})")
    p.add_argument("--force", action="store_true", help="overwrite an existing file")
    json_flag(p)
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("scan", help="flag vague words in a free-text description")
    p.add_argument("file", help="text or Markdown file, or '-' for standard input")
    json_flag(p)
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("validate", help="check structure, IDs, references and origin rules")
    p.add_argument("file", help="requirements.json")
    json_flag(p)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("lint", help="validation + quality warnings, hints and scores")
    p.add_argument("file", help="requirements.json")
    json_flag(p)
    p.set_defaults(func=cmd_lint)

    p = sub.add_parser("export", help=f"generate {MARKDOWN_NAME} (refuses if the JSON is invalid)")
    p.add_argument("file", help="requirements.json")
    p.add_argument("--out", help="output directory (default: the JSON file's directory)")
    json_flag(p)
    p.set_defaults(func=cmd_export)

    for p in [parser, *sub.choices.values()]:
        p.out_stream, p.err_stream = out, err  # type: ignore[attr-defined]
    return parser


def main(argv: Optional[List[str]] = None, out: Optional[TextIO] = None, err: Optional[TextIO] = None) -> int:
    out = out if out is not None else sys.stdout
    err = err if err is not None else sys.stderr
    parser = build_parser(out, err)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # --help / --version (0) or usage error (2)
        return exc.code if isinstance(exc.code, int) else EXIT_USAGE
    try:
        return args.func(args, out, err)
    except FileProblem as exc:
        return _fail(str(exc), err)


def _utf8_console() -> None:
    """Write UTF-8 on every platform (the Windows console and pipes default to a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass


if __name__ == "__main__":
    _utf8_console()
    sys.exit(main())
