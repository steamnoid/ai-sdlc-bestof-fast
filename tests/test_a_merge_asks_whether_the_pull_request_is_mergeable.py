"""A merge is asked about before it is attempted, and a refusal is never read as a conflict.

**The two mistakes this file exists to prevent, and both of them are one word.** GitHub says
*"Pull Request is not mergeable"* in two different situations that call for opposite responses: a
pull request that **conflicts** with its base, which a run can rebase and try again, and a base
branch that is **protected** and refuses merges, which no amount of rebasing will fix. A tool that
classified the refusal by reading that phrase called the second one a conflict, and a person
reading the message went looking for a merge conflict that did not exist.

**So the classification comes from a field and not from prose.** `mergeable` is read from the pull
request *before* the merge is attempted, and `mergeable: false` is the only thing this file calls
a conflict. A refusal by the merge itself is a refusal whatever it is worded like, and it is
quoted so a person can read the reason GitHub gave.

**The commit a merge may land is an argument, because the checks were read about a commit.** The
suite was read green for the head sha of this pull request a moment ago; a head that has moved
since — a rebase, a second run pushing the same branch, somebody clicking "update branch" — is a
commit nothing was proved about. Passing that sha to GitHub is what turns "merge this" into
"merge this commit or nothing", and GitHub refuses the attempt itself rather than this system
having to notice afterwards.

**A `null` mergeability is its own refusal.** GitHub computes a merge conflict in the background,
so a pull request asked about seconds after it was opened answers `mergeable: null`. Reading that
as `true` would merge whatever is there; reading it as `false` would call it a conflict it has not
decided about. It is the one case where the honest answer is "ask again in a moment".
"""

from __future__ import annotations

import httpx
import pytest

from aisdlc.domain.repository import Repository
from aisdlc.tools.credential_error import NoCredentialError
from aisdlc.tools.github_create_pull_request import AnOpenedPullRequest
from aisdlc.tools.merge_a_pull_request import (
    APullRequestToMerge,
    GitHubHasNotSaidWhetherItCanBeMergedYetError,
    TheMergeWasRefusedByGitHubError,
    ThePullRequestCouldNotBeReadError,
    ThePullRequestIsInConflictError,
    merge_a_pull_request,
)

A_REPOSITORY = Repository(owner="steamnoid", name="wellbeing-tracker-public")
A_PULL_REQUEST = AnOpenedPullRequest(number=7, address="https://github.invalid/x/y/pull/7")
THE_COMMIT_THE_SUITE_WENT_GREEN_ON = "1" * 40
A_CREDENTIAL = "a-token"


def _a_pull_request_to_merge() -> APullRequestToMerge:
    return APullRequestToMerge(
        repository=A_REPOSITORY,
        number=A_PULL_REQUEST.number,
        the_commit_a_merge_may_land=THE_COMMIT_THE_SUITE_WENT_GREEN_ON,
    )


def _a_github_answering(
    mergeable: bool | None,
    what_the_merge_answers: int = 200,
    what_github_says: str = "Pull Request successfully merged",
) -> tuple[httpx.Client, list[httpx.Request]]:
    """A GitHub that will answer one pull request and then one merge attempt."""
    what_it_was_asked: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        what_it_was_asked.append(request)
        if request.method == "PUT":
            return httpx.Response(
                what_the_merge_answers,
                json={
                    "sha": THE_COMMIT_THE_SUITE_WENT_GREEN_ON,
                    "merged": what_the_merge_answers == 200,
                    "message": what_github_says,
                },
            )
        return httpx.Response(
            200,
            json={
                "number": A_PULL_REQUEST.number,
                "head": {"sha": THE_COMMIT_THE_SUITE_WENT_GREEN_ON},
                "mergeable": mergeable,
            },
        )

    return (
        httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(answer)),
        what_it_was_asked,
    )


def test_a_merge_lands_the_commit_the_suite_went_green_on() -> None:
    """The sha travels in the request, and what came back is the commit that landed.

    **Both halves, because either on its own is half a record.** The sha in the body is what makes
    GitHub refuse a head that moved, and the sha GitHub answers with is what goes on the card —
    a person reading the run in a month needs to know which commit is in the base branch.
    """
    a_client, what_it_was_asked = _a_github_answering(mergeable=True)

    what_the_merge_landed = merge_a_pull_request(
        a_client, _a_pull_request_to_merge(), A_CREDENTIAL
    )

    the_merge_attempts = [asked for asked in what_it_was_asked if asked.method == "PUT"]
    assert len(the_merge_attempts) == 1, (
        f"the merge was attempted {len(the_merge_attempts)} times: {what_it_was_asked}"
    )
    assert THE_COMMIT_THE_SUITE_WENT_GREEN_ON in the_merge_attempts[0].read().decode(), (
        "the commit the suite was read green on did not travel with the merge, so a head that "
        "moved between the two would be merged on a verdict about a commit nobody proved"
    )
    assert what_the_merge_landed.commit == THE_COMMIT_THE_SUITE_WENT_GREEN_ON
    assert what_the_merge_landed.what_github_said == "Pull Request successfully merged"


