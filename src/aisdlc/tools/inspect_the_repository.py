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

from aisdlc.domain.commissioned_request import CommissionedRequest
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

# A limit on everything, because a context is finite and a selection with no ceiling is a
# repository pasted into a question. It is generous: enough for a real service's
# security-relevant surface, and small enough that a manifest is not the fourth of it.
# **How much of the whole limit one directory may hold.** A third, and the number is a third
# because this repository has two top-level directories that matter — `src` and `tests` — and a
# third leaves each of them room to be fully useful while making it impossible for either to
# crowd the other out.
#
# **This exists because a budget is not a sort.** The order below is by depth and then by path, and
# it was chosen so that a `Dockerfile`, a `Makefile` and a `package.json` — which sit at the root
# and the top — survive a cap. Then test files became part of what an agent is shown, test files
# sit two levels down and source files four, and the rule that protected the manifest spent the
# whole limit on tests. A real run was refused at its first gate for citing twenty-one test files
# and no source file, having been shown exactly that: `src/aisdlc/tools/run_command.py` — the
# subject of the run — was not in the inspection.
THE_SHARE_OF_THE_SOURCE_LIMIT_ONE_DIRECTORY_MAY_HOLD = 1 / 3

# **What it shows of what the rule chose, measured rather than assumed.** In this repository the
# rule chooses forty-two files and this limit shows nineteen; the other twenty-three are named in
# the "not shown" list underneath, and none is dropped without appearing in one bucket or the
# other. That is the design working as it is described — a truncated inspection says it was
# truncated rather than looking complete.
#
# **Raised from 120 000 and then put back, because the measurement behind the raise was about the
# wrong thing.** The rule's chosen set weighs a hundred and ninety thousand characters against a
# hundred-and-twenty-thousand limit, which reads as an argument for raising it — and raising it to
# two hundred and fifty thousand did bring ten more files in. It did not bring `run_command.py` in,
# which is the file a real run had been refused for not having been shown, because that file was
# never among the forty-two: the name rule had dropped it. A number changed for the wrong reason is
# worse than a number left alone, so it is left alone and the request is what the inspection reads.
#
# **And it is named for the source, because it bounds the source and nothing else.** It was
# `A_LIMIT_ON_THE_WHOLE_INSPECTION`, and it is used in exactly two places — once to derive the share
# above and once as the check that stops the loop — and both are inside the source function. On a
# repository built for the purpose it is **not** a bound on the assembled inspection:
#
# ```text
# assembled inspection  175926
# this limit            120000
# exceeds it by          55926
# ```
#
# The manifests, the README and the CI configuration each get the per-file limit and cannot see
# one another, so a repository with three large ones beside a full source section is over by nearly
# half. **Bounding the whole is not done here on purpose**: it re-budgets every inspection every
# reasoning stage is shown, which is a decision to take with its cost measured, and this is a
# naming problem. `tests/test_the_limit_is_named_for_what_it_bounds.py` holds both halves — that
# this name is true, and that the whole still exceeds it, so the day that changes it is a decision
# rather than a surprise.
A_LIMIT_ON_THE_SOURCE_THAT_MAY_CARRY_RISK = 120_000

# What a file has to be called to be shown to a model reasoning about a repository. **A name and
# not a parse, because a name is the only signal available without reading every file in the
# repository.** The list is deliberately a list: a parser for JavaScript routes would be a second
# language implementation in a tool whose job is to choose what to read, and it would be wrong on
# the eleventh language somebody writes.
#
# **It was a list of security words, and a real run found what that costs.** This inspection
# existed for discovery, whose job is a repository's shape, and the security analyst was later
# wired to the same one — so it was handed a directory listing and a `package.json` while being
# asked to find authentication problems, and a real run's gate refused the report for reasoning
# from filenames. The words below fixed that and were then applied to *every* consumer, which is
# the same mistake one level up: a run asked to change the Dockerfile's healthcheck was then
# never shown the Dockerfile, because `Dockerfile` is not a security word. The architecture
# analyst said so honestly — it reported no base image, no `HEALTHCHECK` directive and no interval
# — and the gate refused it for exactly that. **A selection framed around one consumer's question
# is the wrong selection for the others**, so the list is now what a *change* tends to touch:
# where security lives, and also what builds, deploys and configures.
WHAT_A_NAME_SAYS_A_FILE_MAY_MATTER = (
    # where security lives
    "auth",
    "authenticate",
    "authorization",
    "middleware",
    "session",
    "token",
    "secret",
    "credential",
    "password",
    "crypto",
    "permission",
    "role",
    "acl",
    "login",
    "signup",
    "user",
    "admin",
    "api",
    "route",
    "router",
    "controller",
    "handler",
    "env",
    "config",
    "policy",
    "cors",
    "cookie",
    "jwt",
    "oauth",
    "sanit",
    "validat",
    # where a build and a deployment are described — **added after a real run refused an
    # architecture report for never having opened the Dockerfile**, which is the file that
    # work item was about
    "dockerfile",
    "docker-compose",
    "compose",
    "makefile",
    "entrypoint",
    "deploy",
    "build",
    "setup",
    "requirements",
    "manifest",
    "migrat",
    "seed",
    "schema",
    ".env",
    ".gitignore",
)

