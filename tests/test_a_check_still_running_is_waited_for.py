"""A check that is still running is not a refusal, and waiting for it is the only way through.

**This is the one thing standing between this system and a delivery, and a real run found it.**
A run reached `deliver_this_run` for the first time — eight gates approved, a real branch
pushed, a real pull request opened on `steamnoid/wellbeing-tracker-public` — and this tool
answered:

    TheSuiteHasNotFinishedYetError: 'suite' concluded 'no conclusion at all, only
    {"id": 110984693509, "name": "suite", ... "status": "queued", "conclusion": null,
    "started_at": "2026-10-02T18:59:55Z", "completed_at": null, ...}

**GitHub had not run the suite yet.** The pull request had been open for seconds. And a check in
`queued` is not a red suite, not an absent verdict, and not somebody's opinion — it is
*nothing has happened yet*, and a tool that reads it as a refusal cannot open a pull request and
merge it in the same run. **Every real repository's checks take minutes**, so this tool
as written can never reach the commit it exists to reach.
the commit it was built to reach.

**The refusal is not wrong, and that is worth saying plainly.** `TheSuiteHasNotFinishedYetError`'s
own docstring is right that *an absent verdict is not a green one* — a guard written as "is
anything red?" reads a `queued` check as "nothing to complain about" and merges a commit nothing
was proved about. **What is wrong is treating that refusal as the end.** The rule and the ending
are different things, and only the ending is wrong here.

**So the rule keeps every word and the ending changes.** Wait while GitHub is still deciding, with
a ceiling, and refuse on the verdict once there is one. **The ceiling is what makes waiting
honest:** without it a run waits forever on a suite that will never finish, which is a hang
wearing the name of a delivery.
"""

from __future__ import annotations

import httpx
import pytest

from aisdlc.domain.repository import Repository
from aisdlc.tools.the_suite_went_green import (
    TheSuiteHasNotFinishedYetError,
    TheSuiteWentRedBeforeTheMergeError,
    the_suite_went_green,
)

A_REPOSITORY = Repository(owner="steamnoid", name="wellbeing-tracker-public")
THE_HEAD = "01afb811622ba3b2fe2dd6be4c492377984d3124"


class _AClientThatAnswersWithTheseChecks:
    """A GitHub that says one thing and then another, which is what a real one does.

    **`queued` first and a verdict second**, because that is the sequence the run saw: a pull
    request opened seconds before, GitHub still holding the check. **A client that answered once
    would make a waiting tool look like a working one**, because the first answer is always the one
    a broken tool reads.
    """

    def __init__(self, *check_runs: dict[str, object]) -> None:
        self.what_it_was_asked_for: list[str] = []
        self._the_answers = list(check_runs)

    def get(self, url: str, **keywords: object) -> httpx.Response:
        """Answer the pull request with its head, and the check runs with the next row in sequence.

        **Two different shapes, because the tool asks two different questions.** The head commit
        comes from the pull request and the checks from a commit — and a double that answered both
        with one would be testing a client that does not exist.
        """
        self.what_it_was_asked_for.append(url)
        if "/pulls/" in url:
            return httpx.Response(
                200, json={"number": 39, "head": {"sha": THE_HEAD}},
                request=httpx.Request("GET", url),
            )
        the_next = self._the_answers.pop(0) if len(self._the_answers) > 1 else self._the_answers[0]
        return httpx.Response(
            200,
            json={"total_count": 1, "check_runs": [the_next]},
            request=httpx.Request("GET", url),
        )


def _a_check(status: str, conclusion: str | None) -> dict[str, object]:
    """One row of GitHub's answer, in the two fields this tool reads."""
    return {
        "name": "suite",
        "status": status,
        "conclusion": conclusion,
        "head_sha": THE_HEAD,
        "html_url": f"https://github.com/{A_REPOSITORY.owner}/{A_REPOSITORY.name}/actions/runs/1",
    }


def _a_pull_request():
    from aisdlc.tools.github_create_pull_request import AnOpenedPullRequest

    return AnOpenedPullRequest(
        number=39,
        address=f"https://github.com/{A_REPOSITORY.owner}/{A_REPOSITORY.name}/pull/39",
    )


