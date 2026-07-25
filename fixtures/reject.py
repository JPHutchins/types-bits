"""Every checker must flag exactly the statements carrying a trailing ``# E`` comment.

``tests/test_checkers.py`` reads those markers and asserts against them. Every name here
is public and consumed, so that no unused-symbol diagnostic can stand in for the bound
violation the statement exists to prove.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types_bits import i4, u2, u4, u8

above_max: u4 = 16  # E: 16 does not fit in 4 unsigned bits
negative_unsigned: u4 = -1  # E: unsigned cannot be negative
signed_above_max: i4 = 8  # E: i4 tops out at 7
signed_below_min: i4 = -9  # E: i4 bottoms out at -8


def wide_into_narrow(value: u4) -> u2:
    return value  # E: u4 is not a subtype of u2


def plain_int_into_width(value: int) -> u8:
    return value  # E: an unbounded int is not a u8


def arithmetic_is_not_closed(a: u4, b: u4) -> u4:
    return a + b  # E: addition widens to int; the range is not preserved