# What a file has to end in to count as source at all. A repository's own `node_modules` and
# lockfiles are thousands of files and none of them is code anybody wrote for this project.
SUFFIXES_THAT_MAY_BE_SOURCE = (
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".py",
    ".rb",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".php",
    ".c",
    ".h",
    ".cc",
    ".cpp",
    ".cs",
    ".swift",
    ".scala",
    ".ex",
    ".exs",
    ".sh",
    ".sql",
)

# Directories whose contents are somebody else's. Walking into one of these is how an
# inspection turns into a paste of a dependency tree.
DIRECTORIES_THAT_HOLD_SOMEONE_ELSES_CODE = (
    "node_modules",
    ".git",
    "vendor",
    "dist",
    "build",
    ".next",
    "coverage",
    "__pycache__",
    ".venv",
    "venv",
    "target",
)

DIRECTORIES_THAT_HOLD_THE_PROJECTS_OWN_TESTS = (
    "test",
    "tests",
    "testing",
    "spec",
    "specs",
    "__tests__",
)

# How deep the search goes. Deep enough to find `web-app/src/app/api/.../route.ts` and shallow
# enough that a generated tree cannot become the answer on its own.
HOW_DEEP_THE_SEARCH_GOES = 6

# A file whose name says what it is and carries no extension. **The `Dockerfile` and the
# `Makefile` are in this list, and a real run refused an architecture report for never having
# opened one.** The suffix filter above exists to exclude lockfiles, images and data — and it
# excludes exactly these two, because "no extension" is not a suffix it knows. So extensionless
# files are decided by name, and a `Dockerfile` is the most consequential file in a repository a
# deployment is described in.
FILES_NAMED_WITHOUT_AN_EXTENSION = (
    "dockerfile",
    "makefile",
    "procfile",
    "license",
    "notice",
    "authors",
    "codeowners",
    "jenkinsfile",
)


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


def an_inspection_of_the_code(
    clone: ClonedRepository,
    what_the_run_is_about: CommissionedRequest | None = None,
) -> str:
    """Everything `an_inspection_of` shows, plus the code, plus what was left out.

    **Two inspections and not one, because two consumers want different things and sharing one
    is what broke.** A discovery report wants a repository's *shape*, and this module's own note
    that source files are not in it is right for that: a summary of a project is not a copy of
    it. A security analyst is asked to find authentication and authorization problems in the
    code, and a manifest and a README cannot answer either — so it was handed the shape, and
    reasoned from filenames, and a real run's gate refused the report for exactly that:

        "Six of the seven entries are then speculation from filenames and dependency
         declarations alone (findings 4, 5 and 7 reason from `Dockerfile`, `.dockerignore`
         and `bcryptjs` to MCP-endpoint, image-hygiene and cost-factor conclusions the report
         itself calls 'undecidable from the manifest')"

    **The closing section is the half that matters more than the code.** A model shown files it
    was not shown cannot tell that it was not shown them, and a reader cannot either — which is
    how a report about a repository that was never read reaches a gate looking like a report
    about one that was. So the inspection ends by naming what it left out, and a finding about a
    file that is not in that list is visibly a finding about nothing.
    """
    inside = clone.path

    what_was_shown, what_was_not = _the_source_that_may_carry_risk(
        inside, what_the_run_is_about
    )

    sections = [
        _what_the_project_is(clone),
        _the_top_level_listing(inside),
        *_the_contents_of(inside, "manifests", MANIFESTS),
        *_the_contents_of(inside, "readme", READMES),
        *_the_ci_configuration(inside),
        _the_source_is_below(what_was_shown),
        _what_was_not_shown(what_was_not),
    ]

    return "\n\n".join(section for section in sections if section)


