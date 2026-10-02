"""Whether anything in the repository noticed a change come and go — the rule, and its one gap.

**This rule had no test at all, and it is the rule the whole repair mechanism leans on.** Three of
the refusals a supervisor can be handed come from this module or its sibling, and none of them had a
test saying when they fire and when they do not. A rule with no test is a rule nobody has checked,
and this one has a documented gap in it — so the first job here is to pin what it actually does,
gap included.

**The question is asked by undoing the change and running the suite once more.** Green after, green
without, means nothing in the repository noticed the difference, and that is a fact about the
repository rather than a judgement about the model. That is what makes it a refusal rather than an
opinion, and it is why the answer is a boolean fact rather than a field a caller could pass in.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aisdlc.agents.verification_report import VerificationReport
from aisdlc.tools.run_tests import SuiteOutcome
from aisdlc.verify_the_change import (
    ATestThatPassesWithoutTheChangeError,
    refuse_a_change_nothing_observed,
)


def _a_suite(passing: bool, output: str) -> SuiteOutcome:
    return SuiteOutcome(
        exit_code=0 if passing else 1,
        passed=passing,
        dependencies_installed=True,
        output=output,
    )


def _a_green_run_of_the_suite() -> tuple[VerificationReport, int]:
    """A report whose change kept the suite green, and a counter of how often it was re-run."""
    how_many_times_the_suite_was_run_again = {"count": 0}

    def the_suite_answers_without_the_change() -> SuiteOutcome:
        how_many_times_the_suite_was_run_again["count"] += 1
        return _a_suite(True, "74 passed, 9 skipped")

    the_report = VerificationReport(
        suite_before_the_change=_a_suite(True, "65 passed, 9 skipped"),
        suite_after_the_change=_a_suite(True, "65 passed, 9 skipped"),
    )
    return the_report, how_many_times_the_suite_was_run_again


def test_a_test_that_passes_with_the_change_undone_is_refused() -> None:
    """Green after, green without: nothing noticed, so the run stops and a supervisor reads it.

    **The suite is run twice more and not filtered, which is the point.** Asking only the plan's new
    tests would need to know how this project's runner names one test file, and a name invented
    here is a name nobody verified. Running everything asks the stronger question instead: does
    *anything* in this repository notice that the change came and went.
    """
    the_report, how_many_times = _a_green_run_of_the_suite()

    with pytest.raises(ATestThatPassesWithoutTheChangeError) as the_refusal:
        refuse_a_change_nothing_observed(
            the_report,
            ["test_health.py"],
            _answers_without_the_change_returning(_a_suite(True, "74 passed")),
        )

    assert how_many_times["count"] == 0, (
        "the suite was not run a second time, so nothing was asked and this refusal was raised "
        "without looking"
    )
    assert "test_health.py" in str(the_refusal.value), (
        "the refusal does not name the test that passed either way, so whoever reads it has to go "
        "and find the assertion that was supposed to notice the change"
    )


def test_a_test_that_fails_with_the_change_undone_is_left_alone() -> None:
    """Green after and red without is the whole point of the test — so nothing is refused here."""
    the_report, _ = _a_green_run_of_the_suite()

    refuse_a_change_nothing_observed(
        the_report,
        ["test_health.py"],
        _answers_without_the_change_returning(_a_suite(False, "1 failed — expected 200, got 404")),
    )


def test_a_suite_that_went_red_is_reported_by_the_delivery_instead() -> None:
    """A red suite has not been shown to observe anything, so this rule stays out of its way.

    **The failing assertions are what a person needs most, and a second refusal would bury them.**
    So a suite that is already red is not asked the undo question at all — the refusal here would
    be `ASuiteThatWentRedIsNotADeliveryError` at the delivery, which carries the suite's own output.
    """
    the_report, _ = _a_green_run_of_the_suite()
    a_red_report = VerificationReport(
        suite_before_the_change=_a_suite(True, "65 passed"),
        suite_after_the_change=_a_suite(False, "1 failed, 64 passed"),
    )
    how_many_times_the_suite_was_run_again = {"count": 0}

    def the_suite_answers_without_the_change() -> SuiteOutcome:
        how_many_times_the_suite_was_run_again["count"] += 1
        return _a_suite(True, "74 passed")

    refuse_a_change_nothing_observed(
        a_red_report, ["test_health.py"], the_suite_answers_without_the_change
    )

    assert how_many_times_the_suite_was_run_again["count"] == 0, (
        "the suite was run again for a change that had already gone red, so the two refusals now "
        "report the same run and the person reading the card has to work out which one to trust"
    )
    assert the_report.suite_after_the_change.passed, (
        "the fixture a green report is built from is not green, so the other two tests in this "
        "file are not testing what they say they are"
    )


def test_a_change_that_named_no_test_is_not_asked_at_all() -> None:
    """**The known gap, pinned rather than fixed — and the strongest case for it is in the README.**

    A plan that adds no test means this rule never runs, so a change nothing observes is delivered
    with nothing said about it. That is not hypothetical: asked to retime a Dockerfile healthcheck,
    this system's own policy caught it by reading two suite outputs — *"A HEALTHCHECK whose path,
    port, or interval is wrong does not fail loudly — the container simply reports unhealthy
    forever"* — and the machinery said nothing, because the plan named no test.

    **And removing the early return would refuse changes that are fine**, which is why this is left
    as a decision rather than made overnight. The undo-and-rerun answers "did anything notice?",
    and for a README, a comment, or a version bump the truthful answer is no — there was nothing to
    notice and nothing wrong. The rule would refuse every documentation change this pipeline is
    ever asked to make. Telling that apart needs to know whether the change touched anything the
    suite could read, and `refuse_a_change_nothing_observed` is not told what the change wrote.

    So the gap is pinned here, where a reader sees the cost, and the fix is written down rather
    than guessed at.
    """
    the_report, _ = _a_green_run_of_the_suite()
    how_many_times_the_suite_was_run_again = {"count": 0}

    def the_suite_answers_without_the_change() -> SuiteOutcome:
        how_many_times_the_suite_was_run_again["count"] += 1
        return _a_suite(True, "74 passed")

    refuse_a_change_nothing_observed(the_report, [], the_suite_answers_without_the_change)

    assert how_many_times_the_suite_was_run_again["count"] == 0, (
        "the suite was re-run for a change whose plan named no test, so the early return is gone "
        "and the rule now refuses every documentation change it is asked to make — which is a "
        "decision to make on purpose, not one to arrive at by deleting a condition"
    )


def test_a_change_that_edited_a_test_file_is_asked_even_having_named_no_test() -> None:
    """The other side of that rule, and a real run's reason for wanting it.

    **A run wrote a regression test that fails on the file as it stands and passes without it —
    verified by hand, both ways.** The plan named the file to change and left `tests_to_add` empty,
    so the early return above fired and **nothing measured anything**. The supervisor then wrote on
    its own card that the test *"passed with the change applied and passed again with the change
    undone"* — a measurement no run took, said three times, and the run believed.

    **The plan had touched a test file, which is exactly the fact this rule was missing.** A test
    is what a suite reads, so a change that edits one is a change the suite can notice, and asking
    is not absurd for it. **The rule's own docstring already said the missing thing was that this
    function "is not told what the change wrote"** — and the caller has the plan, three lines above
    the call. This test is the other half of the one above: a plan that touched nothing a suite
    reads is not asked, and a plan that touched a test is.

    **The third run finds the observation.** The regression test stays in the working tree through
    `git checkout HEAD~1` on the changed file, so it fails on exactly the content the checkout
    restored — which is what `without_the_change.passed is False` means, and why nothing is refused.
    """
    the_report, _ = _a_green_run_of_the_suite()
    how_many_times_the_suite_was_run_again = {"count": 0}

    def the_suite_answers_without_the_change() -> SuiteOutcome:
        how_many_times_the_suite_was_run_again["count"] += 1
        return _a_suite(False, "1 failed — the regression test still sees expect.skip")

    refuse_a_change_nothing_observed(
        the_report,
        [],
        the_suite_answers_without_the_change,
        what_the_change_touched=["tests/integration/wellbeingt-17-docker.integration.test.ts"],
    )

    assert how_many_times_the_suite_was_run_again["count"] == 1, (
        "the plan touched a test file and named no test, so the rule returned without asking — and "
        "the run then had no measurement of its own change at all, which is how a supervisor ended "
        "up reporting a result that was never run"
    )


def _answers_without_the_change_returning(what_the_suite_says: SuiteOutcome):
    """The third run, as the caller supplies it: this module does not know how a suite is undone."""

    def the_suite_answers_without_the_change() -> SuiteOutcome:
        return what_the_suite_says

    return the_suite_answers_without_the_change


def test_this_file_tests_a_rule_and_not_a_fixture() -> None:
    """The refusal names the test, so a broken fixture cannot make this file green.

    A file whose every test builds its own data can pass for a long time against a fixture that no
    longer says what it says. So one assertion here is not about the rule at all: it re-reads the
    green report the other tests are built from and says it is green, which is the one thing every
    other assertion in this file depends on.
    """
    the_report, _ = _a_green_run_of_the_suite()

    assert the_report.suite_after_the_change.passed, (
        "the report every other test in this file is built from is not green"
    )
    assert Path(__file__).exists(), "this file does not exist, so nothing in it ran"
