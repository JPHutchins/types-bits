"""One interface over six type checkers and their four diagnostic formats."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from typing import TYPE_CHECKING, Final, Literal, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

type DiagFormat = Literal["mypy-json", "pyright-json", "pyrefly-json", "concise"]


class Diagnostic(NamedTuple):
    file: str
    line: int
    severity: str
    code: str
    message: str


class Checker(NamedTuple):
    name: str
    argv: tuple[str, ...]
    fmt: DiagFormat
    caches: tuple[str, ...] = ()

    @property
    def available(self) -> bool:
        return shutil.which(self.argv[0]) is not None


CHECKERS: Final[tuple[Checker, ...]] = (
    Checker(
        "mypy", ("mypy", "-O", "json", "--no-incremental", f"--cache-dir={os.devnull}"), "mypy-json"
    ),
    Checker("pyright", ("pyright", "--outputjson"), "pyright-json"),
    Checker("basedpyright", ("basedpyright", "--outputjson"), "pyright-json"),
    Checker("ty", ("ty", "check", "--output-format=concise"), "concise"),
    Checker("pyrefly", ("pyrefly", "check", "--output-format=json"), "pyrefly-json"),
    Checker("zuban", ("zuban", "check"), "concise"),
)

BY_NAME: Final = {checker.name: checker for checker in CHECKERS}

_CONCISE: Final = re.compile(
    r"^(?P<file>[^\s:][^:]*):(?P<line>\d+):(?:\d+:)?\s*"
    r"(?P<severity>error|warning|note|info)"
    r"(?:\[(?P<code>[\w-]+)\])?:?\s*(?P<message>.*)$"
)
_TRAILING_CODE: Final = re.compile(r"\[(?P<code>[\w-]+)\]\s*$")
_ANSI: Final = re.compile(r"\x1b\[[0-9;]*m")
PLAIN: Final = {"NO_COLOR": "1", "FORCE_COLOR": "0", "CLICOLOR": "0", "CLICOLOR_FORCE": "0"}


class Outcome(NamedTuple):
    checker: str
    returncode: int
    seconds: float
    diagnostics: tuple[Diagnostic, ...]
    raw: str
    timed_out: bool = False

    @property
    def errors(self) -> tuple[Diagnostic, ...]:
        return tuple(diag for diag in self.diagnostics if diag.severity == "error")

    @property
    def error_lines(self) -> frozenset[int]:
        return frozenset(diag.line for diag in self.errors)


def _from_mypy(stdout: str) -> Iterable[Diagnostic]:
    for line in stdout.splitlines():
        if not line.startswith("{"):
            continue
        raw = json.loads(line)
        yield Diagnostic(
            raw["file"], raw["line"], raw["severity"], raw["code"] or "", raw["message"]
        )


def _from_pyright(stdout: str) -> Iterable[Diagnostic]:
    for raw in json.loads(stdout)["generalDiagnostics"]:
        yield Diagnostic(
            raw["file"],
            raw["range"]["start"]["line"] + 1,
            raw["severity"],
            raw.get("rule", ""),
            raw["message"],
        )


def _from_pyrefly(stdout: str) -> Iterable[Diagnostic]:
    for raw in json.loads(stdout)["errors"]:
        yield Diagnostic(
            raw["path"], raw["line"], raw["severity"], raw["name"], raw["concise_description"]
        )


def _from_concise(text: str) -> Iterable[Diagnostic]:
    for line in _ANSI.sub("", text).splitlines():
        found = _CONCISE.match(line)
        if found is None:
            continue
        message = found["message"]
        trailing = _TRAILING_CODE.search(message)
        yield Diagnostic(
            found["file"],
            int(found["line"]),
            found["severity"],
            found["code"] or (trailing["code"] if trailing else ""),
            message,
        )


def parse(fmt: DiagFormat, stdout: str, stderr: str) -> tuple[Diagnostic, ...]:
    match fmt:
        case "mypy-json":
            return tuple(_from_mypy(stdout))
        case "pyright-json":
            return tuple(_from_pyright(stdout))
        case "pyrefly-json":
            return tuple(_from_pyrefly(stdout))
        case "concise":
            return tuple(_from_concise(f"{stdout}\n{stderr}"))


def run(
    checker: Checker,
    targets: Sequence[Path | str],
    *,
    cwd: Path,
    cold: bool = True,
    timeout: float | None = None,
    extra: Sequence[str] = (),
) -> Outcome:
    if cold:
        for cache in checker.caches:
            shutil.rmtree(cwd / cache, ignore_errors=True)

    start = time.perf_counter()
    try:
        proc = subprocess.run(  # noqa: S603
            (*checker.argv, *extra, *(str(target) for target in targets)),
            cwd=cwd,
            env={**os.environ, **PLAIN},
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return Outcome(checker.name, -1, timeout or 0.0, (), "timed out", timed_out=True)
    seconds = time.perf_counter() - start

    return Outcome(
        checker.name,
        proc.returncode,
        seconds,
        parse(checker.fmt, proc.stdout, proc.stderr),
        f"{proc.stdout}\n{proc.stderr}".strip(),
    )


def version(checker: Checker) -> str:
    proc = subprocess.run(  # noqa: S603
        (checker.argv[0], "--version"), capture_output=True, text=True, check=False
    )
    return proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else "unknown"
