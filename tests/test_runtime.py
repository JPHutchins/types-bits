"""The runtime tier: same names, same bounds, no import cost."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

import types_bits
from types_bits._generate import Width, widths
from types_bits._spec import MAX_BITS

STUB = Path(__file__).resolve().parent.parent / "src" / "types_bits" / "__init__.pyi"
ALL_WIDTHS = widths(MAX_BITS)


def rt(name: str) -> Any:  # noqa: ANN401
    """Reach the runtime tier deliberately: the stub says these names are types, not values."""
    return getattr(types_bits, name)


def modules_after(code: str) -> frozenset[str]:
    program = f"import json, sys\n{code}\nprint(json.dumps(sorted(sys.modules)))"
    proc = subprocess.run(  # noqa: S603
        (sys.executable, "-c", program), capture_output=True, text=True, check=True
    )
    return frozenset(json.loads(proc.stdout))


def test_import_pulls_in_nothing_but_the_constant() -> None:
    assert modules_after("import types_bits") - modules_after("") == {
        "types_bits",
        "types_bits._spec",
    }


def test_the_cost_is_deferred_to_attribute_access() -> None:
    deferred = modules_after("import types_bits\ntypes_bits.u8") - modules_after(
        "import types_bits"
    )
    assert {"typing", "annotated_types"} <= deferred


@pytest.mark.parametrize("width", ALL_WIDTHS, ids=lambda width: width.name)
def test_runtime_bounds_match_the_static_range(width: Width) -> None:
    adapter = TypeAdapter(rt(width.name))
    assert adapter.validate_python(width.lo) == width.lo
    assert adapter.validate_python(width.hi) == width.hi
    with pytest.raises(ValidationError):
        adapter.validate_python(width.lo - 1)
    with pytest.raises(ValidationError):
        adapter.validate_python(width.hi + 1)


def test_unknown_width_is_an_attribute_error() -> None:
    with pytest.raises(AttributeError, match="u11"):
        rt(f"u{MAX_BITS + 1}")


def test_both_tiers_export_the_same_names_in_the_same_order() -> None:
    exported = next(
        ast.literal_eval(node.value)
        for node in ast.parse(STUB.read_text(encoding="utf-8")).body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets)
    )
    assert list(exported) == types_bits.__all__
