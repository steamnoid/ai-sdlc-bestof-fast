"""`github.the_suite_went_green`: whether the commit about to be merged is one anything proved.

**A merge is the only irreversible thing a delivery does, and this is the question in front of
it.** The eighth gate decides whether the offer may be delivered; whether the delivery may *land*
is a fact about the remote's own record of a commit, and it is the one fact in a delivery that
this process cannot be the authority for.

**The commit is read from GitHub and never named by a caller.** The head of a pull request moves:
a rebase, an "update branch", or a second run pushing the same branch all change it after this
system pushed. A green run from *before* the rebase describes a commit that is not being merged,
and a check-runs request naming a **branch** answers with the latest run on that branch — which is
the run for the wrong commit, and it is green. So the pull request is asked about first, and the
sha it reports is what the checks are read for.

**Three refusals and a fourth, and each is a different fact.** No checks at all is not a red
suite; a red one will not become green by waiting; one still going is not a verdict. And a GitHub
that will not answer is separated from all three, because "GitHub did not tell us" and "the suite
is still running" send a reader to two different places.

**An absent verdict is never green, and there is no string splitting in this file.** A row with no
conclusion, a row that is not an object, a status nobody has heard of — each is refused as
unfinished, quoting what was actually there. A conclusion is compared against a closed set, and a
missing one is not in it. A related failure this repository has already made is a row split on a
separator and then measured: a trailing empty field vanished, a `len < 3` guard passed, and a
suite that was still running was read as green.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Mapping

import httpx
from pydantic import BaseModel, ConfigDict

from aisdlc.domain.repository import Repository
from aisdlc.tools.github_create_pull_request import AnOpenedPullRequest

WHERE_GITHUB_KEEPS_THE_PULL_REQUEST = "/repos/{owner}/{name}/pulls/{number}"
WHERE_GITHUB_KEEPS_THE_CHECKS_ON_A_COMMIT = (
    "/repos/{owner}/{name}/commits/{commit}/check-runs"
)
GITHUB_OKAY = 200
SECONDS_A_READ_MAY_TAKE = 10
HOW_MANY_CHECK_RUNS_ARE_READ = 100

THE_CONCLUSION_THAT_MEANS_GREEN = "success"
"""The only conclusion this tool will merge on, named because every other one is a refusal.

**One value out of the whole of GitHub's set.** A check that reported `skipped` or `neutral` has
reported no opinion, and a run that merged on it would be recording a verification that did not
happen. It is refused as unfinished, and the refusal quotes the conclusion, because a reader who
is told "not finished" will go and look for a suite that is not running.
"""

THE_CONCLUSIONS_THAT_MEAN_RED = (
    "failure",
    "timed_out",
    "cancelled",
    "action_required",
    "stale",
    "startup_failure",
)
"""What GitHub calls a check that did not pass, gathered here so the red refusal names all of them.

**A tuple and not one string, because the conclusion is compared rather than read.** A red suite
will not become green by waiting, so it is refused before the unfinished case: a run told "the
suite has not finished" goes and waits, and a run told the suite is red goes and reads.
"""


class TheSuiteHasNotRunYetError(Exception):
    """Nothing has been asked to prove anything about the commit about to be merged.

    **A repository with no check runs is not a repository whose suite is green.** Nothing was
    verified, and a merge on the strength of that would put a verification into the record that
    was never performed — which is a worse claim than a red suite, because a red suite is at least
    visible to whoever reads the checks.
    """


class TheSuiteWentRedBeforeTheMergeError(Exception):
    """A check on the commit about to be merged concluded that it did not pass.

    **Carries the check's own name and GitHub's own conclusion**, because this system cannot parse
    another project's check output to name what broke. A summary a scraper invented is a name
    nobody verified, and the person who has to act on this is the one who can read the check.
    """


class TheSuiteHasNotFinishedYetError(Exception):
    """A check on the commit about to be merged has no verdict yet, or has no readable one.

    **An absent verdict is not a green one, and that is the whole of the rule.** A row GitHub
    answered with no `conclusion`, a row that is not an object, a status nobody has heard of — a
    guard written as "is anything red?" reads every one of them as "nothing to complain about",
    and merges a commit nothing was proved about. The refusal quotes what was there, so a reader
    can tell a suite still running from a row this tool cannot read.
    """


class TheChecksCouldNotBeReadError(Exception):
    """GitHub would not say what the pull request points at, so nothing is known about its checks.

    **Separate from the unfinished case, and the difference is what a reader does next.** A 404
    about a repository this system pushed to twenty minutes ago is a fact about the push, and a
    person told "the suite has not finished" will go and wait for a suite nobody is running.
    """


THE_STATUSES_THAT_MEAN_GITHUB_IS_STILL_DECIDING = ("queued", "in_progress", "waiting", "pending")
"""The states a check is in while GitHub has not finished with it, and none is an opinion.

