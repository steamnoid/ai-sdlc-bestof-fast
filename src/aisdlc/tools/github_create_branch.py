"""`github.create_branch`: the first thing this system does that writes to a repository.

A delivery is a git operation on a checkout this run already made, so it goes through
`run_command` rather than through the GitHub API — the clone is here, the commit is in it,
and pushing it is what git is for. That also means a missing git is reported as a missing
git rather than as a refused push, which are different things needing different answers.

The remote is asked about the branch *before* it is pushed to. A branch that is already
there is refused whatever it points at, so this can never move a branch somebody else is
using, and a branch that already holds the commit is refused as not-a-push rather than
reported as one.
"""

from __future__ import annotations

from pydantic import BaseModel

from aisdlc.domain.repository import Repository
from aisdlc.tools.github_client import the_push_address_of
from aisdlc.tools.github_clone_repository import ClonedRepository
from aisdlc.tools.run_command import ACommand, the_outcome_of

THE_REMOTE = "origin"


class NothingToPushError(Exception):
    """The rule is in `create_a_branch_on_a_remote`, and only it may say the rule broke."""


class RemoteRefusedThePushError(Exception):
    """The rule is in `create_a_branch_on_a_remote`, and only it may say the rule broke."""


class BranchToPush(BaseModel):
    """The branch a run wants on the remote, and the commit it is to point at."""

    name: str
    commit: str


class PushedBranch(BaseModel):
    """A branch that is on the remote, named so a caller can go and look at it."""

    name: str
    address: str


def a_branch_to_push(clone: ClonedRepository, name: str) -> BranchToPush:
    """The branch a run wants, at the commit its clone is standing on."""
    return BranchToPush(name=name, commit=clone.commit)


def create_a_branch_on_a_remote(
    clone: ClonedRepository, branch: BranchToPush, repository: Repository
) -> PushedBranch:
    """Put the branch on the remote, or say why it did not go.

    Asked about the branch first, because a push that has already landed is not something
    to undo. `ls-remote` is the question to ask — it reads the remote without changing it,
    which is what makes the refusal possible before the damage rather than after it.
    """
    already_there = the_outcome_of(
        ACommand(
            program="git",
            arguments=["ls-remote", "--heads", THE_REMOTE, branch.name],
            working_directory=str(clone.path),
        )
    )

    if already_there.standard_output.strip():
        raise NothingToPushError(
            f"{branch.name} is already on {THE_REMOTE}, so there is nothing to push. It "
            "either already holds the commit this run produced or it is somebody else's "
            "branch, and this will not move a branch it did not create."
        )

    pushed = the_outcome_of(
        ACommand(
            program="git",
            arguments=["push", THE_REMOTE, f"HEAD:refs/heads/{branch.name}"],
            working_directory=str(clone.path),
        )
    )

    if pushed.exit_code != 0:
        raise RemoteRefusedThePushError(
            f"{THE_REMOTE} did not take {branch.name}, so the push did not happen. git "
            f"said: {pushed.standard_error.strip() or pushed.standard_output.strip()}"
        )

    return PushedBranch(
        name=branch.name, address=the_push_address_of(repository)
    )
