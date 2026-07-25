"""Drive the real checkers over the fixtures.

Diagnostics are attributed per top-level statement, not per line: ty anchors a
return-type error on the ``def`` and the rest on the ``return``.
"""

from __future__ import annotations

import ast
import tokenize
from pathlib import Path

import pytest

from harness.checkers import CHECKERS, Checker, run

ROOT = Path(__file__).resolve().parent.parent
ACCEPT = ROOT / "fixtures" / "accept.py"
REJECT = ROOT / "fixtures" / "reject.py"

MARKER = "# E:"


def blocks(path: Path) -> tuple[range, ...]:
    return tuple(
        range(node.lineno, (node.end_lineno or node.lineno) + 1)
        for node in ast.parse(path.read_text(encoding="utf-8")).body
    )


def block_of(line: int, spans: tuple[range, ...]) -> range | None:
    return next((span for span in spans if line in span), None)


def marked_lines(path: Path) -> tuple[int, ...]:
    """Real comments only -- a docstring is free to mention the marker."""
    with path.open(encoding="utf-8") as handle:
        return tuple(
            token.start[0]
            for token in tokenize.generate_tokens(handle.readline)
            if token.type == tokenize.COMMENT and token.string.startswith(MARKER)
        )


def marked_blocks(path: Path, spans: tuple[range, ...]) -> frozenset[range]:
    return frozenset(
        span for line in marked_lines(path) for span in [block_of(line, spans)] if span is not None
    )


def diagnosed_blocks(lines: frozenset[int], spans: tuple[range, ...]) -> frozenset[range]:
    return frozenset(span for line in lines for span in [block_of(line, spans)] if span is not None)


def describe(spans: frozenset[range]) -> list[int]:
    return sorted(span.start for span in spans)


@pytest.mark.checker
@pytest.mark.parametrize("checker", CHECKERS, ids=lambda checker: checker.name)
def test_accepts_valid_widths(checker: Checker) -> None:
    if not checker.available:
        pytest.skip(f"{checker.name} is not installed")
    outcome = run(checker, [ACCEPT], cwd=ROOT)
    assert outcome.errors == (), outcome.raw


@pytest.mark.checker
@pytest.mark.parametrize("checker", CHECKERS, ids=lambda checker: checker.name)
def test_rejects_exactly_the_marked_blocks(checker: Checker) -> None:
    if not checker.available:
        pytest.skip(f"{checker.name} is not installed")
    spans = blocks(REJECT)
    outcome = run(checker, [REJECT], cwd=ROOT)
    diagnosed = describe(diagnosed_blocks(outcome.error_lines, spans))
    expected = describe(marked_blocks(REJECT, spans))
    assert diagnosed == expected, (
        f"{checker.name} flagged blocks at {diagnosed}, expected {expected}\n"
        f"error lines: {sorted(outcome.error_lines)}\nrc={outcome.returncode}\n{outcome.raw}"
    )


def test_every_checker_is_installed() -> None:
    """A skipped checker is a silently weaker suite, so name the gap out loud."""
    assert [checker.name for checker in CHECKERS if not checker.available] == []