**`conclusion` is `null` in every one of them**, and a missing conclusion is not a green one —
that is why the guard exists and why the refusal is right. What was wrong was treating the
refusal as the end. These four are the states that mean *GitHub has not finished*, against
`completed`, which means it has finished and has an opinion.
"""

THE_SETTING_NAMING_THE_WAIT = "AISDLC_SUITE_GRACE_SECONDS"
"""How long a delivery waits for another system's CI, and it defaults rather than `unlimited`.

**Seconds, and named after what it bounds.** Every other ceiling in this repository counts
something or times something and states its default, because a bound nobody noticed is the same
failure as an answer nobody asked for — and a run holding a delivery open for ever is a hang
wearing the name of a delivery.
"""

HOW_MANY_SECONDS_WHEN_NO_WAIT_IS_STATED = 600
"""Ten minutes, which is a slow CI suite rather than a fast machine."""

SECONDS_BETWEEN_ASKINGS_WHILE_GITHUB_DECIDES = 5
"""How often to ask again while GitHub decides.

**Five seconds rather than one**, because the thing being waited for is somebody else's CI and a
polite poll costs one request in five rather than sixty. **And not longer**, because a run that
asked every thirty seconds would turn a two-minute suite into a five-minute delivery, and the
ceiling would be measuring the sleep rather than the suite.
"""


class WhatTheSuiteSaid(BaseModel):
    """The commit the verdict is about, and every check that went green on it.

    **Two fields and no verdict of its own.** A node writes these on the card, and "green" on its
    own is not a record: a person reading the card in a month has to be able to see which commit
    was proved and by which checks. The run adds no judgement, so a reader is looking at GitHub's
    answer rather than at this system's opinion of it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    head_commit: str
    which_checks_went_green: list[str]


def the_suite_went_green(
    client: httpx.Client,
    the_pull_request: AnOpenedPullRequest,
    repository: Repository,
) -> WhatTheSuiteSaid:
    """The commit this pull request points at, and every check that went green on it — or not.

    **The pull request is read first, and that is the order the whole tool is for.** Everything
    else in a delivery is about the commit this system pushed; this is about the commit GitHub
    says the pull request points at, which is the commit the merge button would merge and the
    only one a merge can be justified by. Read the other way round — a sha handed in by the
    caller — the tool is a lookup on somebody else's opinion of what is being merged.
    """
    the_head_commit = _the_commit_the_pull_request_points_at(
        client, the_pull_request, repository
    )
    the_checks = _the_checks_once_they_have_a_verdict(client, repository, the_head_commit)
    _refuse_a_check_run_that_is_not_green(the_checks, the_head_commit)

    return WhatTheSuiteSaid(
        head_commit=the_head_commit,
        which_checks_went_green=[_the_name_of(a_check) for a_check in the_checks],
    )


def _the_checks_once_they_have_a_verdict(
    client: httpx.Client, repository: Repository, the_commit: str
) -> list[object]:
    """The checks on this commit, read again for as long as GitHub is still deciding.

    **Waiting and not refusing, and only for a check that has not started or is still running.**
    A check that has *concluded* — red, skipped, neutral, anything — comes back from the first
    read and is judged at once, so **nothing here can turn a red suite into a merged one.** What is
    waited out is `queued` and `in_progress`: the states that mean *GitHub has not finished*, which
    are not opinions about the commit.

    **The ceiling is what makes waiting honest.** Every other bound in this repository counts
    something and states its default rather than reading as `unlimited`: a run waiting on another
    system's CI is waiting on something it cannot hurry, and a hang wearing the name of a delivery
    is worse than a refusal because a refusal is readable.

    **The head commit is read once, outside this loop, and that is deliberate.** A branch somebody
    else moved while this run waited would have its checks read from the commit the run asked about
    and merged as though it were the one the pull request points at — which is the exact mistake
    this whole tool was written to prevent. Re-reading the head would turn that mistake from
    unlikely into a race, so a branch that moves while this waits is refused rather than followed.
    """
    the_wait_is_over = time.monotonic() + how_long_this_run_waits_for_the_suite()
    while True:
        the_checks = _the_check_runs_on(client, repository, the_commit)
        if not _some_check_is_still_being_decided(the_checks):
            return the_checks

        if time.monotonic() >= the_wait_is_over:
            the_still_running = [
                _the_name_of(a_check)
                for a_check in the_checks
                if _a_check_is_still_being_decided(a_check)
            ]
            names = ", ".join(repr(a_name) for a_name in the_still_running)
            how_long = how_long_this_run_waits_for_the_suite()
            raise TheSuiteHasNotFinishedYetError(
                f"{names} was still running on {the_commit} after {how_long} seconds, so this run "
                "gives up waiting rather than holding a delivery open for another system's CI. "
                f"GitHub answered: {json.dumps(the_checks)}"
            )

        time.sleep(SECONDS_BETWEEN_ASKINGS_WHILE_GITHUB_DECIDES)


