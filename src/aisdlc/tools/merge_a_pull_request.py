"""`github.merge_a_pull_request`: the step after a delivery, and the last one this system takes.

**A merge is the only thing here that changes somebody else's repository without asking them
again.** Everything before it in a delivery is an offer; this is the offer being taken up, and it
is irreversible in a way a closed issue is not.

**A merge is asked about before it is attempted, and the reason is one repeated word.** GitHub
answers *"Pull Request is not mergeable"* for a pull request that conflicts with its base — which
a run can rebase and try again — and for a base branch that is protected, which no amount of
rebasing will fix. Classifying the refusal by reading that phrase calls the second one a
conflict, and sends a person after a merge conflict on a branch that is protected on purpose. So
`mergeable` is read first and is the only thing that makes this file call something a conflict.

**The commit a merge may land is an argument, because the checks were read about a commit.** The
suite was read green for this pull request's head sha a moment earlier, and a head that moved
since — a rebase, "update branch", a second run pushing the same branch — is a commit nothing was
proved about. Handing the sha to GitHub is what makes the merge mean *this commit or nothing*, and
it is GitHub that refuses the attempt rather than this system noticing afterwards.

**`null` is its own refusal, and it is a fact GitHub states rather than a gap this tool has.**
GitHub computes a merge conflict in the background, so a pull request asked about seconds after it
was opened answers `mergeable: null`. `true` would merge whatever happened to be there; `false`
would accuse it of a conflict nobody has established.

**No credential is refused rather than attempted, and the reason is a pull request too:** a merge
is somebody else's decision being carried out, and an empty credential arrives as a 401 naming
neither the setting nor the permission.

**No merge method is chosen here.** Whether a repository merges, squashes or rebases is that
repository's setting, and a system that picked one would silently change how every repository it
delivers to records history.
"""

from __future__ import annotations

import httpx
from pydantic import BaseModel, ConfigDict, field_validator

from aisdlc.domain.repository import Repository
from aisdlc.tools.credential_error import NoCredentialError
from aisdlc.tools.github_client import THE_SETTING_NAMING_THE_CREDENTIAL
from aisdlc.tools.github_create_pull_request import what_github_said

WHERE_GITHUB_KEEPS_THE_PULL_REQUEST = "/repos/{owner}/{name}/pulls/{number}"

# **`/merge`, and the segment is the whole finding.** GitHub keeps *two* addresses under
# `/pulls/{number}`: one that reads and updates the pull request, and one that merges it. A `PUT`
# carrying `{"sha": …}` to the first is a real request to a real address, and GitHub answers it
# `404 Not Found` — so nothing about it looks wrong until the run that has spent eight gates and
# forty minutes finds out.
#
# **A run delivered a pull request and could not merge it**, with every other fact correct: the
# token carried `repo`, the pull request read `200`, `mergeable` was `true`, and the commit the
# suite went green on was in hand. Reproduced by hand against that same pull request, with that
# same token:
#
# ```text
# $ curl -X PUT .../pulls/43 -d '{"sha":"b9c3d01..."}'
# 404
# {"message": "Not Found"}
# ```
#
# **And no test noticed, because the double answers every `PUT` with a merge** — on the method and
# not on the address. So every property of this request was asserted somewhere except the one that
# decides whether the merge can happen at all.
WHERE_GITHUB_TAKES_A_MERGE = "/repos/{owner}/{name}/pulls/{number}/merge"
SECONDS_A_READ_MAY_TAKE = 10
SECONDS_A_MERGE_MAY_TAKE = 30

GITHUB_OKAY = 200
GITHUB_MERGED_IT = "merged"


class ThePullRequestCouldNotBeReadError(Exception):
    """GitHub would not say what this pull request is, so nothing is known about merging it.

    **Separate from a refusal to merge, because they are different facts about different minutes.**
    A 404 here is about the push that opened the pull request twenty minutes ago, and a person
    told "the merge was refused" would go and look at the merge rather than at the push.
    """


class ThePullRequestIsInConflictError(Exception):
    """GitHub says this pull request cannot be merged because it conflicts with its base.

    **A conflict and not a refusal, and the difference is what can be done about it.** A
    conflicting pull request can be rebased and tried again; a protected base branch cannot be
    merged into at all, and GitHub words both the same way. This is raised from the `mergeable`
    field alone, so the word "not mergeable" in a refusal is never read as a conflict.
    """


