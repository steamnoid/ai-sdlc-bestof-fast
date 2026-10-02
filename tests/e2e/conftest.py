"""A real repository for two real agents to disagree about.

**A clone of this repository, built from the checkout on disk.** No network, and no
credential that is not the model's: the bare origin is this working tree, so the agents read the
code this project actually has rather than a fixture written to be convenient. That matters for
the questions being asked — whether the security analyst's signal names a module the
architecture analyst listed is only an interesting question when the modules are real.

**One clone per test, so one parameter cannot see another's files.** Every parametrised case
builds its own bare repo and clones it into its own `tmp_path`. Nothing process-wide is opened
along the way: no register, no project directory, no checkpoint — which is what makes the
isolation in this tier free rather than something to maintain.

**The commit is fixed to whatever was on disk when the test started**, and it is recorded on the
`ClonedRepository`, because an agent citing a file has to be citing a file of *this* checkout and
not of whatever `main` pointed at five minutes later.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from aisdlc.domain.repository import Repository
from aisdlc.tools.github_client import Addresses
from aisdlc.tools.github_clone_repository import (
    ClonedRepository,
    a_repository_to_clone,
    clone_repository,
)

THE_REPOSITORY_THIS_CLONE_IS_OF = Repository(
    owner="steamnoid", name="ai-sdlc-bestof-fast-selfaware"
)
WHERE_THIS_REPOSITORY_IS = Path(__file__).resolve().parents[2]


def _git(where: Path, *what: str) -> str:
    """One git call, and a readable failure rather than a CalledProcessError."""
    what_happened = subprocess.run(
        ["git", *what], cwd=where, capture_output=True, text=True, check=False
    )
    if what_happened.returncode != 0:
        pytest.fail(f"git {' '.join(what)} in {where} failed: {what_happened.stderr}")
    return what_happened.stdout


@pytest.fixture
def a_clone_of_this_repository(tmp_path: Path) -> ClonedRepository:
    """A bare origin made from the checkout, and a clone of it. Local either way.

    **`--bare` and a clone, rather than handing an agent the working tree.** An agent that writes
    anything — and the implementer writes — would be editing the tree the test is running in, and
    the next parametrised case would read the previous case's change as the repository's own.
    """
    the_bare = tmp_path / "the-origin.git"

    _git(
        tmp_path,
        "clone",
        "--bare",
        "--no-hardlinks",
        str(WHERE_THIS_REPOSITORY_IS),
        str(the_bare),
    )

    return clone_repository(
        a_repository_to_clone(
            THE_REPOSITORY_THIS_CLONE_IS_OF,
            Addresses(fetch_from=str(the_bare), origin_of_the_code=str(the_bare)),
            tmp_path / "a-clone",
        )
    )