def _some_check_is_still_being_decided(the_checks: list[object]) -> bool:
    """Whether any check here has not finished, which is the only thing worth waiting for."""
    return any(_a_check_is_still_being_decided(a_check) for a_check in the_checks)


def _a_check_is_still_being_decided(a_check: object) -> bool:
    """Whether GitHub says this check has not reached a conclusion yet.

    **`status` and not `conclusion`, and that is the distinction the real run turned on.** A check
    in `queued` has no conclusion because none exists yet — nothing has been said about the
    commit, which is not the same as something being said about it. Reading a missing conclusion as
    a verdict and refusing on it is what ended the run; **reading it as green would have been the
    worse bug**, and it is the one this tool was built to avoid.
    """
    if not isinstance(a_check, dict):
        return False
    return a_check.get("status") in THE_STATUSES_THAT_MEAN_GITHUB_IS_STILL_DECIDING


def _the_commit_the_pull_request_points_at(
    client: httpx.Client,
    the_pull_request: AnOpenedPullRequest,
    repository: Repository,
) -> str:
    """The sha GitHub reports as this pull request's head, and a refusal when it will not say.

    **A sha and not a branch, twice over.** The request names the pull request rather than a ref,
    and what is read out of it is `head.sha`. A tool that asked about `aisdlc/issue-1` would be
    answered with the latest run on that branch, which after a rebase is the run for a commit
    nobody is merging.
    """
    answer = client.get(
        WHERE_GITHUB_KEEPS_THE_PULL_REQUEST.format(
            owner=repository.owner,
            name=repository.name,
            number=the_pull_request.number,
        ),
        timeout=SECONDS_A_READ_MAY_TAKE,
    )
    if answer.status_code != GITHUB_OKAY:
        raise TheChecksCouldNotBeReadError(
            f"GitHub answered {answer.status_code} when asked which commit "
            f"{the_pull_request.address} points at, so nothing is known about what was proved "
            f"about the commit about to be merged. GitHub said: {answer.text}"
        )

    the_head = answer.json().get("head")
    the_commit = the_head.get("sha") if isinstance(the_head, dict) else None

    if not isinstance(the_commit, str) or not the_commit.strip():
        raise TheChecksCouldNotBeReadError(
            f"GitHub named no commit for {the_pull_request.address}, so there is nothing to have "
            f"been proved about. GitHub answered: {answer.text}"
        )
    return the_commit


def _the_check_runs_on(
    client: httpx.Client, repository: Repository, the_commit: str
) -> list[object]:
    """Every check GitHub has a run for on this one commit, in the order GitHub lists them."""
    answer = client.get(
        WHERE_GITHUB_KEEPS_THE_CHECKS_ON_A_COMMIT.format(
            owner=repository.owner, name=repository.name, commit=the_commit
        ),
        params={"per_page": HOW_MANY_CHECK_RUNS_ARE_READ},
        timeout=SECONDS_A_READ_MAY_TAKE,
    )
    if answer.status_code != GITHUB_OKAY:
        raise TheChecksCouldNotBeReadError(
            f"the checks on {the_commit} could not be read, so this run cannot claim the commit "
            f"about to be merged was proved by anything. GitHub said: {answer.text}"
        )

    the_check_runs = answer.json().get("check_runs")
    if not isinstance(the_check_runs, list):
        raise TheChecksCouldNotBeReadError(
            f"GitHub answered with no list of checks on {the_commit}, so there is nothing to have "
            f"been proved about. GitHub answered: {answer.text}"
        )
    return the_check_runs