def test_a_check_still_running_is_waited_for_rather_than_refused(monkeypatch) -> None:
    """`queued` and then a verdict, and the verdict is what the run goes on with.

    **This is the exact sequence the real run met and gave up on.** A pull request seconds old, one
    check in `queued`, and a tool that treated "nothing has happened yet" as "nothing to merge".
    **Asserting the outcome and not the waiting**, because the waiting is an implementation and the
    outcome is the claim: the run must end up holding the verdict, not the absence of one.
    """
    monkeypatch.setenv("AISDLC_SUITE_GRACE_SECONDS", "1")
    _no_sleeping(monkeypatch)
    the_client = _AClientThatAnswersWithTheseChecks(
        _a_check("queued", None),
        _a_check("completed", "success"),
    )

    what_the_suite_said = the_suite_went_green(
        _as_a_client(the_client),  # type: ignore[arg-type]
        _a_pull_request(),
        A_REPOSITORY,
    )

    assert what_the_suite_said.head_commit == THE_HEAD, (
        "the run does not have the commit the pull request points at, so nothing below it can be "
        "about what a merge button would merge"
    )
    assert what_the_suite_said.which_checks_went_green == ["suite"], (
        f"the run ended holding {what_the_suite_said.which_checks_went_green} rather than the "
        "check that went green — so a verdict that arrived after the refusal was thrown away, "
        "and the delivery stops on a moment rather than on a fact"
    )


def test_a_red_suite_is_still_refused_after_waiting(monkeypatch) -> None:
    """Waiting does not turn a red suite green, and that is the rule this tool exists for.

    **Both halves in one test, because a waiting tool that also merges failures is worse than no
    tool.** The run that found the gap was one whose `main` was green and whose pull request was
    red: `wellbeingt-17-docker.integration.test.ts` calls `expect.skip`, which Vitest does not have,
    and that line is only reached when a Docker build did not happen. On `main` the build happened
    and the call was never made; on the pull request it was, and the suite went red. **A tool that
    waited and then merged that would be the defect this repository exists to prevent.**
    """
    monkeypatch.setenv("AISDLC_SUITE_GRACE_SECONDS", "1")
    _no_sleeping(monkeypatch)
    the_client = _AClientThatAnswersWithTheseChecks(
        _a_check("queued", None),
        _a_check("completed", "failure"),
    )

    with pytest.raises(TheSuiteWentRedBeforeTheMergeError):
        the_suite_went_green(
            _as_a_client(the_client),  # type: ignore[arg-type]
            _a_pull_request(),
            A_REPOSITORY,
        )


def test_a_suite_that_never_finishes_stops_on_the_ceiling(monkeypatch) -> None:
    """A run waits for GitHub for a stated length and not for ever, and the ceiling says what.

    **A hang wearing the name of a delivery is worse than a refusal**, because a refusal is
    readable and a hang is not. Every other bound in this repository counts something and states its
    default rather than reading as `unlimited`, and this one is the same kind of thing: a run
    waiting on another system's CI is waiting on something this system cannot hurry.
    """
    monkeypatch.setenv("AISDLC_SUITE_GRACE_SECONDS", "1")
    _no_sleeping(monkeypatch)
    the_client = _AClientThatAnswersWithTheseChecks(_a_check("queued", None))

    with pytest.raises(TheSuiteHasNotFinishedYetError) as the_refusal:
        the_suite_went_green(
            _as_a_client(the_client),  # type: ignore[arg-type]
            _a_pull_request(),
            A_REPOSITORY,
        )

    assert "queued" in str(the_refusal.value), (
        f"the refusal is {str(the_refusal.value)!r} and does not say the suite was still "
        "running, so a reader cannot tell a suite that has not answered from a row this tool "
        "cannot read — and those two are the ones they would act on differently"
    )


def _as_a_client(what_it_answers: object) -> httpx.Client:
    """The client this tool is handed, standing in for the one a delivery builds.

    **A double and not a subclass of `httpx.Client`,** because the tool only ever calls `get` on it
    and a real `httpx.Client` would be a second thing to keep working.
    """
    return what_it_answers  # type: ignore[return-value]


def _no_sleeping(monkeypatch: pytest.MonkeyPatch) -> None:
    """Wait without waiting, so a test that exercises waiting takes milliseconds.

    **The sleep is patched and not the reading.** A test that reads twice is what proves a tool
    waits; a test that reads twice *and takes five seconds each time* is the same proof bought at
    the price of the whole suite. **The grace is still a real second**, because a ceiling of zero
    would refuse on the first `queued` and there would be nothing to wait for — which is the
    behaviour of a deployment that states no wait at all, and a different test's claim.
    """
    monkeypatch.setattr(
        "aisdlc.tools.the_suite_went_green.time.sleep", lambda _seconds: None
    )
