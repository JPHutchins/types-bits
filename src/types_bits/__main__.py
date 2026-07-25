"""``python -m types_bits`` -- materialize a stub."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import TYPE_CHECKING, cast

from types_bits._generate import KINDS, VARIANTS, write
from types_bits._spec import MAX_BITS

if TYPE_CHECKING:
    from collections.abc import Sequence

    from types_bits._generate import Kind, Variant

DEFAULT_OUT = Path(__file__).with_name("__init__.pyi")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m types_bits", description=__doc__)
    parser.add_argument("--bits", type=int, default=MAX_BITS)
    parser.add_argument("--variant", choices=VARIANTS, default="flat")
    parser.add_argument("--kind", choices=KINDS, default="both")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    path = write(
        cast("Path", args.out),
        cast("int", args.bits),
        cast("Variant", args.variant),
        cast("Kind", args.kind),
    )
    print(f"wrote {path} ({path.stat().st_size:,} bytes)")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