def _refuse_a_check_run_that_is_not_green(
    the_checks: list[object], the_commit: str
) -> None:
    """Refuse unless every check concluded `success`, and say which check said what.

    **Nothing at all, then red, and then everything else — and the order is the argument.** A
    red check will not become green by waiting, so it is refused first: a run told "the suite has
    not finished" goes and waits, and a run told the suite is red goes and reads. Everything that
    is left and is not `success` is unfinished, which is where a `skipped` or `neutral` conclusion
    lands — a check that reported no opinion is not a check that passed.
    """
    if not the_checks:
        raise TheSuiteHasNotRunYetError(
            f"no check has ever run on {the_commit}, so nothing has been proved about the commit "
            "about to be merged. A repository whose checks have not run is not a repository whose "
            "suite is green, and a merge on the strength of that records a verification that was "
            "never performed"
        )

    for a_check in the_checks:
        what_it_concluded = _what_a_check_run_concluded(a_check)
        if what_it_concluded in THE_CONCLUSIONS_THAT_MEAN_RED:
            raise TheSuiteWentRedBeforeTheMergeError(
                f"{_the_name_of(a_check)!r} concluded {what_it_concluded!r} on {the_commit}, so "
                "the commit about to be merged is not merged on this run's say-so. A red suite "
                "does not become green by waiting, and this system cannot name what broke inside "
                "another project's check, so the check's own name and conclusion are the whole "
                "of what a person can act on"
            )
        if what_it_concluded != THE_CONCLUSION_THAT_MEANS_GREEN:
            raise TheSuiteHasNotFinishedYetError(
                f"{_the_name_of(a_check)!r} concluded {what_it_concluded!r} on {the_commit}, and "
                f"only {THE_CONCLUSION_THAT_MEANS_GREEN!r} is a verdict this tool will merge on. A "
                "check that reported no opinion proved nothing, and a check with no verdict at "
                f"all proved nothing either. GitHub answered: {json.dumps(a_check)}"
            )


def _what_a_check_run_concluded(a_check: object) -> str:
    """The conclusion GitHub gave this check run, or what it gave instead.

    **Nothing readable becomes a word that is in no set, rather than a default.** A row with no
    `conclusion`, a row that is not an object at all, a conclusion that is not a string: each of
    them is a check with no verdict, and the comparison above refuses every one of them because
    the word it produced is not `success` and is not in the red set either. Nothing here counts
    fields or measures a length.
    """
    if not isinstance(a_check, dict):
        return f"no conclusion at all, only {json.dumps(a_check)}"
    the_conclusion = a_check.get("conclusion")
    if not isinstance(the_conclusion, str) or not the_conclusion.strip():
        return f"no conclusion at all, only {json.dumps(a_check)}"
    return the_conclusion


def _the_name_of(a_check: object) -> str:
    """A check run's name, or the row itself when GitHub did not name it."""
    if not isinstance(a_check, dict):
        return json.dumps(a_check)
    the_name = a_check.get("name")
    return the_name if isinstance(the_name, str) and the_name.strip() else json.dumps(a_check)


def how_long_this_run_waits_for_the_suite(environment: Mapping[str, str] | None = None) -> int:
    """The seconds a delivery waits for GitHub, or the default when the deployment says nothing.

    **`0` is a real answer and is read as one.** A deployment that wants the old behaviour —
    refuse immediately rather than wait — states zero, and a test suite needs that or every
    test which touches a check would sleep. **`unlimited` is refused rather than obeyed**, like
    every other ceiling here: a wait with no end is a hang, and naming it one would be claiming
    this tool can tell a suite that is slow from a suite that will never finish.
    """
    the_environment = dict(environment) if environment is not None else dict(os.environ)
    stated = the_environment.get(THE_SETTING_NAMING_THE_WAIT)

    if stated is None or not stated.strip():
        return HOW_MANY_SECONDS_WHEN_NO_WAIT_IS_STATED

    try:
        the_wait = int(stated.strip())
    except ValueError:
        raise TheSuiteHasNotFinishedYetError(
            f"{THE_SETTING_NAMING_THE_WAIT} was read as {stated!r}, which is not a whole number of "
            "seconds. A delivery waits for as long as this says and then gives up, so a value that "
            "is not a number cannot be obeyed — and "
            f"{HOW_MANY_SECONDS_WHEN_NO_WAIT_IS_STATED} is what it is when nothing is stated."
        ) from None

    if the_wait < 0:
        raise TheSuiteHasNotFinishedYetError(
            f"{THE_SETTING_NAMING_THE_WAIT} was read as {stated!r}, which is a length of time "
            "before now. A delivery cannot have finished waiting before it began waiting."
        )

    return the_wait
