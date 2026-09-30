"""The client the GitHub tools use, and the only place a credential is read.

`github.read_file` and `github.clone_repository` take a client as an argument so their
tests can run against a transport that answers without a network. This module is the
other half: the one place a real client is built, so there is one place a credential is
read and one place it can leak.
"""

from __future__ import annotations

import os

import httpx
from pydantic import BaseModel

from aisdlc.domain.repository import Repository

GITHUBS_PUBLIC_API = "https://api.github.com"
GITHUBS_PUBLIC_CLONE_PREFIX = "https://github.com"
SECONDS_A_GITHUB_CALL_MAY_TAKE = 10


def the_read_address_of(repository: Repository, path: str, ref: str) -> str:
    """Where GitHub keeps one file of one repository at one ref."""
    return (
        f"{GITHUBS_PUBLIC_API}/repos/{repository.owner}/{repository.name}"
        f"/contents/{path}?ref={ref}"
    )


def the_clone_url_of(repository: Repository) -> str:
    """Where GitHub keeps a repository, as a clone URL.

    No credential in it, ever, and this function does not read the environment at all so
    that it cannot be made to. A URL with a token in it is a URL git will echo back on
    failure, and that echo is what our error messages are built from.
    """
    return f"{GITHUBS_PUBLIC_CLONE_PREFIX}/{repository.owner}/{repository.name}.git"


class Addresses(BaseModel):
    """Where a clone is fetched from, and where the code it carries came from.

    Two facts, and one string cannot hold both. The first is where this system's copy
    lives, which it may push to. The second is where the code was written, which it may
    only read — and recording it is what lets a reader tell a copy from the original
    months later, by running one command.
    """

    fetch_from: str
    origin_of_the_code: str


def the_addresses_of(came_from: Repository, a_copy: Repository) -> Addresses:
    """The two addresses of a clone, one for each of the two things it is."""
    return Addresses(
        fetch_from=the_push_address_of(a_copy),
        origin_of_the_code=the_clone_url_of(came_from),
    )


def the_push_address_of(repository: Repository) -> str:
    """Where a repository is *written* to, which is a different place from where it is read.

    Reading a public repository needs no credential, so the clone is addressed over HTTPS
    and a run on a machine with no key still works. Writing always needs one, and the
    address that carries a key is SSH. They are separate functions rather than one
    function with a flag because the choice has to be visible: when both were the same
    address, a delivery had to be done by hand because git's HTTPS credentials belonged to
    some other account, and the reason appeared nowhere.
    """
    return f"git@github.com:{repository.owner}/{repository.name}.git"


def the_address_of(repository: Repository) -> str:
    """Where a repository lives, for a human to be shown."""
    return f"{GITHUBS_PUBLIC_CLONE_PREFIX}/{repository.owner}/{repository.name}"


THE_SETTING_NAMING_THE_CREDENTIAL = "GITHUB_TOKEN"


def the_credential() -> str:
    """The credential this system authenticates with, or nothing.

    Read in one place so that the tools which require it and the client that sends it
    cannot disagree about its name, and so a caller can be told which setting to change
    instead of being handed a 401.
    """
    return os.environ.get(THE_SETTING_NAMING_THE_CREDENTIAL, "")


def a_github_client() -> httpx.Client:
    """A client for GitHub, authorized only if the environment says how.

    No header at all when there is no credential, which is the ordinary case: §4 promises
    an arbitrary *public* repository, and `Authorization: Bearer ` with an empty value is
    a claim about the caller that is false, and which a host may answer differently from
    a request that makes no claim at all.

    The timeout is set here rather than per request so that a tool added later is bounded
    without remembering. `github.read_file` also sets one on its own request, which is
    deliberate: a bound that depends on a caller is not a bound.
    """
    headers: dict[str, str] = {}
    credential = the_credential()

    if credential:
        headers["Authorization"] = f"Bearer {credential}"

    return httpx.Client(
        base_url=GITHUBS_PUBLIC_API,
        headers=headers,
        timeout=SECONDS_A_GITHUB_CALL_MAY_TAKE,
    )
