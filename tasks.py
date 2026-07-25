"""Project tasks -- run with ``camas``."""

from pathlib import Path

from camas import AgentFormat, Claude, Config, Parallel, Sequential, Task, by_suffix

CHECKED = ("src", "harness", "tests")
PY = by_suffix((".py", ".pyi"), default=(".",))
UV = "uv run --no-sync"


def checked_dirs(changed: tuple[str, ...]) -> tuple[str, ...]:
    if not changed or "pyproject.toml" in changed:
        return CHECKED
    return tuple(root for root in CHECKED if any(path.startswith(f"{root}/") for path in changed))


sync = Task("uv sync", mutates=True, help="materialize this cell's environment")
gen = Task(f"{UV} python -m types_bits", mutates=True, help="materialize the .pyi stub")

fmt = Task(f"{UV} ruff format {{paths}}", mutates=True, paths=".")
fmt_check = Task(f"{UV} ruff format --check {{paths}}", paths=".")
lint = Task(
    f"{UV} ruff check {{paths}}",
    paths=PY,
    agent_format=AgentFormat("--output-format sarif", "sarif"),
)
lint_fix = Task(f"{UV} ruff check --fix {{paths}}", mutates=True, paths=PY)

actionlint = Task(f"{UV} actionlint", when=".github")
zizmor = Task(f"{UV} zizmor --no-online-audits .github/workflows", when=".github")
actions = Parallel(actionlint, zizmor, help="lint and audit the workflows")
static = Parallel(fmt_check, lint, actions, help="everything that needs no interpreter")

mypy = Task(
    f"{UV} mypy {{paths}}",
    paths=checked_dirs,
    agent_format=AgentFormat("--junit-xml {report}", "junit"),
)
pyright = Task(f"{UV} pyright {{paths}}", paths=checked_dirs)
basedpyright = Task(f"{UV} basedpyright {{paths}}", paths=checked_dirs)
ty = Task(
    f"{UV} ty check {{paths}}",
    paths=checked_dirs,
    agent_format=AgentFormat("--output-format junit", "junit"),
)
pyrefly = Task(
    f"{UV} pyrefly check {{paths}}",
    paths=checked_dirs,
    agent_format=AgentFormat("--output-format junit-xml", "junit"),
)
zuban = Task(f"{UV} zuban check {{paths}}", paths=checked_dirs)

typecheck = Parallel(
    mypy, pyright, basedpyright, ty, pyrefly, zuban, help="every installed checker at once"
)

test = Task(
    f"{UV} pytest",
    when=(*CHECKED, "fixtures", "pyproject.toml"),
    help="unit tests, doctests, and the checker-driven fixtures",
    agent_format=AgentFormat("--junitxml {report}", "junit"),
)

suite = Parallel(static, typecheck, test)

verify = Parallel(
    Sequential(sync, suite),
    matrix={
        "PY": tuple(
            stripped
            for line in (Path(__file__).parent / ".python-version")
            .read_text(encoding="utf-8")
            .splitlines()
            if (stripped := line.strip()) and not stripped.startswith("#")
        )
    },
    env={"UV_PROJECT_ENVIRONMENT": ".camas/.venv-{PY}", "UV_PYTHON": "{PY}"},
    help="every checker and the whole suite, on every interpreter",
)

bench = Task(f"{UV} python -m harness.bench", help="time the checkers as bit width grows")
bench_full = Task(f"{UV} python -m harness.bench --full")
bench_shapes = Task(
    f"{UV} python -m harness.bench --shapes --out bench/results/shapes.json",
    help="fixed vs marginal cost of declaring and using one width",
)
build = Task("uv build", help="prove the build hook materializes the stub into the wheel")

fix = Sequential(fmt, lint_fix)
check = Sequential(sync, gen, verify)

_ = Config(default_task=check, agent=Claude(fix=fix, check=check))
