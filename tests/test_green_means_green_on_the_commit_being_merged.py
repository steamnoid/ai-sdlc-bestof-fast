"""`github.the_suite_went_green` is about the commit being merged, and never about a branch.

**A merge is the only irreversible thing in a delivery, and the one thing this system may not do
on a red suite.** The eighth gate decides whether the offer may be delivered; whether the delivery
may *land* is a fact about the remote's own record of the commit, and a fact nobody in this process
can be asked for twice.

**So the commit is read from GitHub rather than named here, and that is the whole point of this
file.** The head of a pull request is a moving thing: a rebase, a "update branch", or a second run
pushing the same branch all change it after this system pushed. A green run from *before* the
rebase describes a commit that is not being merged, and a tool asked "is the suite green?" about a
**branch name** answers with the latest run on that branch — which is the run for the wrong commit,
and it is green. **The test asserts the sha in the request**, not merely that the tool returned
something, because the failure it guards is a tool that works perfectly on the wrong commit.

**Three refusals and one more, and each names what GitHub said.** No check runs at all is a
different fact from a red one, and a red one is a different fact from one still going: red will not
become green by waiting. A GitHub that will not answer is the fourth, and it is separated because
"GitHub did not tell us" and "the suite is still running" call for different responses from the
person reading the message.

**An absent verdict is never green, and that is the bug this file exists to prevent.** A check
run GitHub answered with half a shape — no `conclusion`, a row that is not an object, a status
that is not a word — has no verdict, and a guard that reads "no verdict" as "no complaint" merges
a commit nothing was proved about. **Every one of those is refused as unfinished**, and the
refusal quotes what was actually there. A related mistake this repository has already made is a
row split on a separator and then measured: a trailing empty field vanished and the guard's
`len < 3` check passed, so a suite that was still running was read as green. There is no string
splitting here at all; a conclusion is compared to a closed set, and a missing one is not in it.
"""

from __future__ import annotations

import httpx
import pytest

from aisdlc.domain.repository import Repository
from aisdlc.tools.github_create_pull_request import AnOpenedPullRequest
from aisdlc.tools.the_suite_went_green import (
    THE_SETTING_NAMING_THE_WAIT,
    TheChecksCouldNotBeReadError,
    TheSuiteHasNotFinishedYetError,
    TheSuiteHasNotRunYetError,
    TheSuiteWentRedBeforeTheMergeError,
    the_suite_went_green,
)

A_REPOSITORY = Repository(owner="steamnoid", name="wellbeing-tracker-public")
A_PULL_REQUEST = AnOpenedPullRequest(number=7, address="https://github.invalid/x/y/pull/7")

THE_COMMIT_THIS_RUN_PUSHED = "1" * 40
THE_COMMIT_THE_BRANCH_POINTS_AT_NOW = "2" * 40

WHEN_THE_SUITE_WENT_GREEN = {"name": "the_gate", "status": "completed", "conclusion": "success"}
WHEN_THE_SUITE_WENT_RED = {"name": "the_gate", "status": "completed", "conclusion": "failure"}
WHEN_THE_SUITE_IS_RUNNING = {"name": "the_gate", "status": "in_progress", "conclusion": None}


def _a_github_answering(
    checks: list[dict[str, object]],
    head: str = THE_COMMIT_THIS_RUN_PUSHED,
    mergeable: bool = True,
    what_the_pull_request_answers: int = 200,
) -> tuple[httpx.Client, list[str]]:
    """A GitHub that knows one pull request and one commit's checks, and records every ask."""
    what_it_was_asked: list[str] = []

    def answer(request: httpx.Request) -> httpx.Response:
        what_it_was_asked.append(str(request.url))
        if request.method == "GET" and request.url.path.endswith("/check-runs"):
            return httpx.Response(200, json={"total_count": len(checks), "check_runs": checks})
        return httpx.Response(
            what_the_pull_request_answers,
            json={"number": A_PULL_REQUEST.number, "head": {"sha": head}, "mergeable": mergeable},
        )

    return (
        httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(answer)),
        what_it_was_asked,
    )


