"""Every checker must flag exactly the statements carrying a trailing ``# E`` comment.

``tests/test_checkers.py`` reads those markers and asserts against them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types_bits import i4, u2, u4, u8


def _above_max() -> None:
    value: u4 = 16  # E: 16 does not fit in 4 unsigned bits


def _negative_unsigned() -> None:
    value: u4 = -1  # E: unsigned cannot be negative


def _signed_above_max() -> None:
    value: i4 = 8  # E: i4 tops out at 7


def _signed_below_min() -> None:
    value: i4 = -9  # E: i4 bottoms out at -8


def _wide_into_narrow(value: u4) -> u2:
    return value  # E: u4 is not a subtype of u2


def _plain_int_into_width(value: int) -> u8:
    return value  # E: an unbounded int is not a u8


def _arithmetic_is_not_closed(a: u4, b: u4) -> None:
    total: u4 = a + b  # E: addition widens to int; the range is not preserved


def _unknown_width() -> None:
    from types_bits import u11  # E: only u1..u10 are materialized

    print(u11)
