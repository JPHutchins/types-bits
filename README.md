# types-bits

`u1`..`u10` and `i1`..`i10` as fully materialized `Literal` unions. Generated `.pyi`, zero
runtime cost, exhaustively checked.

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types_bits import u4

x: u4 = 15  # ok
y: u4 = 16  # error, on every checker
```

`camas` runs the gate; `camas --list` enumerates it. CI fans the same tree out over a
runner axis, with both matrix axes emitted from `tasks.py`. `camas bench` and
`camas bench_shapes` regenerate everything below into `bench/results/`.

## Runtime cost

Zero. The stub is a [PEP 484][pep484] `.pyi` behind `TYPE_CHECKING`. `import types_bits`
loads two modules and no stdlib (`tests/test_runtime.py`). Every number below is
type-checker wall clock, per check run.

## Check cost by width

Seconds, cold, best of one, Python 3.14.1 / WSL2. Encoding `flat`
(`type uN = Literal[0, ..., 2**N-1]`), declaring `u1..uN` and widening each into the next.

| bits | members | mypy | pyright | basedpyright | ty | pyrefly | zuban |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 8 | 256 | 2.30 | 0.68 | 0.71 | 0.08 | 0.32 | 0.10 |
| 10 | 1,024 | 1.98 | 0.75 | 0.83 | 0.09 | 0.38 | 0.12 |
| 12 | 4,096 | 2.22 | 0.79 | 0.85 | 0.11 | 0.31 | 0.33 |
| 14 | 16,384 | 3.10 | 0.59 | 0.64 | 0.17 | 0.27 | 3.23 |
| 16 | 65,536 | 3.85 | 0.70 | 0.79 | 0.41 | 0.46 | 51.26 |

Shipped library (`u1..u10` + `i1..i10`, 2,046 literals): mypy 2.05, basedpyright 1.43,
pyright 1.13, pyrefly 0.24, zuban 0.08, ty 0.06 — matching the `type uN = int` control.

```mermaid
xychart-beta
    title "16 bits, 65,536 literals"
    x-axis [zuban, mypy, basedpyright, pyright, pyrefly, ty]
    y-axis "seconds" 0 --> 55
    bar [51.26, 3.85, 0.79, 0.70, 0.46, 0.41]
```

zuban, same sweep — ~16x per 4x members past 4,096:

```mermaid
xychart-beta
    title "zuban vs literal count"
    x-axis "members" [256, 1024, 4096, 16384, 65536]
    y-axis "seconds" 0 --> 55
    line [0.10, 0.12, 0.33, 3.23, 51.26]
```

The other five, 0–4s axis. Rising line is mypy; flat cluster is pyright, basedpyright,
pyrefly, ty:

```mermaid
xychart-beta
    title "mypy, pyright, basedpyright, pyrefly, ty"
    x-axis "members" [256, 1024, 4096, 16384, 65536]
    y-axis "seconds" 0 --> 4
    line [2.30, 1.98, 2.22, 3.10, 3.85]
    line [0.68, 0.75, 0.79, 0.59, 0.70]
    line [0.71, 0.83, 0.85, 0.64, 0.79]
    line [0.32, 0.38, 0.31, 0.27, 0.46]
    line [0.08, 0.09, 0.11, 0.17, 0.41]
```

## Fixed vs marginal cost

`u(N-1)` and `u(N)` declared in every row; only the use count varies. Italic rows are the
`type uN = int` control.

10 bits — indistinguishable from `int`:

| uses | mypy | pyright | basedpyright | ty | pyrefly | zuban |
|---|---:|---:|---:|---:|---:|---:|
| declared, unused | 1.64 | 0.55 | 0.60 | 0.05 | 0.23 | 0.10 |
| *control* | *1.64* | *0.60* | *0.59* | *0.06* | *0.23* | *0.08* |
| 1 widening | 1.50 | 0.56 | 0.64 | 0.06 | 0.26 | 0.09 |
| 10 widenings | 1.75 | 0.65 | 0.90 | 0.08 | 0.29 | 0.20 |

16 bits — 98,304 literals:

| uses | mypy | pyright | basedpyright | ty | pyrefly | zuban |
|---|---:|---:|---:|---:|---:|---:|
| declared, unused | 2.79 | 0.66 | 0.64 | 0.18 | 0.29 | 0.20 |
| *control* | *1.57* | *0.62* | *0.59* | *0.05* | *0.28* | *0.08* |
| 1 assignment | 2.77 | 0.62 | 0.65 | 0.19 | 0.33 | 0.21 |
| 1 widening | 2.81 | 0.64 | 0.65 | 0.22 | 0.37 | **35.66** |
| 10 widenings | 3.31 | 0.56 | 0.58 | 0.20 | 0.31 | **timeout (>180s)** |

- Declaration: fixed per check run, ~linear in literals (~12 µs/literal on mypy). Not per
  importing file, not per use.
- Assignment: free. Enumerated membership is a hash lookup.
- Widening: free except zuban at width.

## Widening

Cost tracks the *narrow* operand, not the wide one. Wide side fixed at `u16`, one widening:

| narrow | members | zuban | mypy | ty |
|---|---:|---:|---:|---:|
| u1 | 2 | 0.18 | 2.54 | 0.20 |
| u4 | 16 | 0.18 | 2.46 | 0.15 |
| u8 | 256 | 0.16 | 2.67 | 0.21 |
| u12 | 4,096 | 0.76 | 2.50 | 0.17 |
| u15 | 32,768 | 35.21 | 2.80 | 0.18 |

Both operands must be large. At the 10-bit ceiling the worst case (`u9` → `u10`) is 0.09s.
Annotating a boundary at one width, so callers assign literals rather than widen between
adjacent wide aliases, avoids the shape entirely.

## Encodings

| encoding | form | result |
|---|---|---|
| `flat` | `Literal[0, ..., 2**N-1]` | shipped; fastest, portable |
| `nested` | `Literal[u9, 512, ...]` | legal per [PEP 586][pep586]; pyrefly rejects past ~10 levels (`Invalid type inside literal, int`, 1 error at 10 bits → 7 at 16), ty at 16 |
| `union` | `u9 \| Literal[512, ...]` | ty 44.24s at 14 bits vs 0.17s flat |
| `annotated` | `Annotated[Literal[...], Ge, Le]` | tracks `flat` within noise to 14 bits |
| `opaque` | `int` | control |

```mermaid
xychart-beta
    title "ty at 14 bits by encoding"
    x-axis [union, nested, annotated, flat]
    y-axis "seconds" 0 --> 46
    bar [44.24, 0.23, 0.22, 0.17]
