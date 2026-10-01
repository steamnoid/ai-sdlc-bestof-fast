"""`github.create_pull_request`: the step a delivery cannot do without, or cannot do at all."""

from __future__ import annotations

import httpx
from pydantic import BaseModel, field_validator

from aisdlc.domain.repository import Repository
from aisdlc.tools.credential_error import NoCredentialError
from aisdlc.tools.the_tag_this_system_leaves_on_what_it_writes import (
    make_sure_the_tag_is_there,
    the_tag_this_system_leaves,
)

WHERE_A_PULL_REQUEST_IS_OPENED = "/repos/{owner}/{name}/pulls"
THE_SETTING_NAMING_THE_CREDENTIAL = "GITHUB_TOKEN"

# GitHub's own words for "here it is" and "I made it". Named because a bare 200 in a
# comparison reads as a typo rather than as a decision.
GITHUB_OKAY = 200
GITHUB_CREATED_IT = 201


class PullRequestNotOpenedError(Exception):
    """The rule is in `open_a_pull_request`, and only it may say the rule broke."""


class BranchOnRemote(BaseModel):
    """A branch, and whose copy of the repository it is on.

    A branch name on its own is not a branch: `aisdlc/issue-1` exists in our fork and in
    nobody else's, so a pull request that guessed its owner would open itself against a
    branch that is not there. The two halves are one fact and get one name.
    """

    owner: str
    name: str

    @field_validator("owner", "name")
    @classmethod
    def _reject_a_branch_that_is_nobody(cls, half: str) -> str:
        if not half.strip():
            raise ValueError("a branch names whose remote it is on and what it is called")
        return half


class PullRequestToOpen(BaseModel):
    """What a pull request needs named: which branch, into what, called what."""

    repository: Repository
    head: BranchOnRemote
    base: str
    title: str
    body: str

    @field_validator("base")
    @classmethod
    def _reject_a_branch_that_is_nobody(cls, branch: str) -> str:
        if not branch.strip():
            raise ValueError("a pull request names the branch it comes from and the one it joins")
        return branch


class AnOpenedPullRequest(BaseModel):
    """A pull request that exists, with the number and the address a person opens."""

    number: int
    address: str


def a_pull_request_to_open(
    repository: Repository,
    head: BranchOnRemote,
    base: str,
    title: str,
    body: str,
) -> PullRequestToOpen:
    """The pull request a run wants opened."""
    return PullRequestToOpen(
        repository=repository, head=head, base=base, title=title, body=body
    )


def open_a_pull_request(
    wanted: PullRequestToOpen, client: httpx.Client, credential: str
) -> AnOpenedPullRequest:
    """Open it, and hand back where it now lives.

    A pull request cannot be opened anonymously — it is somebody's decision to review —
    so the credential is refused before anything is attempted, the same as forking. The
    head is namespaced by its owner, because `aisdlc/issue-1` exists in our fork and in
    nobody else's, and a pull request that guessed would open itself against a branch
    that is not there.

    A pull request GitHub did not open is refused and GitHub's own words are quoted. A
    422 about a branch that is not on the remote, or a title already in use, arrives as
    prose about a cause, and a caller needs to know that nothing was delivered.
    """
    if not credential.strip():
        raise NoCredentialError(
            f"{THE_SETTING_NAMING_THE_CREDENTIAL} is not set, so there is no account to "
            "open a pull request as. A pull request is somebody's decision to review, and "
            "nobody cannot ask for one."
        )

    the_tag = the_tag_this_system_leaves(wanted.repository)
    the_labels = (
        [the_tag]
        if make_sure_the_tag_is_there(client, credential, wanted.repository, the_tag)
        else []
    )

    answer = client.post(
        WHERE_A_PULL_REQUEST_IS_OPENED.format(
            owner=wanted.repository.owner, name=wanted.repository.name
        ),
        json={
            "title": wanted.title,
            "body": wanted.body,
            "labels": the_labels,
            "head": f"{wanted.head.owner}:{wanted.head.name}",
            "base": wanted.base,
        },
    )

    if answer.status_code not in (GITHUB_CREATED_IT, GITHUB_OKAY):
        raise PullRequestNotOpenedError(
            f"a pull request from {wanted.head.owner}:{wanted.head.name} into "
            f"{wanted.base!r} was not opened, "
            f"so nothing was delivered. GitHub said: {what_github_said(answer)}"
        )

    opened = answer.json()

    return AnOpenedPullRequest(
        number=opened["number"],
        address=str(opened["html_url"]),
    )


def what_github_said(answer: httpx.Response) -> str:
    """Whatever GitHub said, so a refusal quotes it rather than replacing it.

    GitHub puts a one-line reason in `message` and the detail in `errors`, and for a
    validation failure the detail is the useful half. Both are read, because a refusal
    that says "validation failed" has told the caller nothing they did not already know.
    """
    said = str(answer.json().get("message", "")).strip()
    details = [
        str(failure.get("message", "")).strip()
        for failure in answer.json().get("errors", [])
    ]
    every_reason = "; ".join(reason for reason in [said, *details] if reason)

    return every_reason or "GitHub said nothing about why."