class GitHubHasNotSaidWhetherItCanBeMergedYetError(Exception):
    """GitHub is still deciding whether this pull request can be merged, and this run may not guess.

    **`null` is not `true` and is not `false`.** GitHub computes a merge conflict in the
    background, so a pull request asked about moments after it was opened answers `null`. Reading
    it as mergeable merges an unproved commit; reading it as a conflict sends a person after a
    conflict nobody has established. Asking again is the only honest move, and it is a move this
    tool does not make on the caller's behalf.
    """


class TheMergeWasRefusedByGitHubError(Exception):
    """GitHub declined the merge, and what it said is the whole of what a person can act on.

    **Quoted rather than re-interpreted.** GitHub answers 405 for a protected base branch and for
    a pull request that is not mergeable, 409 when the head moved under the merge, 410 for a
    branch that will not take it, and it words several of them alike. This system cannot tell
    those apart from the prose and will not pretend to: the status and GitHub's own sentence
    travel in the message, and the classification stays with the `mergeable` field.
    """


class APullRequestToMerge(BaseModel):
    """The pull request to merge, and the one commit a merge is allowed to land.

    **The commit is required and is not a default.** It is the sha the suite was read green on,
    and a merge that may land any commit is a merge that may land one nothing was proved about.
    `number` and not the whole address, because the endpoint is keyed by number and a string
    address would be a link parsed back into one.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    repository: Repository
    number: int
    the_commit_a_merge_may_land: str

    @field_validator("the_commit_a_merge_may_land")
    @classmethod
    def _refuse_a_merge_of_nothing_in_particular(cls, commit: str) -> str:
        """Refuse a blank commit, which is a merge allowed to land anything."""
        if not commit.strip():
            raise ValueError(
                "a merge names the commit it may land, because that is the commit the checks "
                "were read about. A blank one is a merge of whatever happens to be there"
            )
        return commit


class WhatTheMergeLanded(BaseModel):
    """The commit that is now in the base branch, and GitHub's own sentence about it.

    **What a person reads afterwards, and both halves are GitHub's answer rather than ours.** The
    commit is the fact a reader will look for in the base branch's history, and the sentence is
    carried verbatim because a system that paraphrases a remote's confirmation is a system that
    can be wrong about a merge having happened.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    commit: str
    what_github_said: str


def a_pull_request_to_merge(
    repository: Repository, number: int, the_commit_a_merge_may_land: str
) -> APullRequestToMerge:
    """The merge this run wants, named by the three facts it has and nothing it does not.

    **A builder rather than a constructor call at the call site**, so the one place that has to know
    the three facts in the right order is here: the repository the pull request is on, the number
    GitHub gave it, and the commit the checks were read about.
    """
    return APullRequestToMerge(
        repository=repository,
        number=number,
        the_commit_a_merge_may_land=the_commit_a_merge_may_land,
    )


def merge_a_pull_request(
    client: httpx.Client,
    wanted: APullRequestToMerge,
    credential: str,
) -> WhatTheMergeLanded:
    """Merge it, on the one commit the checks were read about, or say in GitHub's words why not.

    **The credential, then the pull request, then the merge — and that order is the whole
    contract.** Nothing is attempted without a credential; the pull request is asked about before
    anything is pushed at it, because `mergeable` is the only field that tells a conflict from a
    protected branch; and the merge itself carries the commit, so a head that moved under all of
    this is refused by GitHub rather than noticed here afterwards.
    """
    _refuse_a_merge_with_no_credential(credential)

    _refuse_a_pull_request_that_cannot_be_merged(
        client, _whether_github_says_it_can_be_merged(client, wanted), wanted
    )

    return _the_merge_github_performed(client, wanted, credential)


def _refuse_a_merge_with_no_credential(credential: str) -> None:
    """Refuse by name, before any request, because a 401 explains neither setting nor permission."""
    if credential.strip():
        return
    raise NoCredentialError(
        f"{THE_SETTING_NAMING_THE_CREDENTIAL} is not set, so there is no account to merge as. A "
        "merge is somebody else's decision being carried out on their repository, and nobody "
        "cannot carry one out."
    )


