"""The suite's own report names every file it opened, so no separate listing is needed.

**This is the seventh gate, and it is the last thing between this pipeline and `DONE`.** A run
closed a critical vulnerability in `wellbeing-tracker-public` — six gates approved, the fix was
correct — and stopped here:

> both collection logs end with `No test files found, exiting with code 1`, so the test collector
> did not actually enumerate the tests the suites claim ran

The suite behind it reported **74 of 79 passing**. So the refusal was right about the danger and
wrong about the cause: this system asked a runner to name the files it collected, and the answer
arrived as four words that mean *I was asked something I do not have* — because
`vitest list` arrived in vitest 2.1 and the repository pins 1.6.1.

**And the whole question was unnecessary, which is why this is the fix and not a better command.**
vitest 1.6.1's own JSON reporter writes one entry per file it opened, and the entry's `name` is
that file's path. Read out of the runner's source rather than remembered:

```js
testResults.push({ assertionResults, startTime, endTime, status, message, name: file.filepath })
```

**So the suite's run is already a complete witness of what it collected**, and asking a second
command for the same fact is both wrong and an extra container run per verification. The paths are
absolute, which the existing suffix matching already handles — its docstring says a runner prints a
path "relative to whichever root it chose", and `file.filepath` is the longest version of that.

**Both halves are asserted separately, because they can fail separately.** A report nobody reads is
a suite that ran and told nobody, and a reader with nothing to read is a report that exists and says
nothing — and the second is what a repository whose runner prints dots has always looked like.
"""

from __future__ import annotations

import json

from aisdlc.tools.run_tests import (
    THE_SUITE_THAT_THIS_REPOSITORY_DEFINES,
    SuiteOutcome,
    the_test_files_the_suite_reported_running,
)

# **The shape vitest 1.6.1's JSON reporter writes, transcribed from its source** — one entry per
# file, with the file's path under `name`. Only the keys that carry the fact are here, because a
# fixture that reproduces a whole reporter is a fixture nobody can check against anything.
A_SUITE_THAT_REPORTED_TWO_FILES_IN_JSON = json.dumps(
    {
        "numTotalTestSuites": 2,
        "numTotalTests": 79,
        "numPassedTests": 74,
        "numFailedTests": 5,
        "success": False,
        "testResults": [
            {
                "assertionResults": [],
                "startTime": 0,
                "endTime": 1,
                "status": "passed",
                "message": "",
                "name": "/work/tests/unit/the-regression.test.ts",
            },
            {
                "assertionResults": [],
                "startTime": 0,
                "endTime": 1,
                "status": "failed",
                "message": "1 failing",
                "name": "/work/tests/unit/wellbeing-176-177.test.ts",
            },
        ],
    }
)


def test_a_suite_that_reported_in_json_names_the_files_it_opened() -> None:
    """One entry per file, and the path is under `name`.

    **Read through the reader every caller uses**, not through a new helper, because a reader that
    only this test calls is a helper rather than a fix. The paths come back absolute, which is the
    form `file.filepath` writes and the form the suffix matching is documented to expect.
    """
    the_files_named = the_test_files_the_suite_reported_running(
        A_SUITE_THAT_REPORTED_TWO_FILES_IN_JSON
    )

    assert the_files_named == [
        "/work/tests/unit/the-regression.test.ts",
        "/work/tests/unit/wellbeing-176-177.test.ts",
    ], (
        f"the reader got {the_files_named!r} out of a report that names both files plainly. **This "
        "is the seventh gate's blocker**: a plan that adds a regression test cannot be shown that "
        "the suite collected it, so the rule that protects a change from being unobserved refuses "
        "every change that adds a test"
    )


def test_a_report_that_names_no_file_still_names_none() -> None:
    """A runner that prints dots has said nothing, and this reader must not invent a file.

    **The half that keeps the reader honest.** If JSON-reading fell back to *something*, then a
    report with no `testResults` at all would produce an answer, and the answer would be a claim
    about a repository nobody asked. **The refusal `NO_WITNESS_COULD_NAME_THIS_FILE` is built on
    this reader returning nothing**, so a reader that always answers would retire the refusal
    without anyone deciding to retire it.
    """
    assert the_test_files_the_suite_reported_running("....") == [], (
        "a report of four dots named a file, which means this reader is answering from something "
        "other than what the runner printed"
    )


def test_the_suite_is_asked_to_report_in_json() -> None:
    """The command carries `--reporter=json`, because nothing reads a report that does not say so.

    **Asserted on the command rather than on a field, because the field would be a claim.** A
    `reporter` field beside a command that does not use it is the same defect this repository has
    already been bitten by — a property saying `network` is "none" while the arguments carry no
    `--network` — and `run_tests.py`'s own docstring says a field and the command it describes
    cannot disagree.
    """
    assert "--reporter=json" in THE_SUITE_THAT_THIS_REPOSITORY_DEFINES, (
        f"the suite is run as {THE_SUITE_THAT_THIS_REPOSITORY_DEFINES!r}, so its report is "
        "vitest's default output, which names no file. **The default reporter together with the "
        "JSON one** is what keeps both a number a person reads and a path this system reads"
    )


def test_the_default_reporter_is_still_asked_for() -> None:
    """A JSON-only suite is a worse suite: the report a person reads is the JSON.

    **`_the_suite_says_it_ran_something` reads `Tests 74 passed`**, and a JSON report says
    `"numTotalTests": 79` instead — so replacing the default reporter would silence the rule that
    decides whether an empty witness beside a green report is believable. Both are asked for, and
    the pair is the claim.
    """
    assert "default" in " ".join(THE_SUITE_THAT_THIS_REPOSITORY_DEFINES), (
        f"the suite is run as {THE_SUITE_THAT_THIS_REPOSITORY_DEFINES!r}, with no default "
        "reporter "
        "left in it. **The human-readable report is what a person reads at the verification "
        "gate**, and it is also what tells this system the suite ran something at all"
    )


def test_a_report_in_json_is_still_read_for_how_many_tests_ran() -> None:
    """`numTotalTests` is the same fact `Tests 74 passed` states, and the rule needs it.

    **Not a new rule — a second shape for an existing one.** `HOW_MANY_TESTS_A_RUNNER_SAYS`
    answers "did this run open anything", which is what makes an empty witness believable rather
    than damning. **A repository whose suite reports in JSON and nothing else would otherwise have
    its green run treated as silence**, and a refusal that cannot tell those apart refuses
    everything.
    """
    from aisdlc.verify_the_change import _the_suite_says_it_ran_something

    assert _the_suite_says_it_ran_something(A_SUITE_THAT_REPORTED_TWO_FILES_IN_JSON), (
        "a report carrying `\"numTotalTests\": 79` said it ran 79 tests and was read as saying it "
        "ran none. **Then a suite that ran 79 tests and collected nothing the plan asked for looks "
        "like a suite that ran nothing**, and the check meant to catch an unrun test waves it "
        "through"
    )


def _unused(_: SuiteOutcome) -> None:
    """Kept so the import of `SuiteOutcome` is a real one, not a name in an import line."""