def test_green_is_about_the_commit_github_says_the_pull_request_points_at() -> None:
    """The sha in the check-runs request is the head sha, and the branch name appears nowhere.

    **This is the assertion the whole tool exists for.** Asked about a branch, GitHub answers with
    the latest run on that branch: after a rebase, that is a green run for the commit that was
    replaced, and merging on it merges a commit nothing was proved about. So the request names the
    sha GitHub itself reported as the pull request's head, and this reads the request back out of
    the transport rather than trusting the return value.
    """
    a_client, what_it_was_asked = _a_github_answering([WHEN_THE_SUITE_WENT_GREEN])

    the_suite_went_green(a_client, A_PULL_REQUEST, A_REPOSITORY)

    the_requests_about_the_checks = [
        asked for asked in what_it_was_asked if httpx.URL(asked).path.endswith("/check-runs")
    ]
    assert the_requests_about_the_checks, (
        f"the checks were never read at all: {what_it_was_asked}"
    )
    assert all(
        THE_COMMIT_THIS_RUN_PUSHED in asked for asked in the_requests_about_the_checks
    ), (
        f"the checks were read for {the_requests_about_the_checks} rather than for the commit "
        "the pull request points at, so a green run from before a rebase would be read as the "
        "verdict on the commit being merged"
    )


def test_a_rebased_pull_request_is_answered_about_the_new_commit_and_not_the_old_one() -> None:
    """A head that moved after this run pushed is a different commit, and the old verdict is not it.

    **The same tool, the same green run, and a different answer.** The pull request is asked about
    first and the sha it reports is what the checks are read for, so a branch that moved between
    the push and the merge cannot be merged on the run that described where it used to be.
    """
    a_client, what_it_was_asked = _a_github_answering(
        [WHEN_THE_SUITE_WENT_GREEN], head=THE_COMMIT_THE_BRANCH_POINTS_AT_NOW
    )

    what_the_suite_said = the_suite_went_green(a_client, A_PULL_REQUEST, A_REPOSITORY)

    assert what_the_suite_said.head_commit == THE_COMMIT_THE_BRANCH_POINTS_AT_NOW
    assert any(
        THE_COMMIT_THE_BRANCH_POINTS_AT_NOW in asked for asked in what_it_was_asked
    ), (
        f"the checks were not read for the commit the pull request now points at: "
        f"{what_it_was_asked}"
    )


def test_a_repository_whose_checks_have_not_run_is_refused() -> None:
    """No check runs is not a green suite, and it is not a red one either.

    **Its own refusal, because the three cases call for three different responses.** A repository
    with no checks at all is a repository where nothing has been asked to prove anything, and a
    run that merged on it would be reporting a verification that was never performed.
    """
    a_client, _ = _a_github_answering([])

    with pytest.raises(TheSuiteHasNotRunYetError):
        the_suite_went_green(a_client, A_PULL_REQUEST, A_REPOSITORY)


def test_a_failing_check_is_refused_and_named() -> None:
    """Red is refused with the check's own name, because somebody has to go and read it."""
    a_client, _ = _a_github_answering([WHEN_THE_SUITE_WENT_GREEN, WHEN_THE_SUITE_WENT_RED])

    with pytest.raises(TheSuiteWentRedBeforeTheMergeError) as the_refusal:
        the_suite_went_green(a_client, A_PULL_REQUEST, A_REPOSITORY)

    assert "the_gate" in str(the_refusal.value) and "failure" in str(the_refusal.value), (
        "the refusal does not name the check and what it concluded, so a person reading it has to "
        "go and find which of the checks went red"
    )


