"""One directory per work item: the clone, the artifacts, and the summary.

The design note is "The project directory" in `AGENTS.md`. The path is derived rather
than chosen, because a run resumes from a checkpoint and a resume must find the directory
the first run made.
"""

from __future__ import annotations

import os
from pathlib import Path

from aisdlc.domain.work_item import WorkItem

# Where a run's directories go when a deployment has not said otherwise. **Beside the process and
# not under `$HOME`** — a person who runs this twice should find two directories they can delete,
# and a hidden one in their home directory is a directory they will not find.
WHERE_PROJECTS_LIVE_BY_DEFAULT = "aisdlc-projects"


class NoProjectsRootError(Exception):
    """The rule is in `the_project_directory_of`, and only it may say the rule broke."""


def where_projects_live() -> Path:
    """The root every run's directory hangs off, from `AISDLC_PROJECTS_DIR` or from here.

    **The one reader of this setting, and the one place it is defaulted.** A deployment that means
    its projects somewhere particular says so; a deployment that does not gets them in a named
    directory beside it. Reading it here rather than in each caller is what makes a deployment
    change one edit rather than a search, and it is also what makes the register able to sit
    beside the runs it is recording.
    """
    the_setting = os.environ.get("AISDLC_PROJECTS_DIR")
    if the_setting:
        return Path(the_setting)
    return Path.cwd() / WHERE_PROJECTS_LIVE_BY_DEFAULT


def the_project_directory_of(work_item: WorkItem, projects_root: Path | None) -> Path:
    """The one directory a work item's run happens in.

    Refused rather than defaulted, and refused here rather than where the root is read, so
    that every caller is covered by the same refusal instead of by its own care.
    """
    if projects_root is None:
        raise NoProjectsRootError("AISDLC_PROJECTS_DIR is not set")

    return (
        projects_root
        / work_item.repository.owner
        / work_item.repository.name
        / work_item.work_item_id
    )


def the_clone_directory_of(work_item: WorkItem, projects_root: Path | None) -> Path:
    """Where the clone goes, inside the project directory."""
    return the_project_directory_of(work_item, projects_root) / "repository"