def test_a_merge_with_no_credential_is_refused_before_anything_is_attempted() -> None:
    """A merge is somebody else's decision being carried out, and nobody cannot carry it out.

    **Nothing is attempted**, and the test is that: a request that went out with no credential
    would be answered with a 401 that names neither the setting nor the permission, and the
    operator reading it would be sent to look for a token that was never the problem.
    """
    a_client, what_it_was_asked = _a_github_answering(mergeable=True)

    with pytest.raises(NoCredentialError):
        merge_a_pull_request(a_client, _a_pull_request_to_merge(), "   ")

    assert what_it_was_asked == [], (
        f"GitHub was asked something before the credential was checked: {what_it_was_asked}"
    )


def test_a_pull_request_github_says_cannot_be_merged_is_a_conflict_and_not_a_refusal() -> None:
    """`mergeable: false` is a conflict, and no merge is attempted on the strength of it.

    **The check comes first, and the test asserts the absence of the attempt.** A tool that merged
    first and read the answer afterwards would learn the same fact and could not tell it apart
    from a protected branch; and a run that pushed a merge at a pull request known to conflict
    would have GitHub decide, which is a worse way to learn it than being told.
    """
    a_client, what_it_was_asked = _a_github_answering(mergeable=False)

    with pytest.raises(ThePullRequestIsInConflictError) as the_refusal:
        merge_a_pull_request(a_client, _a_pull_request_to_merge(), A_CREDENTIAL)

    assert not [asked for asked in what_it_was_asked if asked.method == "PUT"], (
        "a merge was attempted against a pull request GitHub had already said cannot be merged"
    )
    assert THE_COMMIT_THE_SUITE_WENT_GREEN_ON in str(the_refusal.value), (
        "the conflict does not name the commit, so a person cannot tell which commit conflicted"
    )


def test_a_refusal_wording_the_same_as_a_conflict_is_still_a_refusal() -> None:
    """"Pull Request is not mergeable" is also what a protected base branch answers.

    **The exact confusion this file is for.** GitHub words both the same way, so a tool that
    classified by the phrase would call a protected branch a conflict — and a person would go and
    look for a merge conflict on a branch that is protected on purpose. Here the pull request is
    `mergeable` and the merge itself is refused, so it is a refusal, and GitHub's sentence is
    quoted rather than re-interpreted.
    """
    a_client, _ = _a_github_answering(
        mergeable=True,
        what_the_merge_answers=405,
        what_github_says="Pull Request is not mergeable",
    )

    with pytest.raises(TheMergeWasRefusedByGitHubError) as the_refusal:
        merge_a_pull_request(a_client, _a_pull_request_to_merge(), A_CREDENTIAL)

    assert "Pull Request is not mergeable" in str(the_refusal.value)


def test_a_head_that_moved_while_the_suite_was_being_read_is_refused_with_githubs_reason() -> None:
    """The sha is what catches it, and GitHub is the one that catches it.

    **This is the reason the commit is an argument.** A rebase after the suite was read green
    leaves a head that was never proved, and the merge endpoint refuses the attempt rather than
    this system having to notice a sha that no longer matches. The refusal quotes the reason
    rather than saying the commit moved, which is this system's guess at GitHub's sentence.
    """
    a_client, _ = _a_github_answering(
        mergeable=True,
        what_the_merge_answers=409,
        what_github_says="Head branch was modified. Review and try the merge again.",
    )

    with pytest.raises(TheMergeWasRefusedByGitHubError) as the_refusal:
        merge_a_pull_request(a_client, _a_pull_request_to_merge(), A_CREDENTIAL)

    assert "Head branch was modified" in str(the_refusal.value)


def test_a_pull_request_github_has_not_finished_judging_is_asked_about_again() -> None:
    """`mergeable: null` is neither true nor false, and a run may act on neither.

    **GitHub computes a conflict in the background**, so a pull request asked about seconds after
    it was opened answers `null`. Reading that as mergeable would merge whatever happened to be
    there; reading it as a conflict would send a person after a conflict GitHub has not decided
    about. Both halves of the test matter: the refusal, and the fact that no merge was attempted.
    """
    a_client, what_it_was_asked = _a_github_answering(mergeable=None)

    with pytest.raises(GitHubHasNotSaidWhetherItCanBeMergedYetError):
        merge_a_pull_request(a_client, _a_pull_request_to_merge(), A_CREDENTIAL)

    assert not [asked for asked in what_it_was_asked if asked.method == "PUT"], (
        "a merge was attempted against a pull request GitHub had not finished judging"
    )


def test_a_github_that_will_not_answer_about_the_pull_request_is_refused() -> None:
    """A 404 on a pull request this system opened twenty minutes ago is a fact about the push."""
    a_client, _ = _a_github_answering(mergeable=True)
    a_client = httpx.Client(
        base_url="https://api.github.com",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(404, json={"message": "Not Found"})
        ),
    )

    with pytest.raises(ThePullRequestCouldNotBeReadError):
        merge_a_pull_request(a_client, _a_pull_request_to_merge(), A_CREDENTIAL)
