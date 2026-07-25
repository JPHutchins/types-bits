"""Must type check clean on every checker, with no suppressions.

Also the intended usage pattern: guarded import, deferred annotations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types_bits import i4, u2, u4, u8, u10


def in_range() -> None:
    lo: u4 = 0
    hi: u4 = 15
    mid: u4 = 7
    print(lo, hi, mid)


def signed_in_range() -> None:
    lo: i4 = -8
    hi: i4 = 7
    print(lo, hi)


def widest() -> None:
    top: u10 = 1023
    print(top)


def narrow_widens(value: u2) -> u4:
    """Widen for free: a narrower width is a subtype of a wider one."""
    return value


def widens_to_int(value: u8) -> int:
    return value


def exhaustive(value: u2) -> str:
    """No wildcard arm: a checker that cannot prove ``u2`` closed sees a missing return."""
    match value:
        case 0:
            return "zero"
        case 1:
            return "one"
        case 2:
            return "two"
        case 3:
            return "three"


def literal_arg() -> None:
    print(narrow_widens(3))
