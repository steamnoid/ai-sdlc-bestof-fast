"""Every marker `pyproject.toml` declares is carried by at least one test.

**A marker that no test carries is a claim about the suite that nothing can check.** This
repository declared `e2e`, wrote `-m 'not e2e'` into `addopts`, and had **zero tests marked
`e2e`** — so the filter deselected nothing, the marker named a tier that did not exist, and both
read as a deliberate design to anybody who opened the file. The engine this repository was
assembled from has the opposite arrangement, and the difference is a real design question rather
than a detail: there, a real-dependency tier is *deselected* by a marker; here it is *selected by
a credential and skipped saying what was missing*, which is what the three real tests here do.

**Both halves are compared, and neither is a habit.** The declared set is read out of
`pyproject.toml` and the carried set out of the sources of every test, so a marker added to the
configuration with no test behind it fails here — which is the failure that was already in this
file, and it was invisible because a marker that deselects nothing is *green*.

**The suite is read as text rather than collected**, because collecting it from inside it would
run the suite to check what the suite is, and a reader would have to work out whether the check
saw everything. `pytest.mark.<name>` and a bare `@pytest.mark.<name>` are the two spellings the
repository uses, and both are read.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

THE_PROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"
THE_TESTS = Path(__file__).resolve().parent

A_DECLARED_MARKER = re.compile(r'^\s*"(?P<name>[a-z0-9_]+):\s', re.MULTILINE)
A_MARKER_A_TEST_CARRIES = re.compile(r"@pytest\.mark\.(?P<name>[a-z0-9_]+)")
A_FILTER_THAT_SELECTS_BY_MARKER = re.compile(r"-m\s*[\"']")

THE_MARKERS_PYTEST_CARRIES_ITSELF = frozenset(
    {"skip", "skipif", "xfail", "parametrize", "usefixtures", "filterwarnings"}
)
"""The markers pytest knows without being told, so they are not a claim this repository makes.

**`skipif` is in here because three tests here carry it and it is the whole of the real tier.**
A marker a deployment has to declare before it may use is one more line of configuration to keep
in step with the tests, and pytest's own markers are not a choice anybody in this repository made.
"""


def _the_markers_pyproject_declares() -> set[str]:
    """What `tool.pytest.ini_options.markers` says, read from the file rather than remembered."""
    the_configuration = tomllib.loads(THE_PROJECT.read_text(encoding="utf-8"))
    the_table = the_configuration["tool"]["pytest"]["ini_options"].get("markers", [])
    return {str(a_line).split(":", 1)[0].strip() for a_line in the_table}


def _the_markers_the_tests_carry() -> set[str]:
    """Every marker any test carries that this repository chose, wherever it is written."""
    return {
        a_match.group("name")
        for a_test in sorted(THE_TESTS.glob("test_*.py"))
        for a_match in A_MARKER_A_TEST_CARRIES.finditer(a_test.read_text(encoding="utf-8"))
        if a_match.group("name") not in THE_MARKERS_PYTEST_CARRIES_ITSELF
    }


def test_every_marker_this_repository_declares_is_carried_by_at_least_one_test() -> None:
    """No marker in the configuration with no test behind it, and no test with no marker declared.

    **Both directions, because both are a lie in the same place.** A declared marker no test
    carries is a tier that does not exist; a marker a test carries and nothing declares is a test
    that `--strict-markers` refuses to run at all. Either one is a sentence about how this suite
    is separated that a reader cannot verify by running it.
    """
    declared = _the_markers_pyproject_declares()
    carried = _the_markers_the_tests_carry()

    assert declared == carried, (
        f"pyproject declares {sorted(declared)} and the tests carry {sorted(carried)}. A marker "
        "nothing carries is a tier that does not exist, and a marker nothing declares is a test "
        "`--strict-markers` will refuse to run — and the first of those was here already: `e2e` "
        "was declared, filtered on, and carried by no test at all, so `addopts` deselected "
        "nothing while reading as a deliberate design"
    )


def test_no_marker_filter_deselects_a_test_this_repository_means_to_run() -> None:
    """No `-m` in `addopts`, and the reason is this repository's own arrangement.

    **The real tier here is selected by a credential, not by a marker.** Three tests need a real
    model, a real `GITHUB_TOKEN` and a real repository to file against; they are collected by the
    default run and skip with the reason printed, which is a claim a reader sees. A `-m` filter
    would turn that into a deselection, which is silent — and a silent tier is indistinguishable
    from a tier with nothing in it.
    """
    the_configuration = tomllib.loads(THE_PROJECT.read_text(encoding="utf-8"))
    what_is_run_by_default = the_configuration["tool"]["pytest"]["ini_options"]["addopts"]

    assert not A_FILTER_THAT_SELECTS_BY_MARKER.search(what_is_run_by_default), (
        f"addopts is {what_is_run_by_default!r}, which deselects by marker, and every test in "
        "this repository is meant to be collected by the default run — a real dependency makes a "
        "test skip with its reason printed, and a marker makes it disappear without saying why"
    )
