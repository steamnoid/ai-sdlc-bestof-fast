"""`an_inspection_of`: the text a model is asked to reason about a repository by.

The substrate is a clone, so this tool's question is not how to fetch a repository but
*which files of it* a model should be shown. It is a selection, and the selection is the
whole design: a repository has thousands of files, a model has a context, and whatever
decides between them must decide the same way every time or two runs of one work item
are not comparable and a report cannot be checked against the repository it describes.

The selection is what `DiscoveryReport` asks for and no more. The manifests say which
language and which build system, the README says what the project is for, the CI
configuration says whether there is any, and the top-level listing says what the project
is made of. Source files are not in it, because a discovery report is a summary of a
repository's shape and not a copy of its contents.

Everything is read through `read_file_in_the_project`, with the clone as the boundary.
That is not ceremony: a workflow file is a file a pull request can add, and a symlink
named `.github/workflows/ci.yml` pointing at `/etc` would otherwise be followed without
anything noticing.

A file that is not there is left out. That is what makes `ci_system: None` reachable
from a real run — a tool that failed on a repository without CI would leave the model
with nothing, and a model with nothing guesses, which is the exact reason `ci_system` is
optional.
"""

from __future__ import annotations

from pathlib import Path

from aisdlc.tools.filesystem_read import (
    PathNotInTheProjectError,
    a_path_in_the_project,
    read_file_in_the_project,
)
from aisdlc.tools.github_clone_repository import ClonedRepository

MANIFESTS = (
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "Gemfile",
    "composer.json",
    "Makefile",
)

READMES = ("README.md", "README.rst", "README.txt", "README")

# Named separately rather than as a tuple of pairs: a missing comma there unpacks a
# string into characters, and a reader has no way to see the difference.
WHERE_WORKFLOWS_LIVE = ".github/workflows"
SUFFIXES_A_WORKFLOW_MAY_HAVE = (".yml", ".yaml")
CI_AT_THE_ROOT = (
    ".gitlab-ci.yml",
    ".circleci/config.yml",
    "azure-pipelines.yml",
    "Jenkinsfile",
)

A_LIMIT_ON_A_SINGLE_FILE = 20_000


def an_inspection_of(clone: ClonedRepository) -> str:
    """The files a model is shown, and the listing that gives them context."""
    inside = clone.path

    sections = [
        _what_the_project_is(clone),
        _the_top_level_listing(inside),
        *_the_contents_of(inside, "manifests", MANIFESTS),
        *_the_contents_of(inside, "readme", READMES),
        *_the_ci_configuration(inside),
    ]

    return "\n\n".join(section for section in sections if section)


def _what_the_project_is(clone: ClonedRepository) -> str:
    """Which repository, which commit, which branch — because every claim is about one.

    A model told about a repository without being told which one will answer in general
    terms, and the report it produces will be about a repository that looks like this
    one. The commit is here for the same reason it is in `ClonedRepository`: every later
    reference in the run is about a specific one.
    """
    return (
        "# The repository under inspection\n\n"
        f"clone at {clone.path}\n"
        f"branch: {clone.ref}\n"
        f"commit: {clone.commit}"
    )


def _the_top_level_listing(inside: Path) -> str:
    """What the project is made of, at one level.

    One level and not a tree, because the point is to name the shape rather than to
    enumerate it, and a tree of a large repository is a wall of directory names that
    answers nothing a summary cannot say more cheaply.
    """
    directories = sorted(entry.name for entry in inside.iterdir() if entry.is_dir())
    files = sorted(entry.name for entry in inside.iterdir() if entry.is_file())

    return (
        "## What is at the top level\n\n"
        f"directories: {', '.join(directories) if directories else 'none'}\n"
        f"files: {', '.join(files) if files else 'none'}"
    )


def _the_contents_of(inside: Path, what: str, names: tuple[str, ...]) -> list[str]:
    """Each named file that exists, with its text, under a heading naming it."""
    sections: list[str] = []

    for name in names:
        section = _the_section(inside, name, what)
        if section:
            sections.append(section)

    return sections


def _the_ci_configuration(inside: Path) -> list[str]:
    """Every CI file, not just the first.

    A repository may have both a workflow directory and a config file at the root, and
    which one actually runs is not ours to assume. The workflow directory is globbed
    rather than listed because the names in it belong to the repository.
    """
    sections: list[str] = []

    if (inside / WHERE_WORKFLOWS_LIVE).is_dir():
        for a_workflow in sorted((inside / WHERE_WORKFLOWS_LIVE).iterdir()):
            if a_workflow.is_file() and a_workflow.suffix in SUFFIXES_A_WORKFLOW_MAY_HAVE:
                section = _the_section(
                    inside,
                    f"{WHERE_WORKFLOWS_LIVE}/{a_workflow.name}",
                    "CI configuration",
                )
                if section:
                    sections.append(section)

    sections.extend(_the_contents_of(inside, "CI configuration", CI_AT_THE_ROOT))

    return sections


def _the_section(inside: Path, name: str, what: str) -> str | None:
    """One file's text, or nothing at all when the file is not there.

    Reading goes through the confined reader with the clone as the boundary, so a file
    that turns out to be a symlink out of the clone is refused rather than followed.
    A file too large to be worth the context is named and left out, because a truncated
    manifest is a manifest that lies about its own contents.
    """
    try:
        read = read_file_in_the_project(
            a_path_in_the_project(project_directory=inside, path=name)
        )
    except PathNotInTheProjectError:
        return None

    if len(read.text) > A_LIMIT_ON_A_SINGLE_FILE:
        return f"## {name}\n\n(omitted: {len(read.text)} characters, too large to read)"

    return f"## {name}\n\n{read.text}"

