"""`filesystem.list`: what a directory of the project holds.

Not recursive yet. How deep a listing goes, what it ignores, and what a symlink means
are one design question and deserve one commit, not a decision smuggled in here.
"""

from __future__ import annotations

from pydantic import BaseModel

from aisdlc.tools.filesystem_read import APathInTheProject, the_path_inside_the_project


class ProjectListing(BaseModel):
    """What a directory holds: which entries are directories, and which are files."""

    path: str
    directory_names: list[str] = []
    file_names: list[str] = []


def list_the_project(asked_for: APathInTheProject) -> ProjectListing:
    """The directory asked for, and what is in it."""
    where = the_path_inside_the_project(asked_for)

    return ProjectListing(
        path=asked_for.path,
        directory_names=[
            entry.name for entry in where.iterdir() if entry.is_dir()
        ],
        file_names=[entry.name for entry in where.iterdir() if entry.is_file()],
    )
