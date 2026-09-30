"""`github.fork_repository`: the account's copy of a repository we may write to.

A fork is how this system gets a repository it is allowed to push to. Reading a public
repository needs no permission, and a pull request can be opened against it without ever
holding write access to it — so a fork is not a shortcut around the permission model, it is
the permission model's own answer for somebody who works on somebody else's code.

**Idempotent, because this runs once per source repository and a run must be able to run
twice.** A second fork attempt is not a no-op on GitHub: it is an error, or a second
repository. So the fork is asked about before it is made, and an existing one is returned
as the answer.

**The account is stated rather than derived.** Deriving it would mean asking GitHub who
the credential belongs to and trusting the answer, which is a second request and a
footgun that is invisible when it is wrong. `the_account_we_fork_into` refuses when the
setting is absent, in the same way the projects root is refused, and a caller that has not
been told an account cannot fork into a random one.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

import httpx

from aisdlc.domain.repository import Repository
from aisdlc.tools.credential_error import NoCredentialError
from aisdlc.tools.github_client import (
    Addresses,
    a_github_client,
    the_addresses_of,
    the_credential,
)
from aisdlc.tools.github_clone_repository import RepositoryToClone, a_repository_to_clone

WHERE_A_REPOSITORY_IS_FORKED = "/repos/{owner}/{name}/forks"
WHERE_A_REPOSITORY_IS_READ = "/repos/{owner}/{name}"

THE_SETTING_NAMING_THE_ACCOUNT = "AISDLC_FORK_OWNER"
THE_SETTING_NAMING_THE_CREDENTIAL = "GITHUB_TOKEN"

# GitHub's own words for "it is there", "here it is" and "I will make it". Named because
# a bare 200 in a comparison reads as a typo rather than as a decision.
GITHUB_SAYS_IT_IS_THERE = 200
GITHUB_OKAY = 201
GITHUB_ACCEPTED_A_FORK = 202


class NoAccountToForkIntoError(Exception):
    """The rule is in `the_account_we_fork_into`, and only it may say the rule broke."""


class ForkNotMadeError(Exception):
    """The rule is in `fork_a_repository`, and only it may say the rule broke."""


def the_account_we_fork_into() -> str:
    """The account whose copy of a repository this system's forks become.

    Named `owner` because that is what it is on both sides of the API: the account that
    owns the fork, and the `owner` half of the `owner/name` a repository is named by. One
    fact, one word.
    """
    account = os.environ.get(THE_SETTING_NAMING_THE_ACCOUNT, "")

    if not account.strip():
        raise NoAccountToForkIntoError(
            f"{THE_SETTING_NAMING_THE_ACCOUNT} is not set, so there is no account to fork "
            "into. A fork is an account's copy of somebody's repository, and this system "
            "is not one: it needs to be told whose copy to make."
        )

    return account


def fork_a_repository(
    source: Repository, account: str, client: httpx.Client, credential: str
) -> Repository:
    """The account's copy of `source`, made now or found already made.

    Asked before made, because asking GitHub for a second fork of a repository you have
    already forked is an error rather than a no-op, and a delivery that runs twice must
    not turn into a failed run the second time.

    The credential is refused before any request is made rather than after one comes back
    as a 401: there is no outcome to report for a request that was never sent, and a
    message naming the setting is worth more than a host's.
    """
    if not credential.strip():
        raise NoCredentialError(
            f"{THE_SETTING_NAMING_THE_CREDENTIAL} is not set, so there is no account to "
            f"make a copy in. A fork is {account}'s copy of a repository, and a copy "
            "cannot be made by nobody."
        )

    the_copy = Repository(owner=account, name=source.name)

    if what_github_answered(client, "GET", where_a_repository_lives(account, source.name))[
        0
    ] == GITHUB_SAYS_IT_IS_THERE:
        return the_copy

    status, said = what_github_answered(
        client, "POST", where_a_repository_is_forked(source.owner, source.name)
    )
    if status not in (GITHUB_ACCEPTED_A_FORK, GITHUB_OKAY, GITHUB_OKAY):
        raise ForkNotMadeError(
            f"{source.owner}/{source.name} could not be forked into {account}, so there "
            f"is no repository to work on. GitHub said: {said}"
        )

    return the_copy


def what_github_answered(client: httpx.Client, method: str, where: str) -> tuple[int, str]:
    """The status GitHub answered with, and what it said, asked for in one request.

    Both halves, because a status code is a fact about HTTP and the message is the fact
    about the situation. A tool that keeps the first and discards the second has thrown
    away the half a person needs, and then writes its own guess in its place.
    """
    answer = client.request(method, where)

    return answer.status_code, str(answer.json().get("message", "")).strip()


def a_clone_this_system_may_write_to() -> Callable[[Repository, Path], RepositoryToClone]:
    """The request to clone a repository this run may write to, into a given place.

    Forked if it is not already ours, because a run that may not push cannot deliver
    anything, and fetching a copy it cannot write to would produce a clone that is
    useless for the one thing a clone is for here. This is the whole collaborator the
    clone node has, so every address-shaped decision lives here rather than spread
    through the graph.
    """

    def planning(source: Repository, into: Path) -> RepositoryToClone:
        our_copy = fork_a_repository(
            source, the_account_we_fork_into(), a_github_client(), the_credential()
        )
        addresses: Addresses = the_addresses_of(came_from=source, a_copy=our_copy)

        return a_repository_to_clone(our_copy, addresses, into)

    return planning


def where_a_repository_lives(owner: str, name: str) -> str:
    """Where GitHub keeps one repository, for reading it or asking whether it exists."""
    return WHERE_A_REPOSITORY_IS_READ.format(owner=owner, name=name)


def where_a_repository_is_forked(owner: str, name: str) -> str:
    """Where a fork of one repository is made."""
    return WHERE_A_REPOSITORY_IS_FORKED.format(owner=owner, name=name)

