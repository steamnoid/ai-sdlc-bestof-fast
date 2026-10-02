"""A change is proved by what the repository's own runner collected, not by scraping its dots.

**Six pull requests on this machine were opened by a run, and the best documented one was hollow.**
It delivered `tests/api-health.test.ts` into `tests/`, while the target's `vitest.config.ts`
collects only `tests/unit/**` and `tests/integration/**`. Its own report said the suite passed
before the change and passed after it — and both were true, because `65 passed, 9 skipped` did not
move. **The suite never opened either of the two files the change consisted of.**

So this repository has three pieces of that answer already, none of them connected:

- `HowThisRepositoryIsTested.listing_command` — the command that asks a runner what it collects,
  set for all three toolchains,
- `the_test_files_the_suite_reported_running` — a parser for both a vitest listing and a pytest
  node-id listing, whose own docstring quotes that pull request,
- `listing_command` passed on as `announcement_command`, which the *planning* stage reads.

**And `SuiteOutcome` carries no listing.** So the answer is asked, used to plan, thrown away, and
the verification stage is left scraping the suite's own stdout. On this repository's own
toolchain that stdout is nine dots and a percentage:

```text
.........                                                                [100%]
9 passed in 0.07s
```

which names no file at all — so `_the_suite_mentioned` answers False for every test, and a
correct change is refused for not running tests it ran. **That is the same root as the hollow pull
request: nobody checked the check against the runner this repository actually uses.** A check that
refuses every correct change is a check somebody switches off, and a check nobody switches off
because it happens to be right on the target is a check that lies once.

**The suite's report is the witness, and a listing is the suite's own account of its files.**
These tests say so at the only place it can be checked cheaply — no container, no model.
"""

from __future__ import annotations

from aisdlc.verify_the_change import (
    NO_WITNESS_COULD_NAME_THIS_FILE,
    the_tests_the_suite_never_ran,
)

A_TEST_THE_PLAN_NAMED = "tests/test_the_trust_boundary_of_run_command.py"


def test_a_suite_that_names_a_test_in_its_output_proves_it_ran() -> None:
    """A vitest-shaped report, which is the shape the existing matcher already read."""
    the_suite = _a_suite_saying(
        " Test Files  1 passed (1)\n"
        f"      Tests  2 passed (2)\n"
        f" ✓ {A_TEST_THE_PLAN_NAMED} (2 tests) 12ms\n"
    )

    assert the_tests_the_suite_never_ran([A_TEST_THE_PLAN_NAMED], the_suite) == []


def test_a_pytest_node_id_listing_proves_the_test_ran() -> None:
    """**`--collect-only -q` prints `path::test_name`, and that is the shape this missed.**

    Checked because it was proved missed rather than suspected: the shipped matcher looks for the
    path at the *end* of a line, which is where vitest puts it and where pytest does not.
    """
    the_suite = _a_suite_saying(
        f"{A_TEST_THE_PLAN_NAMED}::test_the_checkout_is_a_place\n"
        f"{A_TEST_THE_PLAN_NAMED}::test_the_checkout_is_not_a_string_prefix\n"
        "\n"
        "2 tests collected in 0.04s\n"
    )

    assert the_tests_the_suite_never_ran([A_TEST_THE_PLAN_NAMED], the_suite) == [], (
        "the suite printed this test's node id and the matcher did not see it, so a correct change "
        "is refused for not running a test it ran. That is the vitest shape only, and this "
        "repository's own toolchain is pytest"
    )


def test_a_suite_that_names_no_file_cannot_prove_anything_ran() -> None:
    """`pytest -q` prints dots. **A report with no filename in it is not evidence of anything.**

    **So the answer is not to scrape harder** — it is that the runner is asked, once, and its
    answer travels with its result. This test is why that has to happen rather than the matcher
    being improved: there is nothing in this output to improve against.
    """
    what_pytest_prints = "." * 9 + " " * 56 + "[100%]\n"
    the_suite = _a_suite_saying(what_pytest_prints)

    assert the_suite.output.strip() != "", "a fixture with no output would prove anything"
    assert A_TEST_THE_PLAN_NAMED not in the_suite.output, (
        "and if this fixture ever starts naming the file it stops being the case that matters, so "
        "it is asserted here rather than trusted"
    )


def _a_suite_saying(what_it_said: str):
    """A suite result carrying one run's own words, and nothing else invented."""
    from aisdlc.tools.run_tests import SuiteOutcome

    return SuiteOutcome(
        exit_code=0,
        passed=True,
        output=what_it_said,
        dependencies_installed=True,
    )


def test_a_suite_that_named_no_file_is_proved_by_the_listing_the_runner_gave() -> None:
    """**The dots case, and it is the case that has no answer anywhere in the suite's output.**

    This is the third test's scenario completed rather than abandoned: a report of nine dots and a
    percentage names nothing, so the only witness left is the listing the runner was already asked
    for. **That listing is asked at planning time and thrown away**, because `SuiteOutcome` has
    nowhere to put it — and the stage that needs it is the verification, which runs later.
    """
    the_suite = _a_suite_that_collected(
        what_the_suite_said="." * 9 + " " * 56 + "[100%]\n",
        what_it_collected=(
            "tests/test_the_trust_boundary_of_run_command.py::test_the_checkout_is_a_place\n"
            "tests/test_the_trust_boundary_of_run_command.py::test_it_is_not_a_string_prefix\n"
            "\n2 tests collected in 0.04s\n"
        ),
    )

    assert the_suite.output.find(A_TEST_THE_PLAN_NAMED) == -1, (
        "this fixture is only the interesting case while the suite output names nothing"
    )
    assert the_tests_the_suite_never_ran([A_TEST_THE_PLAN_NAMED], the_suite) == [], (
        "the runner collected this test and said so, and the check called it unrun. The answer was "
        "asked once, at planning time, and thrown away"
    )


