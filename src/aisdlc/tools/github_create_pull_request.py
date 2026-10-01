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

    # **The label goes on afterwards, because GitHub's create-pull-request endpoint ignores a
    # `labels` field.** It does not error and it does not warn: it answers 201 and opens the pull
    # request with no labels on it. A pull request *is* an issue in GitHub's data model, which is
    # why labels work on one and not the other — and why eleven assertions about the request all
    # passed while every pull request this system opened went out untagged. They were about the
    # request rather than about the pull request.
    if the_labels:
        _the_labels_go_on_afterwards(
            client, credential, wanted.repository, int(opened["number"]), the_labels
        )



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


def _the_labels_go_on_afterwards(
    client: httpx.Client,
    credential: str,
    repository: Repository,
    number: int,
    labels: list[str],
) -> None:
    """Put the project's name on a pull request that already exists, through the issues endpoint.

    **This is the only way GitHub offers.** There is no version of the create call that carries a
    label, and a pull request's labels live at `POST /repos/{owner}/{name}/issues/{number}/labels`
    because of the issue underneath it.

    **And a refusal here is not fatal, which matters more on this path than on the issue path.**
    This call happens *after* the pull request exists and its branch is on a remote, so raising
    would tell the caller a delivery failed when it succeeded — the same lie as delivering nothing,
    pointed the other way. The first version raised, and its own test said it should not. So the
    pull request stays open and untagged: untagged beats undelivered, on both paths, for the same
    reason.
    """
    answer = client.post(
        f"/repos/{repository.owner}/{repository.name}/issues/{number}/labels",
        json={"labels": labels},
        headers={
            "Authorization": f"Bearer {credential}",
            "Accept": "application/vnd.github+json",
        },
    )

    if answer.status_code in {GITHUB_OKAY, GITHUB_CREATED_IT}:
        return

    # **Nothing is raised, and the reason is that the work is already delivered.** Returning
    # quietly is not ideal — a deployment that cannot write labels would find out by noticing the
    # tag is missing — but the alternative is reporting a failure for a pull request that exists.
    a_failed_label_put_where_it_would_be_seen(
        client, credential, repository, number, labels, answer
    )


def a_failed_label_put_where_it_would_be_seen(
    client: httpx.Client,
    credential: str,
    repository: Repository,
    number: int,
    labels: list[str],
    what_github_said: httpx.Response,
) -> None:
    """Say on the pull request itself that its label never arrived, since nothing else will.

    **A comment, and not an exception, because an exception here is a lie.** The pull request is
    open and the branch is pushed by the time this is called, so a caller told the delivery failed
    would go and look for a delivery that is sitting there. A person looking at the pull request
    is exactly who would act on the missing tag, and this is the one place they will look.

    **And if even that is refused, the run carries on untagged**, because a missing label is a
    smaller loss than a delivery nobody believes happened.
    """
    answer = client.post(
        f"/repos/{repository.owner}/{repository.name}/issues/{number}/comments",
        json={
            "body": (
                f"This pull request could not be labelled `{', '.join(labels)}`, so it carries no "
                f"project tag. The work is delivered and this note is the only record that the tag "
                f"did not arrive. GitHub said: {what_github_said.text}"
            )
        },
        headers={
            "Authorization": f"Bearer {credential}",
            "Accept": "application/vnd.github+json",
        },
    )
    if answer.status_code not in {GITHUB_OKAY, GITHUB_CREATED_IT}:
        print(
            f"{labels} could not be put on pull request {number} of "
            f"{repository.owner}/{repository.name}, and saying so on the pull request was refused "
            f"too: {answer.text}",
            flush=True,
        )