def test_a_check_still_running_is_refused_after_waiting_and_is_never_read_as_green(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A suite in progress has no verdict, and no verdict is not a green light.

    **This test used to say the opposite about the first half, and a real run is why it changed.**
    It asserted that a check in `in_progress` is *refused* — which is true of the verdict and false
    of the ending. A run that opened a real pull request on `steamnoid/wellbeing-tracker-public`
    was refused here because the suite had been `queued` for seconds:

        TheSuiteHasNotFinishedYetError: 'suite' concluded 'no conclusion at all, only
        {"name": "suite", ... "status": "queued", "conclusion": null, ...

    **Every real repository's checks take minutes**, so refusing on the first `queued` means this
    tool can never reach the commit it was written to reach. A check that has not started is now
    waited out, with a ceiling — and **the half that matters here is untouched**: a check with no
    verdict is still never read as green, and a ceiling of zero makes this refusal immediate, which
    is the behaviour a deployment that states no wait at all asked for.
    """
    monkeypatch.setenv(THE_SETTING_NAMING_THE_WAIT, "0")
    a_client, _ = _a_github_answering([WHEN_THE_SUITE_WENT_GREEN, WHEN_THE_SUITE_IS_RUNNING])

    with pytest.raises(TheSuiteHasNotFinishedYetError):
        the_suite_went_green(a_client, A_PULL_REQUEST, A_REPOSITORY)


def test_a_check_github_answered_with_nothing_to_read_is_refused_and_quoted() -> None:
    """Every half-shape GitHub can answer with is a refusal, and never a green light.

    **Four shapes, one rule.** A row that is not an object, a row with no name, a row whose status
    is a word nobody has heard of, and a row with no conclusion at all. **The last of those is the
    one that matters**: a guard written as "is any check red?" reads a missing conclusion as "not
    red", and a commit nothing was proved about is merged on a check that never said anything.
    """
    a_client, _ = _a_github_answering(
        [
            {"name": "a check with no verdict at all"},
            "a row that is not an object",
            {"name": "a check with an unknown status", "status": "who_knows"},
        ]
    )

    with pytest.raises(TheSuiteHasNotFinishedYetError) as the_refusal:
        the_suite_went_green(a_client, A_PULL_REQUEST, A_REPOSITORY)

    assert "a check with no verdict at all" in str(the_refusal.value), (
        "the refusal does not quote what GitHub answered, so a reader cannot tell a suite that is "
        "still running from a check that answered with something this tool cannot read"
    )


def test_a_check_that_was_skipped_is_refused_because_it_proved_nothing() -> None:
    """Only `success` is green, and a skipped check is not a green check.

    **Where the brief named three cases and this is a fourth.** GitHub has conclusions that are
    neither `success` nor a failure — `skipped` and `neutral` among them — and a run that merged on
    either would be reporting a verification that did not happen. They are refused as unfinished,
    and the refusal quotes the conclusion, because "not finished" is the honest reading of a check
    that reported no opinion rather than a passing one.
    """
    a_client, _ = _a_github_answering(
        [{"name": "the_gate", "status": "completed", "conclusion": "skipped"}]
    )

    with pytest.raises(TheSuiteHasNotFinishedYetError) as the_refusal:
        the_suite_went_green(a_client, A_PULL_REQUEST, A_REPOSITORY)

    assert "skipped" in str(the_refusal.value)


def test_a_github_that_will_not_answer_is_refused_rather_than_read_as_green() -> None:
    """"GitHub did not tell us" and "the suite is still running" are different facts.

    **Separate from the unfinished case on purpose.** A 404 about a repository this system pushed
    to twenty minutes ago is a fact about the push and not about the suite, and a person who reads
    "the suite has not finished" will go and wait for a suite nobody is running.
    """
    a_client, _ = _a_github_answering(
        [WHEN_THE_SUITE_WENT_GREEN], what_the_pull_request_answers=404
    )

    with pytest.raises(TheChecksCouldNotBeReadError) as the_refusal:
        the_suite_went_green(a_client, A_PULL_REQUEST, A_REPOSITORY)

    assert "404" in str(the_refusal.value)


def test_every_check_that_went_green_is_named_with_the_commit_it_went_green_on() -> None:
    """What the node will write on the card, and both halves are facts rather than a summary.

    **The commit and the checks, because a note saying "green" is not a record.** A person reading
    the card in a month has to be able to see which commit was proved and by which checks, and
    that is the whole of what this returns — the run adds no verdict of its own.
    """
    a_client, _ = _a_github_answering(
        [
            WHEN_THE_SUITE_WENT_GREEN,
            {"name": "unit", "status": "completed", "conclusion": "success"},
        ]
    )

    what_the_suite_said = the_suite_went_green(a_client, A_PULL_REQUEST, A_REPOSITORY)

    assert what_the_suite_said.head_commit == THE_COMMIT_THIS_RUN_PUSHED
    assert what_the_suite_said.which_checks_went_green == ["the_gate", "unit"]