```

## Runtime tier

[PEP 562][pep562] module `__getattr__` resolves the same names to
`Annotated[int, Ge(lo), Le(hi)]` ([PEP 593][pep593]), the shape
[`annotated-types`][at] consumers read. `tests/test_runtime.py` pins it against the static
bounds for all 20 widths. Needs the `rt` extra; `annotated_types` imports on first
attribute access.

```python
from pydantic import TypeAdapter
from types_bits import u8  # Annotated[int, Ge(0), Le(255)] at runtime

TypeAdapter(u8).validate_python(256)  # ValidationError
```

## Prior art

[`range-typed-integers`][rti] defines `u8 = NewType('u8', Annotated[int, ValueRange(0, 255)])`
for the byte widths `u8`..`u64` / `i8`..`i64`.

| | range-typed-integers | types-bits |
|---|---|---|
| carrier | `NewType` over `Annotated[int, ValueRange]` | `Literal` enumeration |
| bound enforced by | runtime `u8_checked()` / `check_int()`, raising `IntegerBoundError` | the type checker |
| `a: u8 = 12` | mypy error — `int` is not `u8`; requires `u8(12)` | ok |
| `a: u8 = 900` | mypy error, *identical* to the line above | error, and distinguished |
| `u8(900)` | accepted statically | n/a |
| widths | u8..u64 | u1..u10 |

Verified against every checker in the gate: mypy reports the same `Incompatible types in assignment
(expression has type "int", variable has type "u8")` on the in-range and out-of-range
lines alike. The range is metadata no checker reads ([PEP 746][pep746] would not change
this). `ValueRange` is O(1) per type, so it reaches u64; enumeration is O(2^N), so it
stops at u10.

## PEPs

No PEP provides bounded integers.

| PEP | Status | Relevance |
|---|---|---|
| [586 – Literal Types][pep586] | Final | The mechanism. Calls `Literal` insufficient for numpy-style numeric code and defers integer generics. Permits the `nested` form pyrefly rejects. |
| [593 – `Annotated`][pep593] | Final | Metadata channel for the runtime tier. |
| [695 – Type Parameter Syntax][pep695] | Final | `type uN = ...` in the stub. |
| [561 – Packaging Type Information][pep561] | Final | `py.typed`; why the stub ships in the wheel. |
| [562 – Module `__getattr__`][pep562] | Final | One name, two tiers. |
| [649][pep649] / [749][pep749] – Deferred Annotations | Final (3.14) | Guarded import gets cheaper. |
| [746 – Type checking `Annotated` metadata][pep746] | Draft, targets 3.15 | Lets a checker verify metadata suits its type. Does not make any checker enforce `Ge`/`Le`. |

- [python/typing#554, "Support for Range Types?"][i554] — closed. Requested an Ada-style
  `RangeType`.
- [discuss.python.org, "Use type hinting with bound constraints, e.g. `int[0:15]`"][thread]
  — no resolution. Objections: most constraints are not statically validatable; ranges need
  new type-system machinery; arithmetic is not closed. Landed on `Annotated` +
  `annotated-types` with runtime validation.

`fixtures/reject.py` covers the arithmetic case: mypy widens `u4 + u4` to
`Literal[0, ..., 30]` and rejects assignment back into `u4`.

[pep484]: https://peps.python.org/pep-0484/
[pep561]: https://peps.python.org/pep-0561/
[pep562]: https://peps.python.org/pep-0562/
[pep586]: https://peps.python.org/pep-0586/
[pep593]: https://peps.python.org/pep-0593/
[pep649]: https://peps.python.org/pep-0649/
[pep695]: https://peps.python.org/pep-0695/
[pep746]: https://peps.python.org/pep-0746/
[pep749]: https://peps.python.org/pep-0749/
[at]: https://github.com/annotated-types/annotated-types
[i554]: https://github.com/python/typing/issues/554
[thread]: https://discuss.python.org/t/use-type-hinting-with-bound-constraints-e-g-int-0-15/38820
[rti]: https://github.com/theCapypara/range-typed-integers