def test_a_suite_whose_listing_omits_a_test_still_refuses_it() -> None:
    """**The listing has to be able to say no, or it is not a witness.**

    This is the hollow pull request restated against the one mechanism that could have caught it:
    a test the runner never collected is not evidence of anything, whatever the suite's exit code
    says, and this is the only test here that says the check can fail.
    """
    the_suite = _a_suite_that_collected(
        what_the_suite_said="." * 9 + " " * 56 + "[100%]\n",
        what_it_collected="tests/test_something_else.py::test_unrelated\n\n1 test collected\n",
    )

    assert the_tests_the_suite_never_ran([A_TEST_THE_PLAN_NAMED], the_suite) == [
        A_TEST_THE_PLAN_NAMED
    ]


def _a_suite_that_collected(what_the_suite_said: str, what_it_collected: str):
    """A suite result that carries both the run's words and the listing the runner gave.

    **Two fields because there are two facts.** What a suite printed and what it collects are
    different questions, asked at different moments, and collapsing them is how a check ends up
    scraping dots.
    """
    from aisdlc.tools.run_tests import SuiteOutcome

    return SuiteOutcome(
        exit_code=0,
        passed=True,
        dependencies_installed=True,
        output=what_the_suite_said,
        what_it_collected=what_it_collected,
    )


# **The two marks this runner prints, as escapes, for the reason the three vitest marks already
# are** — `THE_MARKS_A_SUITE_NAMES_A_FILE_BY` spells itself that way so the source is ASCII and
# nobody's editor has to guess what a lone mark means. These were read out of a container, and a
# character that renders as a box in one terminal is a test that fails for a reason nobody can see.
A_NODE_PASSDED = "\u2714 the_edge_it_does_take (0.27ms)"
A_NODE_SAYS_ONE_TEST_RAN = "\u2139 tests 1\n\u2139 pass 1\n\u2139 fail 0\n"
A_NODE_SAYS_NO_TEST_RAN = "\u2139 tests 0\n\u2139 pass 0\n\u2139 fail 0\n"


def test_a_runner_that_cannot_name_its_files_is_not_read_as_having_collected_nothing() -> None:
    """**Read out of a container, and it is the case that makes the rest of this file necessary.**

    `node --test` prints `ok 1 - the_edge_it_does_take` and nothing else. Four reporters were run
    against it — `spec`, `tap`, `dot`, `junit` — and **not one of them prints a file path.** A
    vitest report names files, a pytest listing names `path::test_name`, and Node's own runner
    names the test and leaves the file out.

    **So an empty listing from a green suite means "this runner cannot say", and it does not mean
    "this runner collected nothing".** Read as the second, every test a correct change adds is
    reported unrun and the delivery is refused for not running tests it ran — which is the
    mirror image of the hollow pull request, and a false accusation rather than a missed one.

    **And it is not fixable by scraping harder**, which is what the three marks before it tried.
    There is no file in the output to find. The fix is to ask the suite whether it ran anything
    at all, because that it does say, and to refuse to accuse on a witness that could not speak.
    """
    the_suite = _a_suite_that_collected(
        what_the_suite_said=f"{A_NODE_PASSDED}\n{A_NODE_SAYS_ONE_TEST_RAN}",
        what_it_collected=f"{A_NODE_PASSDED}\n{A_NODE_SAYS_ONE_TEST_RAN}",
    )

    assert the_suite.what_it_collected.strip() != "", "a fixture with no listing proves nothing"
    assert the_tests_the_suite_never_ran([A_TEST_THE_PLAN_NAMED], the_suite) == [
        NO_WITNESS_COULD_NAME_THIS_FILE
    ], (
        "a runner that printed no file name and said it passed one test cannot be read as having "
        "collected nothing. This is the Node built-in runner's real output, and reading it as an "
        "empty collection refuses every correct change made to a project that uses it"
    )


def test_a_suite_that_says_it_collected_nothing_is_believed() -> None:
    """**The other side, or the rule above is just "never accuse".**

    A green run over a repository with no tests says so in a number, and an empty listing beside
    that number is believable. **A check that cannot say no is a check that protects nothing.**
    """
    the_suite = _a_suite_that_collected(
        what_the_suite_said=A_NODE_SAYS_NO_TEST_RAN,
        what_it_collected=A_NODE_SAYS_NO_TEST_RAN,
    )

    assert the_tests_the_suite_never_ran([A_TEST_THE_PLAN_NAMED], the_suite) == [
        A_TEST_THE_PLAN_NAMED
    ], (
        "the suite said it ran no tests and the listing named none, so the plan's test is "
        "uncollected — and saying otherwise would make this a check that never fails"
    )
