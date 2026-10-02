"""A real container, a real runner, and a real answer to the question a delivery rests on.

**Six pull requests on this machine were opened by a run, and the best documented one was hollow.**
It delivered `tests/api-health.test.ts` into `tests/`, while its target's `vitest.config.ts`
collected only `tests/unit/**` and `tests/integration/**`. Its own report said the suite passed
before the change and passed after it, and both statements were true, because the count did not
move. **The suite never opened either of the two files the change consisted of.**

Everything else in this repository proves that rule against a hand-written report. **This is the
one test that asks a runner.** It runs *this* repository's own suite, on its own toolchain, in a
container, and reads what the runner said it collects. There is no double in it: the answer comes
out of pytest, and the target is a project whose tests have run here many times.

**Opt-in, and skipped loudly.** A container is a real dependency in the same sense a credential
is, so a run that needs one proves nothing without it — and a green run that never started a
container is a lie, so the skip prints which thing was missing.

**The second test is the one that matters.** A witness that agrees with everything is not a
witness. The hollow pull request is exactly the case where a mechanism like this could have said
no and was not asked, so the test that says the check can still say no is the one that earns the
tier.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from aisdlc.verify_the_change import the_tests_the_suite_never_ran

pytestmark = pytest.mark.integration

WHERE_THIS_REPOSITORY_IS = Path(__file__).resolve().parents[2]

A_TEST_THIS_REPOSITORY_RUNS = "tests/test_a_change_is_proved_by_what_the_runner_collected.py"
A_TEST_NO_RUNNER_WILL_EVER_COLLECT = "tests/elsewhere/test_nothing_collects_me.py"


def _a_copy_of_this_repository(tmp_path: Path) -> str:
    """A working copy, because a suite writes to the tree it runs in.

    **A copy rather than this checkout.** `uv sync` writes `.venv` inside the project, and the
    suite container and the install container share that one directory — which is the entire
    reason the install survives into the suite. A copy is the only way this says something about
    the runner without writing a virtual environment into the tree the test is running from.
    """
    the_copy = tmp_path / "this-repository"
    shutil.copytree(
        WHERE_THIS_REPOSITORY_IS,
        the_copy,
        ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc"),
    )
    return str(the_copy)


def _what_a_real_runner_said_about(a_checkout: str):
    """The two containers this repository's own declarations ask for, and what they said.

    **Assembled by the runner, not spelled out here.** A test that re-declared the image and the
    mount would be testing its own declarations rather than the ones a real run uses, which is
    how the runner stayed npm-only for a while while a test beside it read a node
    `package.json` and agreed with it.
    """
    from aisdlc.domain.repository import Repository
    from aisdlc.tools.run_tests import (
        a_suite_to_run,
        the_container_is_reachable,
        the_tests_in,
    )

    if not the_container_is_reachable():
        pytest.skip(
            "a real container could not be started, so nothing here is proven. The default tier "
            "proves this rule against a hand-written report; this is the only test that asks a "
            "runner, and a green run that never started one proves less than no run at all"
        )

    return the_tests_in(
        a_suite_to_run(
            repository=Repository(owner="steamnoid", name="ai-sdlc-bestof-fast-selfaware"),
            checkout=a_checkout,
        )
    )


def test_a_real_runner_names_the_files_it_will_open(tmp_path: Path) -> None:
    """The answer, read out of a container rather than written into a fixture."""
    the_outcome = _what_a_real_runner_said_about(_a_copy_of_this_repository(tmp_path))

    assert the_outcome.dependencies_installed, (
        "the install did not succeed, so the suite did not run and nothing below is about "
        f"collection: {the_outcome.output[-400:]}"
    )
    assert A_TEST_THIS_REPOSITORY_RUNS in the_outcome.what_it_collected, (
        "pytest collected a test that is in this repository and did not say so, so a change "
        f"adding one would be refused for not running tests it ran:\n"
        f"{the_outcome.what_it_collected[-600:]}"
    )
    assert the_outcome.what_it_collected != the_outcome.output or the_outcome.output.strip(), (
        "a listing that is simply the suite's own output has not been read from a listing at all"
    )


def test_a_change_adding_a_test_the_runner_will_not_open_is_refused(tmp_path: Path) -> None:
    """**The hollow pull request, restated against a runner that can actually answer.**

    The suite is green, the exit code is zero, and the test this change added was never opened.
    A run reporting that as verified would be reporting a green suite over a file nobody ran, which
    is the exact shape of the six deliveries on this machine.
    """
    the_outcome = _what_a_real_runner_said_about(_a_copy_of_this_repository(tmp_path))

    the_never_run = the_tests_the_suite_never_ran(
        [A_TEST_THIS_REPOSITORY_RUNS, A_TEST_NO_RUNNER_WILL_EVER_COLLECT], the_outcome
    )

    assert the_never_run == [A_TEST_NO_RUNNER_WILL_EVER_COLLECT], (
        f"the runner named {the_outcome.what_it_collected[-300:]!r} and the check said "
        f"{the_never_run!r}. A test in a directory no runner collects is a real file with a real "
        "passing test in it, and calling it run is what made six deliveries hollow"
    )