def _the_source_that_may_carry_risk(
    inside: Path, what_the_run_is_about: CommissionedRequest | None
) -> tuple[list[str], list[str]]:
    """The source files whose names say a change might touch them, and the names of the rest.

    **Chosen by name and capped by characters, in that order.** A name is the only signal
    available without reading every file, and a cap is what keeps a large repository from becoming
    a paste. When the cap is reached the search stops and everything left goes into the "not
    shown" list — so a truncated inspection says it was truncated rather than looking complete.

    **The cap bites from the top down, not in an arbitrary order.** Sorted by depth and then by
    path, so the files nearest the root — which is where a `Dockerfile`, a `Makefile` and a
    `package.json` live — are the ones that survive it.
    """
    how_many_characters_are_spent = 0
    how_much_each_directory_may_spend = (
        A_LIMIT_ON_THE_SOURCE_THAT_MAY_CARRY_RISK
        * THE_SHARE_OF_THE_SOURCE_LIMIT_ONE_DIRECTORY_MAY_HOLD
    )
    spent_by_directory: dict[str, int] = {}
    what_was_shown: list[str] = []
    what_was_not: list[str] = []

    for a_path in _every_source_file_in(inside, what_the_run_is_about):
        its_text = _the_text_of(inside, a_path)

        if its_text is None:
            what_was_not.append(a_path)
            continue

        if (
            how_many_characters_are_spent + len(its_text)
            > A_LIMIT_ON_THE_SOURCE_THAT_MAY_CARRY_RISK
        ):
            what_was_not.append(a_path)
            continue

        the_directory_it_is_in = a_path.split("/", 1)[0]
        how_much_that_directory_has_spent = spent_by_directory.get(the_directory_it_is_in, 0)
        if how_much_that_directory_has_spent + len(its_text) > how_much_each_directory_may_spend:
            what_was_not.append(a_path)
            continue

        what_was_shown.append(f"## {a_path}\n\n{its_text}")
        spent_by_directory[the_directory_it_is_in] = (
            how_much_that_directory_has_spent + len(its_text)
        )
        how_many_characters_are_spent += len(its_text)

    return what_was_shown, what_was_not


def _every_source_file_in(
    inside: Path, what_the_run_is_about: CommissionedRequest | None = None
) -> list[str]:
    """Every source file, what the run asked about first, skipping anybody else's code.

    **Sorted by depth and then by path, so two runs of one work item are comparable.** An
    inspection whose order came out of the file system would be a different question each time,
    and a report checked against it would be checked against a different thing.

    **What the run asked about comes before both, and that is the only thing read here about
    the work.** A real run was refused at its first gate for citing twenty-one test files and no
    source file at all, while every one of its `key_components` named a symbol out of `src/` — and
    measuring the selection said why nothing else could have found the file:

    ```text
    eligible files 169      selected by name 11      dropped by the name rule 158
    ```

    **The run's request contained the path in plain text and the file was one of the hundred and
    fifty-eight the name rule dropped.** The rule is a list of words about security and about
    builds, extended twice already for exactly this reason — once because a run was refused for
    never having opened a `Dockerfile` — and the next extension would have been `command`, which
    adds one file: the one that run was about. A selection that reads nothing about the work is a
    guess dressed as a selection, so the request is read here and the request is the run's own
    words.

    **The check is a substring and not a parser, on purpose.** A file qualifies when the text of
    the request contains its path exactly as the clone spells it. There is no pattern to get
    wrong, no way to read a path that is not there, and no way for a request to name a file that
    does not exist — the file has to have been found by the walk to be named at all.
    """
    what_they_asked_for = _the_words_of(what_the_run_is_about)

    found: list[tuple[int, int, str]] = []

    for a_path in inside.rglob("*"):
        if not a_path.is_file():
            continue

        its_parts = a_path.relative_to(inside).parts
        if any(a_part in DIRECTORIES_THAT_HOLD_SOMEONE_ELSES_CODE for a_part in its_parts):
            continue
        if len(its_parts) > HOW_DEEP_THE_SEARCH_GOES:
            continue

        its_name = a_path.name.lower()
        if a_path.suffix not in SUFFIXES_THAT_MAY_BE_SOURCE and (
            its_name not in FILES_NAMED_WITHOUT_AN_EXTENSION
        ):
            continue

        its_path_as_written = str(a_path.relative_to(inside))
        the_run_asked_for_it = its_path_as_written in what_they_asked_for

        if not (
            the_run_asked_for_it
            or _it_lives_where_tests_live(its_parts)
            or any(a_word in its_name for a_word in WHAT_A_NAME_SAYS_A_FILE_MAY_MATTER)
        ):
            continue

        found.append((0 if the_run_asked_for_it else 1, len(its_parts), its_path_as_written))

    return [a_path for _, _, a_path in sorted(found)]


