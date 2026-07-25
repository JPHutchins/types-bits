"""Properties of the materialized stub, checked without invoking a type checker."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from types_bits._generate import (
    KINDS,
    VARIANTS,
    Kind,
    Signed,
    Unsigned,
    Variant,
    Width,
    added,
    alias,
    members,
    module,
    narrower,
    widths,
)
from types_bits._spec import MAX_BITS

STUB = Path(__file__).resolve().parent.parent / "src" / "types_bits" / "__init__.pyi"

ALL_WIDTHS = widths(MAX_BITS)


def literal_members(source: str, name: str) -> tuple[int, ...]:
    """Read a ``type NAME = Literal[...]`` alias back out of generated source."""
    for node in ast.parse(source).body:
        if not isinstance(node, ast.TypeAlias) or node.name.id != name:
            continue
        subscript = node.value
        assert isinstance(subscript, ast.Subscript)
        evaluated: tuple[int, ...] | int = ast.literal_eval(subscript.slice)
        return evaluated if isinstance(evaluated, tuple) else (evaluated,)
    pytest.fail(f"no alias named {name!r}")


def alias_names(source: str) -> tuple[str, ...]:
    return tuple(node.name.id for node in ast.parse(source).body if isinstance(node, ast.TypeAlias))


@pytest.mark.parametrize("width", ALL_WIDTHS, ids=lambda width: width.name)
def test_cardinality_is_two_to_the_bits(width: Width) -> None:
    assert len(members(width)) == 2**width.bits


@pytest.mark.parametrize("bits", range(1, MAX_BITS + 1))
def test_bounds_are_twos_complement(bits: int) -> None:
    assert (Unsigned(bits).lo, Unsigned(bits).hi) == (0, 2**bits - 1)
    assert (Signed(bits).lo, Signed(bits).hi) == (-(2 ** (bits - 1)), 2 ** (bits - 1) - 1)


@pytest.mark.parametrize("width", ALL_WIDTHS, ids=lambda width: width.name)
def test_narrower_plus_added_partitions_the_width(width: Width) -> None:
    prev = narrower(width)
    previous = frozenset[int]() if prev is None else frozenset(members(prev))
    contributed = frozenset(added(width))
    assert previous.isdisjoint(contributed)
    assert previous | contributed == frozenset(members(width))


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("kind", KINDS)
def test_every_variant_generates_parseable_python(variant: Variant, kind: Kind) -> None:
    source = module(MAX_BITS, variant, kind)
    expected = tuple(width.name for width in widths(MAX_BITS, kind))
    assert alias_names(source) == expected


@pytest.mark.parametrize("width", ALL_WIDTHS, ids=lambda width: width.name)
def test_flat_variant_enumerates_the_whole_range(width: Width) -> None:
    source = module(MAX_BITS, "flat")
    assert literal_members(source, width.name) == tuple(members(width))


def test_nested_and_union_variants_reference_the_narrower_alias() -> None:
    assert alias(Unsigned(4), "nested") == "type u4 = Literal[u3, 8, 9, 10, 11, 12, 13, 14, 15]"
    assert alias(Unsigned(4), "union") == "type u4 = u3 | Literal[8, 9, 10, 11, 12, 13, 14, 15]"


def test_generation_is_deterministic() -> None:
    assert module(MAX_BITS) == module(MAX_BITS)


def test_materialized_stub_matches_the_generator() -> None:
    assert STUB.read_text(encoding="utf-8") == module(MAX_BITS)
