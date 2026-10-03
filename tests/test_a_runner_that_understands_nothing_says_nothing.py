"""A runner with no listing command must not be reported as a repository that collects no tests.

**This repository's seventh gate has been refusing deliveries over a lie, and the lie is four words
long: `No test files found`.** The run that closed a critical vulnerability in
`wellbeing-tracker-public` reached the verification gate and was refused for exactly that, while the
suite it had just run reported 74 of 79 passing:

> I looked at both `what_it_collected` fields and both suite outputs: the outputs claim 74/79
> passing tests, but both collection logs end with `No test files found, exiting with code 1`

**The refusal was correct and its reason was false, and the reason is this system's own.** The
listing is `npx vitest list --run`, and:

```text
$ npx vitest list --help
vitest/1.6.1
Usage: $ vitest [...filters]
Commands: run  related  watch  dev  bench  typecheck  [...]
```

**There is no `list` command in vitest 1.6.1.** It was added in vitest 2.1. So `vitest list --run`
is not a listing at all — it is `vitest` with the *filter* `list`, which matches no file, and vitest
prints its `include` patterns and then reports honestly that it matched nothing. **The output says
"no test files found" and the truth is "I was asked a question that does not exist in this runner."**

**Both readings are the same four words and nothing in the record tells them apart.** One means a
delivery's tests were never collected — a refusal, and correctly so. The other means this system
asked its own tool a question its version cannot answer. **A gate reading the second one as the
first one is a gate stopping a correct change for an invented reason**, which is the failure this
repository keeps meeting in the other direction.

**So the rule is narrow and it is about honesty rather than about listing.** An answer a runner
gave because it understood the question is not the same as an answer it gave because it did not, and
a caller that cannot tell them has to be told rather than left to guess — **the same rule that made
`dependencies_installed` a field rather than an inference from the exit code.**
"""

from __future__ import annotations

from aisdlc.tools.run_tests import (
    THE_LISTING_THAT_A_NODE_RUNNER_UNDERSTANDS,
    the_runners_announcement_of,
)


def _the_help_a_vitest_without_a_listing_command_prints() -> str:
    """Exactly what `npx vitest list --help` printed on this repository's runner, kept verbatim.

    **The real output, not a paraphrase**, because the whole claim is that the word `list` does not
    appear among the commands. A paraphrase could tidy in a `list` line and the test would then be
    asserting nothing about the runner at all.
    """
    return """vitest/1.6.1

Usage:
  $ vitest [...filters]

Commands:
  run [...filters]
  related [...filters]
  watch [...filters]
  dev [...filters]
  bench [...filters]
  typecheck [...filters]
  [...filters]
"""


def test_the_listing_asks_a_command_this_repository_runner_does_not_have() -> None:
    """The constant names `list`, and vitest 1.6.1 has no such command.

    **Asserted as a fact about the constant and the runner's own help, not as a fact about
    vitest.** If a future repository upgrades to a vitest that *does* have `list`, this test fails
    and the fix is to delete it rather than to make it pass — which is the point. **A test that
    would still pass on a repository whose listing works is measuring nothing**, and the run that
    produced this finding was refused for four words of this constant's output.
    """
    assert "list" in THE_LISTING_THAT_A_NODE_RUNNER_UNDERSTANDS, (
        "the listing no longer asks for a `list` command, so the finding this file records has been "
        "acted on. **Delete this test when that happens** — a characterisation of a defect that has "
        "been fixed is a claim the defect is still there"
    )
    assert THE_LISTING_THAT_A_NODE_RUNNER_UNDERSTANDS[:3] == ("npx", "vitest", "list"), (
        f"the listing is now {THE_LISTING_THAT_A_NODE_RUNNER_UNDERSTANDS!r}, so whatever this test "
        "says about `vitest list` is no longer about the command that runs"
    )
    the_commands_the_runner_offers = _the_help_a_vitest_without_a_listing_command_prints()
    assert "list [" not in the_commands_the_runner_offers and "\n  list\n" not in (
        the_commands_the_runner_offers
    ), (
        "vitest 1.6.1's own help now offers a `list` command, which this file's transcript says it "
        "does not. **That means this repository's vitest has moved**, and the refusal it caused has "
        "to be re-run rather than assumed still to apply"
    )


def test_a_runner_that_understood_nothing_is_not_reported_as_a_repository_with_no_tests() -> None:
    """Four words that mean two different things must not arrive as one answer.

    **The two meanings.** A runner that ran a listing it understands and matched nothing means the
    repository collects no test files, and a delivery whose tests were never collected is not a
    delivery. A runner that did not understand the command means this system asked a question its own
    tool cannot answer, and the honest answer is silence rather than a fact about the repository.

    **Which one silence.** Because the caller cannot tell, silence is the only answer that cannot be
    a fabricated claim — and a rule that treats nothing printed as "no grounds to refuse" already
    exists in this module, so silence is a shape a caller already handles rather than a new one.
    """
    what_the_runner_printed = (
        "include: tests/unit/**/*.{test,spec}.ts\n"
        "include: tests/integration/**/*.{test,spec}.ts\n"
        "No test files found, exiting with code 1\n"
    )

    what_the_caller_is_told = the_runners_announcement_of(what_the_runner_printed, exit_code=1)

    assert "No test files found" not in what_the_caller_is_told, (
        f"the caller is told {what_the_caller_is_told!r}. **On a runner with no `list` command, "
        "those four words are the runner reporting that it was asked something it does not have, "
        "and passing them on as an answer about the repository is how a gate refuses a correct "
        "change.** The suite behind this run reported 74 of 79 passing"
    )
