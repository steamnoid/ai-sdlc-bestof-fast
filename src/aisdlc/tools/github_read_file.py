"""`github.read_file`: one text file out of one public repository.

Typed in and typed out, because §14 says a contract is a Pydantic model and §13 says a
tool owes one at each end. The two models here are deliberately different things:
`FileToRead` is the request, and `RepositoryFile` is what came back, which is the path
and the text and nothing inferred about it.

The client is an argument rather than something constructed here, so a test can supply
a transport that answers without a network and without a credential. That is the seam,
and it is an argument because the alternative — a module-level client — would be a
global that a test has to reach into.
"""

from __future__ import annotations

import base64

import httpx
from pydantic import BaseModel

from aisdlc.domain.repository import Repository

SECONDS_A_READ_MAY_TAKE = 10
# GitHub's own word for "no such thing here", kept named because the refusal below
# is the only place this tool interprets it.
GITHUB_SAYS_IT_IS_NOT_THERE = 404
WHERE_GITHUB_KEEPS_A_FILE = "/repos/{owner}/{name}/contents/{path}"


class PathNotInRepositoryError(Exception):
    """The rule is in `read_file`, and this is the only thing that may say it broke."""


class FileToRead(BaseModel):
    """The request: which file, of which repository, at which ref."""

    repository: Repository
    path: str
    ref: str = "main"


class RepositoryFile(BaseModel):
    """A file and what was in it. The path is kept as it was asked for."""

    path: str
    text: str


def a_file_to_read(repository: Repository, path: str, ref: str = "main") -> FileToRead:
    """The request for one file of one repository."""
    return FileToRead(repository=repository, path=path, ref=ref)


def read_file(request: FileToRead, client: httpx.Client) -> RepositoryFile:
    """The file asked for, or the reason it is not there."""
    where = WHERE_GITHUB_KEEPS_A_FILE.format(
        owner=request.repository.owner,
        name=request.repository.name,
        path=request.path,
    )

    response = client.get(
        where,
        params={"ref": request.ref},
        timeout=SECONDS_A_READ_MAY_TAKE,
    )

    if response.status_code == GITHUB_SAYS_IT_IS_NOT_THERE:
        raise PathNotInRepositoryError(
            f"{request.path!r} is not in {request.repository.owner}/"
            f"{request.repository.name} at {request.ref!r}, or the repository is not "
            "public. Nothing was read, and nothing may be concluded from the file that "
            "was asked for."
        )

    answered = response.json()

    return RepositoryFile(
        path=request.path,
        text=base64.b64decode(answered["content"]).decode("utf-8"),
    )