def _whether_github_says_it_can_be_merged(
    client: httpx.Client, wanted: APullRequestToMerge
) -> bool | None:
    """The `mergeable` field, verbatim: `True`, `False`, or `None` while GitHub is still deciding.

    **Read as three states and not two, and the third is the one this exists for.** GitHub
    computes a conflict in the background, so `null` is an answer this run may not interpret; the
    two booleans are the only two things that mean anything here, and a `200` with no field at all
    is treated as `None` rather than as permission.
    """
    answer = client.get(
        WHERE_GITHUB_KEEPS_THE_PULL_REQUEST.format(
            owner=wanted.repository.owner,
            name=wanted.repository.name,
            number=wanted.number,
        ),
        timeout=SECONDS_A_READ_MAY_TAKE,
    )
    if answer.status_code != GITHUB_OKAY:
        raise ThePullRequestCouldNotBeReadError(
            f"GitHub answered {answer.status_code} when asked whether pull request "
            f"{wanted.number} of {wanted.repository.address} can be merged, so nothing is known "
            f"about merging it. GitHub said: {what_github_said(answer)}"
        )

    what_github_said_about_it = answer.json().get("mergeable")
    if not isinstance(what_github_said_about_it, bool):
        return None
    return what_github_said_about_it


def _refuse_a_pull_request_that_cannot_be_merged(
    client: httpx.Client,
    can_it_be_merged: bool | None,
    wanted: APullRequestToMerge,
) -> None:
    """Two refusals from one field, and no merge is attempted in either case.

    **A conflict and an unfinished judgement are different facts with different remedies.** A
    conflict can be rebased and tried again; `null` means GitHub has not decided and the answer is
    to ask again. Neither is a refusal by GitHub, so neither is dressed up as one, and neither
    reaches the merge endpoint — a merge attempted against either is a merge GitHub decides
    rather than one this system decided.
    """
    del client

    if can_it_be_merged is False:
        raise ThePullRequestIsInConflictError(
            f"GitHub says pull request {wanted.number} of {wanted.repository.address} conflicts "
            f"with the branch it would join, and it cannot be merged as it stands. The commit it "
            f"would have landed is {wanted.the_commit_a_merge_may_land}. This is a conflict and "
            "not a refusal: a protected base branch is refused instead, and GitHub words the two "
            "the same way, which is why this is read from the field and not from the message"
        )

    if can_it_be_merged is None:
        raise GitHubHasNotSaidWhetherItCanBeMergedYetError(
            f"GitHub has not finished saying whether pull request {wanted.number} of "
            f"{wanted.repository.address} can be merged. It computes a merge conflict in the "
            "background and answers null until it has one, and this run will not read null as "
            "permission to merge whatever is there or as an accusation that there is a conflict"
        )


def _the_merge_github_performed(
    client: httpx.Client, wanted: APullRequestToMerge, credential: str
) -> WhatTheMergeLanded:
    """Ask for the merge of exactly this commit, and believe GitHub only if it says it merged.

    **The sha in the body is the guarantee, and GitHub's `merged` is the confirmation.** A `200`
    that says `merged: false` has not merged anything, and a run reporting a delivery from it
    would be reporting one that did not happen. Everything else is quoted: 405, 409 and 410 are
    three different problems and this system cannot tell them apart from the prose.
    """
    answer = client.put(
        WHERE_GITHUB_TAKES_A_MERGE.format(
            owner=wanted.repository.owner, name=wanted.repository.name, number=wanted.number
        ),
        json={"sha": wanted.the_commit_a_merge_may_land},
        headers={
            "Authorization": f"Bearer {credential}",
            "Accept": "application/vnd.github+json",
        },
        timeout=SECONDS_A_MERGE_MAY_TAKE,
    )
    what_github_said_about_it = what_github_said(answer)
    merged = answer.json().get(GITHUB_MERGED_IT) if answer.status_code == GITHUB_OKAY else None

    if merged is not True:
        raise TheMergeWasRefusedByGitHubError(
            f"GitHub did not merge pull request {wanted.number} of {wanted.repository.address}, so "
            f"{wanted.the_commit_a_merge_may_land} was not landed and this run's delivery is not "
            f"in the base branch. GitHub answered {answer.status_code} and said: "
            f"{what_github_said_about_it}"
        )

    return WhatTheMergeLanded(
        commit=str(answer.json()["sha"]), what_github_said=what_github_said_about_it
    )
