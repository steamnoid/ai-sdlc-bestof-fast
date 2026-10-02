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

from aisdlc.verify_the_change import the_tests_the_suite_never_ran

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
