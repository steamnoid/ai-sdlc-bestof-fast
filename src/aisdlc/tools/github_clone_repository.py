"""`github.clone_repository`: the operation §12's tool list omits and the pipeline needs.

The design note is "The project directory" in `AGENTS.md`: one directory per work item,
the clone inside it, every agent of the run reading that one clone. So the tool's whole
job is to produce a checkout somewhere specific and say what it got.

A full clone, not `--depth 1`, and the reason is what the run does with the history: a
diff against a base, `git log` for how a file got the way it is, `git blame` for who
touched it. A shallow clone answers none of those, and the cheapest clone is a false
economy that gets paid at the first review.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from aisdlc.domain.repository import Repository
from aisdlc.tools.github_client import Addresses
from aisdlc.tools.run_command import ACommand, the_outcome_of


class DestinationNotEmptyError(Exception):
    """The rule is in `clone_repository`, and this is the only thing that may say it broke."""


class RepositoryNotFoundError(Exception):
    """The rule is in `clone_repository`, and this is the only thing that may say it broke.

    Promised by the glossary since Phase 1 and raised here for the first time, because
    this is where a run learns that a repository it was asked to work on is not there.
    Extracted to its own module when a second tool raises it, for the same reason
    `LlmConfigurationError` has one.
    """


class RepositoryToClone(BaseModel):
    """The request: which repository, from where it is fetched, and where it lands."""

    repository: Repository
    addresses: Addresses
    into: Path


class ClonedRepository(BaseModel):
    """A checkout on disk, and the commit and branch it is standing on."""

    path: Path
    ref: str
    commit: str


def a_repository_to_clone(
    repository: Repository, addresses: Addresses, into: Path
) -> RepositoryToClone:
    """The request to clone one repository into one place."""
    return RepositoryToClone(repository=repository, addresses=addresses, into=into)


def clone_repository(request: RepositoryToClone) -> ClonedRepository:
    """The clone, and what it turned out to contain.

    The destination is checked before `git` runs, not after. A refusal that arrives once
    the damage is done is not a refusal, and `git` cannot be trusted to refuse in our
    terms — pointed at a directory that already holds a run's edits it fails, and blames
    the source, which is a statement about the wrong thing entirely.
    """
    if _the_destination_already_holds_something(request.into):
        raise DestinationNotEmptyError(
            f"{request.into} already holds something, and a clone is not written over a "
            "directory with work in it. A run resumes, so this directory is derived from "
            "the work item and may already exist: the work there is the state the resume "
            "was supposed to find."
        )

    request.into.parent.mkdir(parents=True, exist_ok=True)

    finished = the_outcome_of(
        ACommand(
            program="git",
            arguments=["clone", request.addresses.fetch_from, str(request.into)],
        )
    )

    if finished.exit_code != 0:
        raise RepositoryNotFoundError(
            f"{request.repository.owner}/{request.repository.name} could not be cloned "
            f"from {request.addresses.fetch_from!r}. git said: {finished.standard_error.strip()}"
        )

    _the_clone_records_where_the_code_came_from(request)

    return ClonedRepository(
        path=request.into,
        ref=_the_ref_of(request.into),
        commit=_the_commit_of(request.into),
    )


def _the_clone_records_where_the_code_came_from(request: RepositoryToClone) -> None:
    """Name where the code came from, so a copy can be told from the original.

    `git clone` sets `origin` and nothing else, so a clone of this system's copy would
    carry no memory of what it is a copy of. `upstream` is what a reader runs `git remote
    -v` to see, and it is the difference between a fork and a mystery. Set after the
    clone rather than before because there is no checkout to add a remote to until there
    is one.
    """
    the_outcome_of(
        ACommand(
            program="git",
            arguments=[
                "remote",
                "add",
                "upstream",
                request.addresses.origin_of_the_code,
            ],
            working_directory=str(request.into),
        )
    )


def _the_destination_already_holds_something(destination: Path) -> bool:
    """Whether cloning there would land on top of something.

    A directory that does not exist yet is the ordinary case — a run's first pass has
    nothing — and an existing but empty one is the same situation after an interrupted
    run. Anything else is somebody's state.
    """
    if not destination.exists():
        return False
    return any(destination.iterdir())


def _the_commit_of(checkout: Path) -> str:
    """The commit the clone is standing on, read from the clone and not remembered."""
    return the_outcome_of(
        ACommand(program="git", arguments=["rev-parse", "HEAD"], working_directory=str(checkout))
    ).standard_output.strip()


def _the_ref_of(checkout: Path) -> str:
    """The branch the clone is standing on, which is not always the branch asked for.

    Cloning a detached ref leaves no branch behind, and reporting a branch there would
    be a fiction: `git rev-parse --abbrev-ref HEAD` says `HEAD`, which is exactly the
    honest answer for a checkout that is not on one.
    """
    return the_outcome_of(
        ACommand(
            program="git",
            arguments=["rev-parse", "--abbrev-ref", "HEAD"],
            working_directory=str(checkout),
        )
    ).standard_output.strip()
