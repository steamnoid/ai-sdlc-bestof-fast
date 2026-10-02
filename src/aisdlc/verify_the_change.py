"""Running a repository's suite on both sides of a change, which is the only proof there is.

**The suite runs here, and that is the point of this module.** A `VerificationReport` built
from two outcomes a caller typed in would report green without anything having run, and
that is the same lie as a test that skips: a green tick for work nobody did. So the change is
applied *between* two runs performed by this function, and the production runner is a
container rather than a stub, so the default path cannot quietly become the cheap one.

**The order is the property, and it is the one thing worth defending.** A verification that
applied the change first and ran the suite twice afterwards would report the same number
twice and call it before-and-after. There is no way to catch that from outside this
function, so the unit test puts an assertion *inside* the change and asks how many times the
suite had run when it was applied.

**Nothing is rolled back when the second run is red.** The change stays applied and the
report says so, because a report that undid the evidence would leave nothing to look at: the
question a person asks of a failing change is which files it touched, and that question has
no answer on a checkout somebody else put back.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from aisdlc.agents.verification_report import VerificationReport
from aisdlc.domain.repository import Repository
from aisdlc.tools.github_clone_repository import ClonedRepository
from aisdlc.tools.run_tests import (
    SuiteOutcome,
    a_suite_to_run,
    the_test_files_the_suite_reported_running,
    the_tests_in,
)

RunTheSuite = Callable[[ClonedRepository, Repository], SuiteOutcome]

# **One call that undoes the change and runs the suite, because the caller is the only one that
# knows how either is done.** See `verify_the_change` for why this is one argument and not two.
AnswerTheSuiteWithoutTheChange = Callable[[], SuiteOutcome]


class AnUnrunTestError(Exception):
    """The suite passed and never ran a test the approved plan said this change adds.

    Named after the rule rather than after the symptom: the symptom is a green report, and a
    green report is what a passing verification is supposed to look like. What is wrong is the
    gap between the tests the change adds and the tests that ran, and that gap is the finding.
    """


def the_suite_in_a_container(clone: ClonedRepository, repository: Repository) -> SuiteOutcome:
    """The repository's own suite, run where §27 says it runs.

    The default rather than a keyword a caller must remember, so a caller who forgets
    anything gets the real thing instead of nothing at all. A stub is a test's business and
    a test passes one explicitly.
    """
    return the_tests_in(a_suite_to_run(repository=repository, checkout=str(clone.path)))


class ATestThatPassesWithoutTheChangeError(Exception):
    """A change nothing observes is not a change, and this says the three runs that say so.

    **The sibling of `AnUnrunTestError`, and between them they are the only two ways a test can be
    a file rather than a test.** That one catches a test the runner never opened. This one catches
    a test the runner opened, ran, and that agreed with a repository the change had not been
    applied to — the test passing *vacuously*, which looks identical to a passing test from
    every signal this system has.

    **It is a fact and not a judgement about the model.** The suite ran three times in a
    container and its three outputs are in the message, so a person deciding reads the same
    numbers this system refused on. Nothing here says the change was a good idea or a bad one.
    """


def verify_the_change(
    clone: ClonedRepository,
    repository: Repository,
    what_the_change_does: Callable[[], None],
    run_the_suite: RunTheSuite = the_suite_in_a_container,
    the_tests_the_plan_named: Sequence[str] = (),
) -> VerificationReport:
    """The suite before the change, the suite after it, and what the pair says about it.

    The change is a function rather than a description because the ordering above can only
    be honoured by doing the work in the middle, and a description would leave the ordering
    to the caller — which is where it was wrong in the first place.
    """
    before = run_the_suite(clone, repository)
    what_the_change_does()
    after = run_the_suite(clone, repository)

    # **A red suite is already a failed verification, so it is asked nothing.** Both facts hold
    # when a change's tests go unrun *and* the suite went red, and answering only the first
    # would throw away the regressions — the failing assertions, which are what a person needs.
    # This check is for the case where everything is green, because a green report over a change
    # that was never executed is the one that lies.
    the_tests_never_run = []
    if after.passed:
        the_tests_never_run = the_tests_the_suite_never_ran(the_tests_the_plan_named, after)
    if the_tests_never_run:
        raise AnUnrunTestError(
            f"The suite passed and never ran {len(the_tests_never_run)} of the "
            f"{len(the_tests_the_plan_named)} test(s) this approved plan said the change adds: "
            f"{', '.join(the_tests_never_run)}.\n\n"
            f"The suite said:\n{after.output}\n\n"
            "A test file the suite's runner never collects is not a passing test — it is a "
            "file that was never opened. The usual cause is a test placed where the "
            "repository's own configuration does not look, so the change was delivered and "
            "never exercised."
        )

    return VerificationReport(
        suite_before_the_change=before,
        suite_after_the_change=after,
    )


def refuse_a_change_nothing_observed(
    verification: VerificationReport,
    the_tests_the_plan_named: Sequence[str],
    how_the_suite_answers_without_the_change: AnswerTheSuiteWithoutTheChange,
) -> None:
    """Undo the change, run the suite once more, and refuse if it agrees with what came before.

    **A separate rule and not a third run inside `verify_the_change`.** That function had five
    arguments, and a sixth would have made it a shape `PLR0913` was right about -- and the sixth
    would have belonged to a different question anyway. Producing the report is one thing and
    asking whether anything observed it is another, so the second has its own name and its own
    error, and the caller that can answer the question supplies the answer rather than the facts
    to work it out from.

    **Asked only of a change that kept the suite green.** A suite that is already red has not
    been shown to observe anything, and the red suite is `ASuiteThatWentRedIsNotADeliveryError`
    at the delivery to say -- reporting both from here would throw away the failing assertions,
    which are what a person needs most.

    **And a change that named no test is not asked, which is this rule's one gap and the argument
    below is deliberately the other way round.** The early return reads "a plan that adds no test
    has nothing to observe the change", and that is true of the *plan's tests* and false of the
    suite: the whole suite can notice a change the plan said nothing about. The function's own
    last paragraph commits to asking the stronger question -- does *anything* notice -- and the
    early return quietly narrows it back.

    **So this is written down rather than fixed, because the obvious fix is worse.** Deleting the
    condition would refuse every documentation change, every comment and every version bump this
    pipeline is ever asked for, because the truthful answer to "did anything notice?" about a
    README is no and there was nothing wrong. Telling a silent change apart from a harmless one
    needs to know whether the change touched something a suite could read, and this function is
    not told what the change wrote. A real run is what made it worth writing down: asked to retime
    a Dockerfile healthcheck, this system's policy caught it -- *a HEALTHCHECK whose path, port, or
    interval is wrong does not fail loudly, the container simply reports unhealthy forever* -- and
    this function said nothing at all, because the plan named no test.

    `tests/test_whether_anything_observed_the_change.py` pins the gap, so whoever closes it is
    closing something named rather than something discovered.

    **The whole repository's suite and not only the new tests.** A filter would need to know how
    this project's runner names a single test file, and a name invented here is a name nobody
    verified -- the same reason `regressions` quotes the suite rather than scraping it. Running
    everything also asks the stronger question: does *anything* in this repository notice that the
    change came and went.
    """
    if not verification.suite_after_the_change.passed or not the_tests_the_plan_named:
        return

    without_the_change = how_the_suite_answers_without_the_change()

    if not without_the_change.passed:
        return

    raise ATestThatPassesWithoutTheChangeError(
        f"The suite is green after this change, and green again with the change undone, so "
        f"{len(the_tests_the_plan_named)} test(s) this approved plan said the change adds passed "
        f"either way: {', '.join(the_tests_the_plan_named)}.\n\n"
        f"With the change undone the suite said:\n{without_the_change.output}\n\n"
        "A test that passes with the change taken away is a file, not a test: it observes "
        "nothing this run did, and a suite that grows by fifteen assertions nobody wrote for this "
        "change is a number that went up and a repository that did not. Either the change does "
        "something a test can see, or the tests assert what was already true."
    )


def the_tests_the_suite_never_ran(
    the_tests_the_plan_named: Sequence[str], the_suite: SuiteOutcome
) -> list[str]:
    """The plan's tests the suite's own output does not mention, in the plan's order.

    **The suite is the only witness, and its own output is the witness's account.** Nothing here
    counts test files on disk, guesses a runner's naming convention, or asks a model whether the
    tests passed. A runner names the files it ran, and a file it does not name is a file it did
    not run — which is the whole finding, and it is checkable by string because the fact is a
    string.

    **A plan, and not a pattern, says which of a change's files are tests.** `tests_to_add` is a
    field a person approved at the planning gate, so nothing has to infer that
    `api-health.test.ts` is a test and `route.ts` is not. A glob would be a second opinion about
    a repository's conventions, from a file that has never read them.

    **The path is matched as a suffix, because a runner prints the path relative to whichever
    root it chose** — `/work/tests/unit/x.test.ts` and `tests/unit/x.test.ts` are the same file
    and one of them is what a container sees. Matching the whole line instead would call every
    test unrun on a runner that prints absolute paths, and a check that cries wolf on the
    ordinary case is a check people switch off.

    **Only the suite after the change is asked**, in the caller. A file that ran before the
    change is not evidence about the change.
    """
    # **The listing first, and the report second — in that order, for a reason.** A listing is
    # the runner naming the files it will open; a report is what it printed while opening them.
    # On a toolchain whose report names no file at all — `pytest -q` prints dots — the report can
    # answer nothing, and a check that consults it first is a check that refuses every correct
    # change or waves through every uncollected one. Both are read because both exist, and the
    # listing does not exist unless the runner was asked, which is the runner's business.
    what_the_runner_says = "\n".join((the_suite.what_it_collected, the_suite.output))

    the_never_run: list[str] = []
    for a_test_the_plan_named in the_tests_the_plan_named:
        if not _the_suite_mentioned(what_the_runner_says, a_test_the_plan_named):
            the_never_run.append(a_test_the_plan_named)
    return the_never_run


def _the_suite_mentioned(what_the_suite_said: str, a_test: str) -> bool:
    """Whether the suite's own output names this test, in any of the shapes a runner prints it.

    **Three shapes, and the first version of this read only the first.** A vitest report puts the
    path at the *end* of a line after a mark (`✓ tests/unit/x.test.ts (2 tests)`), so an
    `endswith` was enough — and it was written against the one runner the first real delivery
    targeted. Then `pytest --collect-only -q` puts it at the *start* of a line followed by a node
    id (`tests/x.py::test_name`), and the same check answered False for a suite that had plainly
    named the test.

    **That is not a near miss, it is the same defect that made six deliveries hollow**: a check
    read against one runner and trusted on another. The parser that reads both already existed —
    `the_test_files_the_suite_reported_running`, whose docstring quotes the pull request this
    defect produced — and had no caller outside its own test. **It has one now.**
    """
    for a_file_the_suite_named in the_test_files_the_suite_reported_running(what_the_suite_said):
        if a_file_the_suite_named == a_test:
            return True

    for a_line in what_the_suite_said.splitlines():
        if a_line.rstrip().endswith(a_test):
            return True
        # A runner counts its tests on the same line: "(3 tests)", "(9 tests | 9 skipped)".
        if a_line.rstrip().rstrip(")").endswith(a_test) or f"{a_test} " in a_line:
            return True
    return False