def _the_words_of(what_the_run_is_about: CommissionedRequest | None) -> str:
    """The request as one piece of text, or nothing at all when nobody said what the run was for.

    **The title and the body, and not `filed_as`.** The filing is where a reader goes for the rest
    of a conversation and it is `None` for the ordinary case of somebody saying it out loud, so a
    run commissioned from a filing has the same words as one commissioned from a sentence.

    **`None` is an honest empty string rather than a default worth having.** Four of the five
    stages are handed no request today, and a stage that is not told what the run is about gets
    the selection the name rule alone produces — which is what it got before any of this.
    """
    if what_the_run_is_about is None:
        return ""
    return f"{what_the_run_is_about.title}\n{what_the_run_is_about.body}"


def _it_lives_where_tests_live(its_parts: tuple[str, ...]) -> bool:
    """Whether a path runs through a directory whose job is to hold this project's own tests.

    **The third time a file has been invisible because its *name* did not match a list**, and
    the same comment above the list says why it keeps happening: the word list is framed around
    what a *change* tends to touch, and a test is named after what it asserts rather than after
    a subsystem. `test_a_python_repository_can_be_verified.py` contains none of those words, so
    the entire suite of this repository was shown to nobody.

    Location is the honest signal here. A directory called `tests` holds tests whatever the files
    inside are called, and every language in every repository agrees on the name because it is
    the one thing that has to mean the same thing to a person reading a path and to the tool
    walking it.
    """
    return any(a_part in DIRECTORIES_THAT_HOLD_THE_PROJECTS_OWN_TESTS for a_part in its_parts)


def _the_text_of(inside: Path, a_path: str) -> str | None:
    """One file's text, or `None` when it could not be read or is too large to be worth having.

    **Read through the confined reader, so a symlink out of the clone is refused rather than
    followed.** A repository is arbitrary input: a file named `auth.ts` is a file a pull request
    can add, and it can be a link to somewhere else on the machine.
    """
    try:
        read = read_file_in_the_project(
            a_path_in_the_project(project_directory=inside, path=a_path)
        )
    except PathNotInTheProjectError:
        return None

    if len(read.text) > A_LIMIT_ON_A_SINGLE_FILE:
        return None

    return read.text


def _the_source_is_below(what_was_shown: list[str]) -> str | None:
    """The code, under a heading saying the rest of this is the code rather than a summary."""
    if not what_was_shown:
        return None
    return "# The code that may carry risk\n\n" + "\n\n".join(what_was_shown)


def _what_was_not_shown(what_was_not: list[str]) -> str:
    """What this inspection left out, said plainly and first.

    **A model that knows its own coverage can be held to it, and a reader can too.** The whole
    finding of the run that produced this is a report reasoning about files nobody had shown it,
    and the reason it read as a report is that nothing said otherwise. This section is the
    otherwise.
    """
    if not what_was_not:
        return (
            "# What you were not shown\n\nNothing. Every file whose name suggests it may carry "
            "risk is above, and nothing was left out for being too large or too numerous."
        )

    return (
        "# What you were not shown\n\n"
        f"{len(what_was_not)} further source file(s) whose names suggested a change might touch "
        "them, and which are **not** above. A finding about one of these is a finding about a "
        "file nobody has shown you, and it has to say so rather than reason from the name — a "
        "real run's gate refused an architecture report for exactly that, having reported no "
        "base image and no healthcheck interval about a Dockerfile it had never been shown:\n\n"
        + "\n".join(f"- `{a_path}`" for a_path in what_was_not[:60])
        + (f"\n- and {len(what_was_not) - 60} more" if len(what_was_not) > 60 else "")
    )


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

    **And the line saying so states where its number came from.** It used to read
    `(omitted: 61199 characters, too large to read)`, which says two things and lets a
    careful reader resolve them wrongly: a bare character count on the same line as
    "too large to read" is a measurement to anyone who has not been told otherwise, and
    nobody had been told otherwise. A real run's discovery report said faithfully that
    `README.md` was not readable and quoted the size it had been given here, and the
    policy reading it refused the run for the contradiction — which does not exist. The
    line now says the size is known without reading the file, which is what is true.

    **This is the writer's mistake rather than the reader's**, and that is why the fix is
    here instead of in the policy's question: explaining a notation to the model about to
    rule on a document puts the convention somewhere it can drift from the thing it
    describes. A line that cannot be misread needs no explanation.
    """
    try:
        read = read_file_in_the_project(
            a_path_in_the_project(project_directory=inside, path=name)
        )
    except PathNotInTheProjectError:
        return None

    if len(read.text) > A_LIMIT_ON_A_SINGLE_FILE:
        return (
            f"## {name}\n\n"
            f"({len(read.text)} characters. Its text is not shown, because a file this large is "
            f"not worth the context, and the size is known without reading it.)"
        )

    return f"## {name}\n\n{read.text}"

