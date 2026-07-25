"""Materialize the stub before anything reads it."""

from __future__ import annotations

from pathlib import Path

import pytest

from types_bits._generate import write

ROOT = Path(__file__).resolve().parent.parent
STUB = ROOT / "src" / "types_bits" / "__init__.pyi"


@pytest.fixture(scope="session", autouse=True)
def materialize_stub() -> Path:
    return write(STUB)
