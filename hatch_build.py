"""Materialize ``types_bits/__init__.pyi`` into every built artifact."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

SRC = Path(__file__).parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class MaterializeStubs(BuildHookInterface[Any]):
    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:  # noqa: ARG002
        from types_bits._generate import write

        stub = write(SRC / "types_bits" / "__init__.pyi")
        build_data.setdefault("artifacts", []).append(f"/{stub.relative_to(SRC.parent).as_posix()}")
