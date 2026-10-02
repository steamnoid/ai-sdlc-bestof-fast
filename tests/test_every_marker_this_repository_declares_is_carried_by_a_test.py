"""Every marker `pyproject.toml` declares is carried by at least one test.

**A marker that no test carries is a claim about the suite that nothing can check.** This
repository declared `e2e`, wrote `-m 'not e2e'` into `addopts`, and had **zero tests marked
`e2e`** — so the filter deselected nothing, the marker named a tier that did not exist, and both
read as a deliberate design to anybody who opened the file.

**Two arrangements run side by side here, and both are allowed.** A marker-selected tier is
deselected: `tests/e2e/` needs a real model and `tests/integration/` needs a real container, and
running either by default would make `pytest -q` a paid call nobody asked for. A credential-
selected test carries no marker, is collected by the default run, and skips with the reason
printed — `test_a_real_model_judging_a_real_refusal.py` and its two neighbours. **The rule is not
"never deselect", because that rule forbade the first of the two and could not have forbidden the
second.** The rule is that a filter may only exclude markers which exist, which is what the two
tests here check between them.

**Both halves are compared, and neither is a habit.** The declared set is read out of
`pyproject.toml` and the carried set out of the sources of every test, so a marker added to the
configuration with no test behind it fails here — which is the failure that was already in this
file, and it was invisible because a marker that deselects nothing is *green*.

**The suite is read as text rather than collected**, because collecting it from inside it would
run the suite to check what the suite is, and a reader would have to work out whether the check
saw everything. `@pytest.mark.<name>` and `pytestmark = pytest.mark.<name>` are the two spellings
a tier uses — a decorator for one test, a module-level assignment for a whole directory — and
**reading only the first is what made this file blind to both tiers that exist.**
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

THE_PROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"
THE_TESTS = Path(__file__).resolve().parent

A_DECLARED_MARKER = re.compile(r'^\s*"(?P<name>[a-z0-9_]+):\s', re.MULTILINE)
A_MARKER_A_TEST_CARRIES = re.compile(r"@pytest\.mark\.(?P<name>[a-z0-9_]+)")
A_MARKER_A_MODULE_APPLIES_TO_EVERYTHING = re.compile(
    r"^pytestmark\s*(?::[^=]+)?=\s*(?:\[)?pytest\.mark\.(?P<name>[a-z0-9_]+)",
    re.MULTILINE,
)
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
    """Every marker any test carries that this repository chose, wherever it is written.

    **Both spellings, and the second one is the one that hid the whole tier.** A marker on one
    test is a decorator; a marker on a directory of tests is `pytestmark`, which is a module-level
    assignment because it is the only thing that can apply to every test in a file. The two marker-
    selected tiers here are written that way, so a reader of `@pytest.mark.<name>` alone reported
    that no test carries `e2e` while the file did — and the check that exists to catch a marker
    nothing carries was blind to both markers that carry the most.
    """
    every_spelling = (A_MARKER_A_TEST_CARRIES, A_MARKER_A_MODULE_APPLIES_TO_EVERYTHING)
    return {
        a_match.group("name")
        for a_test in sorted(THE_TESTS.rglob("test_*.py"))
        for a_spelling in every_spelling
        for a_match in a_spelling.finditer(a_test.read_text(encoding="utf-8"))
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


def test_the_filter_deselects_only_markers_that_are_declared_and_carried() -> None:
    """`-m 'not X and not Y'` is allowed, and only because both of its halves are real tiers.

    **This repository runs two arrangements at once, and the rule has to hold for both.** Three
    tests need a real model, a real `GITHUB_TOKEN` and a real repository; they carry no marker, so
    the default run collects them and they skip with the reason printed — a claim a reader sees.
    Two directories are deselected by marker, because a container and a live model are a real
    dependency in the same sense and **running them by default would make `pytest -q` a paid call
    that nobody asked for**.

    **So the ban is wrong and the coupling is right.** The failure the original rule was written
    against is real and is worth naming: a `-m` filter that deselects nothing reads as a deliberate
    design while doing nothing — `e2e` was declared, filtered on, and carried by no test at all,
    which is the exact shape. **What catches that is not the absence of a filter; it is the filter
    naming markers that exist.** A filter over a marker no test carries deselects nothing and
    claims to deselect something, and the first assertion above now fails the moment that happens
    — so the two tests are halves of one rule rather than a rule and a habit.

    **Both halves of the expression, read out of it rather than remembered**, because
    `-m 'not e2e and not integration'` that quietly lost `and not integration` would deselect one
    tier, print a `deselected` count nobody could account for, and leave the container tier running
    in a suite that says it needs no container.
    """
    the_configuration = tomllib.loads(THE_PROJECT.read_text(encoding="utf-8"))
    what_is_run_by_default = the_configuration["tool"]["pytest"]["ini_options"]["addopts"]

    the_filter = A_FILTER_THAT_SELECTS_BY_MARKER.search(what_is_run_by_default)
    if the_filter is None:
        return

    what_it_excludes = set(re.findall(r"\bnot ([a-z0-9_]+)", what_is_run_by_default))
    declared = _the_markers_pyproject_declares()
    carried = _the_markers_the_tests_carry()

    assert what_it_excludes, (
        f"addopts is {what_is_run_by_default!r}, which starts a marker filter and then excludes "
        "nothing — the exact shape this repository already had once, where `e2e` was declared and "
        "filtered on and carried by no test, so the filter deselected nothing while reading as a "
        "deliberate design"
    )
    assert what_it_excludes <= declared, (
        f"the filter excludes {sorted(what_it_excludes - declared)}, which "
        f"{'is' if len(what_it_excludes - declared) == 1 else 'are'} not declared in `markers`. "
        "A filter can exclude a marker nothing declares, and the two ways of failing are the same "
        "way: the reader is told a tier is held back and nothing is"
    )
    assert what_it_excludes <= carried, (
        f"the filter excludes {sorted(what_it_excludes - carried)}, which "
        f"{'is' if len(what_it_excludes - carried) == 1 else 'are'} carried by no test. Every test "
        "in such a marker runs in the default suite, so the filter hides nothing while claiming to "
        "hide something — and a container or a live model in a suite documented as needing neither "
        "is a paid call nobody asked for"
    )
