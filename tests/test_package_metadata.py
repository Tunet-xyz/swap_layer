"""Package metadata follows the conventions the four Tunet libraries share."""

import re
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    tomllib = pytest.importorskip("tomli")

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).parents[1]
PROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
SDIST = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["hatch"][
    "build"]["targets"]["sdist"]["include"]
WORKFLOW = ROOT / ".github/workflows/tests.yaml"


def tests_workflow() -> dict:
    if not WORKFLOW.exists():  # the sdist does not ship .github
        pytest.skip("needs the repository checkout")
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_classifiers_are_sorted_and_typed():
    classifiers = PROJECT["classifiers"]
    assert classifiers == sorted(classifiers)
    assert "Typing :: Typed" in classifiers
    assert (ROOT / "src/swap_layer/py.typed").exists()


def test_python_classifiers_match_the_test_matrix():
    matrix = tests_workflow()["jobs"]["test"]["strategy"]["matrix"]["python-version"]
    listed = [c.rsplit(" ", 1)[1] for c in PROJECT["classifiers"] if re.fullmatch(r"Programming Language :: Python :: 3\.\d+", c)]
    assert listed == matrix


def test_lowest_django_classifier_is_tested():
    series = sorted(
        (c.rsplit(" ", 1)[1] for c in PROJECT["classifiers"] if c.startswith("Framework :: Django :: ")),
        key=lambda version: tuple(map(int, version.split("."))),
    )
    assert series[0] == "4.2"
    jobs = tests_workflow()["jobs"]
    install = " ".join(step.get("run", "") for step in jobs["minimum-dependencies"]["steps"])
    assert '"Django>=4.2,<4.3"' in install


def test_keywords_follow_the_shared_form():
    keywords = PROJECT["keywords"]
    assert keywords == sorted(keywords)
    assert {"django", "mcp"} <= set(keywords)
    assert "python" not in keywords
    assert all(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", keyword) for keyword in keywords)


def test_sdist_ships_examples_tools_and_community_files():
    for entry in ("/examples", "/tools", "/CODE_OF_CONDUCT.md", "/SECURITY.md", "/LICENSE"):
        assert entry in SDIST, entry
        assert (ROOT / entry.lstrip("/")).exists(), entry
    # Agent instructions and CI configuration stay in the repository, as in the other libraries.
    for entry in ("/AGENTS.md", "/CLAUDE.md", "/.github"):
        assert entry not in SDIST, entry
