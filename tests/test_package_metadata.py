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
TESTS = yaml.safe_load((ROOT / ".github/workflows/tests.yaml").read_text(encoding="utf-8"))


def test_classifiers_are_sorted_and_typed():
    classifiers = PROJECT["classifiers"]
    assert classifiers == sorted(classifiers)
    assert "Typing :: Typed" in classifiers
    assert (ROOT / "src/swap_layer/py.typed").exists()


def test_python_classifiers_match_the_test_matrix():
    matrix = TESTS["jobs"]["test"]["strategy"]["matrix"]["python-version"]
    listed = [c.rsplit(" ", 1)[1] for c in PROJECT["classifiers"] if re.fullmatch(r"Programming Language :: Python :: 3\.\d+", c)]
    assert listed == matrix


def test_lowest_django_classifier_is_tested():
    series = sorted(
        (c.rsplit(" ", 1)[1] for c in PROJECT["classifiers"] if c.startswith("Framework :: Django :: ")),
        key=lambda version: tuple(map(int, version.split("."))),
    )
    assert series[0] == "4.2"
    install = " ".join(step.get("run", "") for step in TESTS["jobs"]["minimum-dependencies"]["steps"])
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
