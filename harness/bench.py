"""Time every checker as the literal count grows."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal, NamedTuple

from harness.checkers import CHECKERS, run, version
from types_bits._generate import VARIANTS, Unsigned, alias, module, widths
from types_bits._spec import MAX_BITS

if TYPE_CHECKING:
    from collections.abc import Sequence

    from harness.checkers import Checker
    from types_bits._generate import Variant

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "bench" / ".work"
RESULTS = ROOT / "bench" / "results"
FIXTURE = ROOT / "fixtures" / "accept.py"

SWEEP_BITS: Final = (8, 10, 12, 14, 16)
FULL_BITS: Final = (4, 6, 8, 10, 12, 14, 16)
SWEEP_VARIANTS: Final[tuple[Variant, ...]] = ("opaque", "flat")
TIMEOUT: Final = 180.0


class Sample(NamedTuple):
    checker: str
    variant: str
    bits: int
    members: int
    seconds: float | None
    errors: int

    @property
    def cell(self) -> str:
        if self.seconds is None:
            return "timeout"
        return f"{self.seconds:.2f}" + ("" if self.errors == 0 else f" ({self.errors}e)")


def probe(bits: int, variant: Variant) -> str:
    selected = widths(bits, "u")
    pins = "\n".join(f"v{w.bits}: {w.name} = {w.hi}" for w in selected)
    widens = "\n\n".join(
        f"def widen{wide.bits}(value: {narrow.name}) -> {wide.name}:\n    return value"
        for narrow, wide in pairwise(selected)
    )
    return f"{module(bits, variant, 'u')}\n{pins}\n\n{widens}\n"


type Shape = Literal["declare", "assign1", "assign10", "widen1", "widen10"]
SHAPES: Final[tuple[Shape, ...]] = ("declare", "assign1", "assign10", "widen1", "widen10")
SHAPE_BITS: Final = (10, 16)
SHAPE_VARIANTS: Final[tuple[Variant, ...]] = ("flat", "opaque")


def shape_probe(bits: int, shape: Shape, variant: Variant) -> str:
    """Isolate the marginal cost of *using* a width from the fixed cost of declaring it.

    Both aliases are declared in every shape, so the delta between shapes is use cost
    and nothing else.
    """
    narrow, wide = Unsigned(bits - 1), Unsigned(bits)
    imports = "from typing import Literal\n" if variant == "flat" else ""
    decls = f"{imports}\n{alias(narrow, variant)}\n{alias(wide, variant)}\n"

    def assigns(count: int) -> str:
        return "\n".join(f"a{i}: {wide.name} = {i}" for i in range(count))

    def widens(count: int) -> str:
        return "\n\n".join(
            f"def w{i}(v: {narrow.name}) -> {wide.name}:\n    return v" for i in range(count)
        )

    match shape:
        case "declare":
            return decls
        case "assign1":
            return f"{decls}\n{assigns(1)}\n"
        case "assign10":
            return f"{decls}\n{assigns(10)}\n"
        case "widen1":
            return f"{decls}\n{widens(1)}\n"
        case "widen10":
            return f"{decls}\n{widens(10)}\n"


def write_shape_probe(bits: int, shape: Shape, variant: Variant) -> Path:
    WORK.mkdir(parents=True, exist_ok=True)
    path = WORK / f"shape_{variant}_{bits:02d}_{shape}.py"
    path.write_text(shape_probe(bits, shape, variant), encoding="utf-8")
    return path


def shapes(checkers: Sequence[Checker], repeat: int) -> dict[str, tuple[Sample, ...]]:
    return {
        f"{variant} u{bits - 1} + u{bits} declared, varying uses": tuple(
            measure(checker, write_shape_probe(bits, shape, variant), shape, bits, 2**bits, repeat)
            for shape in SHAPES
            for checker in checkers
        )
        for variant in SHAPE_VARIANTS
        for bits in SHAPE_BITS
    }


def shape_table(samples: Sequence[Sample], checkers: Sequence[Checker]) -> str:
    names = [checker.name for checker in checkers]
    rows = (
        f"| {shape} | "
        + " | ".join(
            next((s.cell for s in samples if s.variant == shape and s.checker == name), "-")
            for name in names
        )
        + " |"
        for shape in SHAPES
    )
    return "\n".join((f"| uses | {' | '.join(names)} |", f"|---|{'---:|' * len(names)}", *rows))


def write_probe(bits: int, variant: Variant) -> Path:
    WORK.mkdir(parents=True, exist_ok=True)
    path = WORK / f"{variant}_{bits:02d}.py"
    path.write_text(probe(bits, variant), encoding="utf-8")
    return path


def measure(
    checker: Checker, target: Path, variant: str, bits: int, members: int, repeat: int
) -> Sample:
    outcomes = [run(checker, [target], cwd=ROOT, cold=True, timeout=TIMEOUT) for _ in range(repeat)]
    timings = [outcome.seconds for outcome in outcomes if not outcome.timed_out]
    return Sample(
        checker.name,
        variant,
        bits,
        members,
        min(timings) if timings else None,
        max(len(outcome.errors) for outcome in outcomes),
    )


def sweep(
    checkers: Sequence[Checker], bit_widths: Sequence[int], variants: Sequence[Variant], repeat: int
) -> tuple[Sample, ...]:
    return tuple(
        measure(checker, write_probe(bits, variant), variant, bits, 2**bits, repeat)
        for variant in variants
        for bits in bit_widths
        for checker in checkers
    )


def library(checkers: Sequence[Checker], repeat: int) -> tuple[Sample, ...]:
    return tuple(
        measure(checker, FIXTURE, "library", MAX_BITS, 2 ** (MAX_BITS + 1) - 2, repeat)
        for checker in checkers
    )


def table(samples: Sequence[Sample], checkers: Sequence[Checker]) -> str:
    names = [checker.name for checker in checkers]
    by_bits = {sample.bits: sample.members for sample in samples}
    rows = (
        f"| {bits} | {by_bits[bits]:,} | "
        + " | ".join(
            next(
                (s.cell for s in samples if s.bits == bits and s.checker == name),
                "-",
            )
            for name in names
        )
        + " |"
        for bits in sorted(by_bits)
    )
    return "\n".join(
        (
            f"| bits | members | {' | '.join(names)} |",
            f"|---:|---:|{'---:|' * len(names)}",
            *rows,
        )
    )


def render(samples: Sequence[Sample], checkers: Sequence[Checker]) -> str:
    if samples and samples[0].variant in SHAPES:
        return shape_table(samples, checkers)
    return table(samples, checkers)


def report(grouped: dict[str, tuple[Sample, ...]], checkers: Sequence[Checker]) -> str:
    sections = (f"### {label}\n\n{render(samples, checkers)}" for label, samples in grouped.items())
    versions = "\n".join(f"- {c.name}: {version(c)}" for c in checkers)
    return (
        f"# Type checker cost of exhaustive integer literals\n\n"
        f"Python {platform.python_version()} on {platform.platform(terse=True)}\n\n"
        f"{versions}\n\nSeconds, best of repeats, cold. `(Ne)` marks unexpected diagnostics.\n\n"
        + "\n\n".join(sections)
        + "\n"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m harness.bench", description=__doc__)
    parser.add_argument("--full", action="store_true", help="every variant, up to 16 bits")
    parser.add_argument("--shapes", action="store_true", help="fixed vs marginal cost of one width")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--out", type=Path, default=RESULTS / "bench.json")
    args = parser.parse_args(argv)

    repeat: int = args.repeat
    checkers = tuple(checker for checker in CHECKERS if checker.available)
    bit_widths = FULL_BITS if args.full else SWEEP_BITS
    variants: tuple[Variant, ...] = VARIANTS if args.full else SWEEP_VARIANTS

    if args.shapes:
        grouped = shapes(checkers, repeat)
    else:
        grouped = {
            f"variant={variant} (u1..uN, one use per alias)": sweep(
                checkers, bit_widths, (variant,), repeat
            )
            for variant in variants
        }
        grouped["shipped library (u1..u10 and i1..i10 via the real stub)"] = library(
            checkers, repeat
        )

    rendered = report(grouped, checkers)
    print(rendered)

    out: Path = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "python": platform.python_version(),
                "platform": platform.platform(terse=True),
                "versions": {c.name: version(c) for c in checkers},
                "samples": [s._asdict() for group in grouped.values() for s in group],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    out.with_suffix(".md").write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
