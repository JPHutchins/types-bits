"""Rust-style sized integer types.

``__init__.pyi`` shadows this module for type checkers; this is the runtime tier.
"""

from types_bits._spec import MAX_BITS

__all__ = [  # pyright: ignore[reportUnsupportedDunderAll]
    f"{prefix}{bits}" for prefix in ("u", "i") for bits in range(1, MAX_BITS + 1)
]


def __getattr__(name: str) -> object:
    if name not in __all__:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)

    from typing import Annotated

    from annotated_types import Ge, Le

    from types_bits._generate import Signed, Unsigned

    width = Unsigned(int(name[1:])) if name[0] == "u" else Signed(int(name[1:]))
    return Annotated[int, Ge(width.lo), Le(width.hi)]
