"""`filesystem.read`: one file of the project, as text.

The substrate is a clone on local disk ("The project directory" in `AGENTS.md`), so this
and `filesystem.list` are the only tools an agent uses to read code.

The tool is handed a project directory and reads inside it. That is the whole security
argument: an agent reasoning about somebody else's pull request has no business reading
the machine's credentials, and a project directory is the boundary that stops it.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class PathOutsideTheProjectError(Exception):
    """The rule is in `read_file_in_the_project`, and this is the only thing to say it broke."""


class PathNotInTheProjectError(Exception):
    """The rule is in `read_file_in_the_project`, and this is the only thing to say it broke."""


#: The longest a single path component may be, in bytes, on the filesystems this runs on.
#: `NAME_MAX` is 255 on ext4, APFS and NTFS. This is a *bound*, not a promise of portability:
#: a filesystem may allow less, and the point is that a name this long is refused here rather
#: than discovered at `stat`, where the operating system raises instead of answering.
THE_LONGEST_A_COMPONENT_MAY_BE = 255

#: Characters that may not appear in a path at all. A NUL ends a C string and has done so
#: since before this was written; the rest are control characters, which no filesystem this
#: runs on accepts and which no model has ever meant.
A_CHARACTER_A_PATH_MAY_NOT_HOLD = frozenset(chr(code) for code in range(32)) | {chr(127)}


class APathNotAPathError(Exception):
    """The rule is in `a_path_in_the_project`, and this is the only thing to say it broke.

    **This is the boundary's half of the work, and it is separate on purpose.** Containment —
    does the path land inside the project — is decided by `the_path_inside_the_project` and has
    always been decided there. Whether the string *can be* a path at all is decided here,
    before anything touches the disk, because every one of the rules below assumed it was
    holding a path and that assumption is where a real run died: `stat` does not return `False`
    for a name the filesystem will not hold, it raises.
    """


class APathInTheProject(BaseModel):
    """A path asked for, named the way it was asked for, inside a project directory."""

    project_directory: Path
    path: str


class ProjectFile(BaseModel):
    """A file of the project and the text it holds."""

    path: Path
    text: str


def a_path_in_the_project(project_directory: Path, path: str) -> APathInTheProject:
    """A path inside a project, named relative to the project's root, or why it is not one.

    **Four rules, and the boundary is where they belong.** The input to this function is a
    string a model produced, and every caller downstream assumes it is a path. So whether it
    can be one is decided here, once, by name, before any filesystem call — and the message
    quotes the input back, because a refusal the model cannot match against its own answer
    spends a correction and teaches it nothing.

    The rules, in the order a reader meets them:

    * something, and not only whitespace — a path to nowhere is not a path;
    * no character no filesystem holds, and no NUL in particular;
    * no empty segment, and no segment that is `.` or `..` — those are ways of *spelling*, and
      whether they climb out is containment's question, not this one;
    * every segment within `NAME_MAX`, per segment rather than for the path as a whole,
      because a repository has paths longer than 255 bytes and they are ordinary.
    """
    _refuse_a_string_that_cannot_be_a_path(path)
    return APathInTheProject(project_directory=project_directory, path=path)


def _refuse_a_string_that_cannot_be_a_path(path: str) -> None:
    """Every shape that is not a path, refused on its own terms and quoting the input.

    Separate function rather than four inside the constructor so the reasons can be read as a
    list, and so a caller that wants to know which rule broke gets one name for it.
    """
    if not path.strip():
        raise APathNotAPathError(
            f"{path!r} is empty. A path to nothing is not a path, and the answer to a change "
            "was found by naming nothing is to name the file the change starts in."
        )

    # **An address and a rooted path are deferred, not judged here.** Both have a better
    # answer from the rule that owns them — `the_path_inside_the_project` says "that is an
    # address" and "that is outside the project", and both are true in words this rule cannot
    # match. Claiming them here replaced a clear message with "you have a doubled slash",
    # which is both less useful to a model and wrong about why.
    if "://" in path or path.startswith("/"):
        return

    for character in sorted(A_CHARACTER_A_PATH_MAY_NOT_HOLD & set(path)):
        raise APathNotAPathError(
            f"{path!r} contains {character!r}, which no filesystem accepts and no path has "
            "ever meant. A character like that is a sentence that was written where a path "
            "belongs, and a correction has to name the sentence rather than the path."
        )

    for segment in path.split("/"):
        if segment == "":
            raise APathNotAPathError(
                f"{path!r} has an empty segment, from a doubled slash or a leading one. A path "
                "names the places between its names, and there is no place named by nothing."
            )
        if segment in (".", ".."):
            continue
        if len(segment.encode()) > THE_LONGEST_A_COMPONENT_MAY_BE:
            raise APathNotAPathError(
                f"{path!r} names a {len(segment.encode())}-byte file, and a filesystem holds "
                f"at most {THE_LONGEST_A_COMPONENT_MAY_BE} bytes in one name. This is not a "
                "missing file: it is a sentence, or an answer to a question about something "
                "else, written where a path belongs."
            )


def read_file_in_the_project(asked_for: APathInTheProject) -> ProjectFile:
    """The file asked for, and the text it holds.

    The boundary is decided before the path is touched, and by the resolved location
    rather than by the spelling of the request: `..` is a way out whether it is written
    in one segment or three, and a symlink is a way out however innocent it looks.
    Resolving first and comparing afterwards is the only version of this that cannot be
    walked past by writing the path differently.
    """
    where = the_path_inside_the_project(asked_for)

    if not where.exists():
        raise PathNotInTheProjectError(
            f"{asked_for.path!r} is not in the project, and there is nothing at "
            f"{where}. A path that is absent is a fact about the clone, so the answer "
            "is to ask for a different one."
        )

    return ProjectFile(path=where, text=where.read_text())


def the_path_inside_the_project(asked_for: APathInTheProject) -> Path:
    """Where the path asked for actually is, if that is inside the project.

    Four shapes get out, and a URL is one of them rather than a path that happens to be
    missing: `://` means a request to fetch something, which this tool has no business
    doing, and a caller told the file is "not there" would go looking in the clone for
    it instead of asking why a repository path was handed to a filesystem tool.
    """
    if "://" in asked_for.path:
        raise PathOutsideTheProjectError(
            f"{asked_for.path!r} is an address, and a filesystem tool reads inside the "
            f"project {asked_for.project_directory} rather than fetching anything. It is "
            "outside the project rather than missing from it."
        )

    root = asked_for.project_directory.resolve()
    where = (root / asked_for.path).resolve()

    if where != root and root not in where.parents:
        raise PathOutsideTheProjectError(
            f"{asked_for.path!r} is outside the project {root}. A tool handed a project "
            "reads that project, and an agent reasoning about somebody else's pull "
            "request has no business reading the machine's credentials."
        )

    return where
