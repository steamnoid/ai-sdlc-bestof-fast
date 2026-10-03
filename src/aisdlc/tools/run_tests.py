"""`shell.run_tests`: the repository's own test suite, run somewhere that is not the host.

§27 says it plainly: never allow arbitrary repository code to execute with unrestricted
host permissions. A pull request's test suite is arbitrary code from a stranger, and
running it on the host means it runs with the developer's credentials, their SSH keys and
their file system. So the boundary goes around execution and not around the run.

**Two runs, because one cannot be both.** `npm ci` has to reach a registry and `npm test`
must not. So the install is its own invocation with the network, and it finishes before any
of the stranger's code is in the image; the suite is a second invocation with no network at
all. A single invocation either blocks the install or leaves the suite free to phone home.

**A command is an argument vector, never a shell line.** `sh -c "npm test"` would be the
one shape that could carry `; rm -rf /work` out of a repository's own manifest, so the
suite is invoked as `["npm", "test"]` and a string is refused rather than sanitised. A
check that tried to make a shell line safe would be a claim nobody could verify.

**The toolchain image is read out of the repository, not remembered.** A repository that pins
its toolchain in a Dockerfile is telling us what it wants to be run with, and overriding it
with a guess produces failures that belong to this system and get reported as the
repository's tests failing. The repository's own images do not contain its tests — the
build stage copies the application and the runtime stage copies the bundle — so the test
image is built here, from the declared base, and the version in it is the one the
repository says.

**What this tool cannot do, said plainly: a suite that needs the host's Docker daemon.**

A repository's own integration tests may build an image and start a container, and they
usually skip themselves unless `docker info` answers. Inside this container it does not —
there is no host socket, by design — so those tests skip. That is the boundary working, not
a defect in the repository: a container that could reach the host's Docker daemon would hold
the host's ability to start anything, which is precisely what §27 exists to withhold. A suite
that needs the host to run containers is outside what this tool offers, and no amount of
mounting would fix it without undoing the thing.

**A field and the command it describes cannot disagree.** Every property that reaches the
container is a flag in `arguments`, and the fields beside it are read from the same values
rather than set separately: a model that said `as_user` was not root while the command
carried no `--user` would be a claim with nothing behind it.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, field_validator

from aisdlc.domain.repository import Repository
from aisdlc.tools.run_command import (
    ACommand,
    CommandOutcome,
    NoSuchProgramError,
    the_outcome_of,
)

# The one directory a container may see from the host, and what it looks like inside.
WHERE_THE_CHECKOUT_APPEARS_INSIDE = "/work"

# Credentials that must never reach code this system did not write. Named rather than
# derived from a pattern, because a pattern misses the one that matters and a test should
# be able to say which names it means.
CREDENTIALS_THAT_MUST_NOT_REACH_A_REPOSITORY = (
    "GITHUB_TOKEN",
    "OPENAI_API_KEY",
    "OPENCODE_GO_KEY",
    "LANGSMITH_API_KEY",
    "SSH_AUTH_SOCK",
)

# **How the runner is asked, rather than what it is asked.** The suite is `npm test` because that is
# what this repository's package.json declares, and the listing is vitest's own mode rather than a
# second npm script, because the runner knows its own configuration and npm does not. Written as a
# pair because the pair is the claim: a repository whose suite is `pytest` has no such mode, and
# `a_listing_command_for_a_toolchain` is where that question is asked and answered.
THE_LISTING_THAT_A_NODE_RUNNER_UNDERSTANDS = ("npx", "vitest", "list", "--run")

# **Two reporters, because the two readers need two different things and neither reporter has
# both.** `default` is what a person reads at the verification gate *and* what
# `_the_suite_says_it_ran_something` reads for a number; `json` is the only shape in which vitest
# 1.6.1 writes the path of every file it opened. **The JSON does not replace the report, it carries
# the file list the report has no room for** — so a suite run in JSON alone would be a worse suite,
# and `--` is npm's own way of handing arguments to the script rather than to itself.
#
# **Read out of a repository rather than remembered**: `package.json` declares
# `"test": "vitest run"`, so `npm test -- --reporter=json` reaches `vitest run --reporter=json`.
THE_SUITE_THAT_THIS_REPOSITORY_DEFINES = (
    "npm",
    "test",
    "--",
    "--reporter=default",
    "--reporter=json",
)

# **The same four answers for a Python repository, and read out of a real `pytest` rather than
# remembered.** `--collect-only -q` prints one `path::test_name` per collected test, which is more
# than a file listing and is why `the_test_files_the_suite_reported_running` now reads both.
THE_SUITE_THAT_A_PYTHON_REPOSITORY_DEFINES = ("python", "-m", "pytest", "-q")
# **The runner is installed with the project, because the runner is what the suite invokes.**
# `pip install -e .` installs the repository's own package and nothing else, so `python -m pytest`
# then fails with `No module named pytest` — read out of a real container run, not imagined.
# A repository's test dependencies live in whatever it declares, and a group pip does not read
# (`[dependency-groups]`, which is a `uv` concept) is invisible to it, so naming the runner
# explicitly is the one answer that works for an arbitrary repository rather than this one.
THE_INSTALL_THAT_FETCHES_A_PYTHON_PACKAGE = (
    "python",
    "-m",
    "pip",
    "install",
    "-e",
    ".",
    "pytest",
)
THE_LISTING_THAT_A_PYTHON_RUNNER_UNDERSTANDS = (
    "python",
    "-m",
    "pytest",
    "--collect-only",
    "-q",
)
THE_PYTHON_WHEN_A_REPOSITORY_DECLARES_NONE = "python:3.13-slim"

# **The uv branch, and the image is the one that has uv in it.** Read out of a real `docker
# manifest inspect`, not remembered: the tag is the part of this that has to be right, and a
# repository that cannot be installed because the image name was a guess is a red suite that says
# nothing about the change.
# **Not the `-slim` variant, and that is a real run's finding rather than a preference.** Thirteen
# of this repository's tests build a git repository in a temporary directory, and the slim image
# has no `git` in it, so all thirteen error with `FileNotFoundError: 'git'`. That is not a smaller
# suite — it is a suite whose fixtures cannot run, and the report says "13 errors" rather than
# "the sandbox lacks a tool". Checked with `docker run --rm --network=none <image> command -v git`
# on both variants; the slim one has no git and the other one does.
#
# **`node:22-bookworm` is already the non-slim variant**, which is why the node path never hit
# this and why the two answers disagreeing would have looked like a uv problem.
THE_UV_IMAGE_THAT_RUNS_A_REPOSITORYS_OWN_TOOLCHAIN = (
    "ghcr.io/astral-sh/uv:python3.13-bookworm"
)
# `--all-extras` because a repository's own suite lives in its extras and its dev group, which is
# what "the suite" means for a project that publishes a library and tests the rest.
THE_INSTALL_THAT_FETCHES_WITH_UV = ("uv", "sync", "--all-extras")
# `--no-sync` because the suite container must not touch the network, and a sync would.
THE_SUITE_THAT_A_UV_REPOSITORY_DEFINES = ("uv", "run", "--no-sync", "pytest", "-q")
THE_LISTING_THAT_A_UV_REPOSITORY_UNDERSTANDS = (
    "uv",
    "run",
    "--no-sync",
    "pytest",
    "--collect-only",
    "-q",
)

# **pytest's own "nothing was collected", named.** Exit code 5 means no tests were collected, which
# is not a failing suite and is not a passing one — it is a suite that never ran, and the first
# report of a Python repository here said "No module named pytest" as though it were a red suite.
# `dependencies_installed` already keeps "would not install" apart from "ran and failed"; this is
# the same idea for the third case.
PYTEST_SAYS_IT_COLLECTED_NOTHING = 5

# Where the container's `HOME` points, and why it is a constant rather than a setting.
# S108 is about a *host's* shared temporary directory: this is inside a `--rm` container that
# has one mount, no credential and no network, and the value names a home rather than opening one.
WHERE_THE_TOOLCHAIN_MAY_WRITE_ITS_HOME = "/tmp"  # noqa: S108
A_FROM_LINE_NAMING_A_PYTHON_IMAGE = re.compile(r"^\s*FROM\s+(python:[\w.\-]+)", re.MULTILINE)


class HowThisRepositoryIsTested(BaseModel):
    """The four answers that decide how one repository's suite is run, together.

    **One model and not five arguments,** because they are one fact and because they were once
    unrelated constants that happened to agree. `pip install -e .` with `node:22-bookworm` is not
    a configuration anybody chose; it is what you get when each answer has its own default and none
    of them has an owner.

    **And the cache flag is one of the answers, which is the fifth one and the reason it is here.**
    It used to be appended at the call site as a literal `--cache`, because npm was the only
    toolchain this system had. `uv` spells it `--cache-dir` and **refuses to start** when given
    the other one — a red install that said `tip: a similar argument exists`, from a real run.
    A flag belonging to one toolchain cannot be a constant in a function serving three.

    **And neither can the directory.** The path was `/tmp/.npm` for all of them, so `uv` was told
    to keep its cache in a directory named after another package manager — which works, and is
    the sort of thing that is still there in three years when somebody greps for what writes to
    `/tmp`.
    """

    toolchain_image: str
    installation_command: tuple[str, ...]
    suite_command: tuple[str, ...]
    listing_command: tuple[str, ...]
    the_flag_that_points_a_cache_somewhere_writable: str
    where_its_cache_may_be_written: str

# The marks a runner puts in front of a file it collected: passed, failed, and skipped. As escapes
# so this file stays ASCII, and three rather than four because a fourth was remembered rather than
# observed — see `the_test_files_the_suite_reported_running`, which quotes a container's output for
# all three.
THE_MARKS_A_SUITE_NAMES_A_FILE_BY = "\u2713\u00d7\u2193"
THE_INSTALL_THAT_FETCHES_PACKAGES = ("npm", "ci")

# Where `npm` keeps its cache and its logs, named rather than left to the image's `HOME`.
# The container runs as the process's uid so it can write the checkout, and that uid keeps
# whichever home the image declares — `node:24` declares `/`, and `/.npm` cannot be created
# by anybody but root. A real run died there with `TAR_ENTRY_ERROR ENOENT` and exit 243,
# having passed every other property of the sandbox. `/tmp` is the one directory every user
# in a toolchain image can create, and it is inside the container rather than on the host.
#
# **The alternative — setting `HOME` — is refused**, and that is why this is a constant
# rather than a setting: `environment` is empty by construction, no code path fills it, and
# that emptiness is what makes "no credential reaches this container" a property of the code
# instead of somebody remembering to filter a list.
# S108 is about predictable names in a *shared* temporary directory on a host. This path
# exists only inside a `--rm` container that has one mount, no credential and no network, and
# the alternative was `/` — which the image's non-root user cannot write at all.
WHERE_THE_TOOLCHAIN_MAY_WRITE_ITS_CACHE = "/tmp/.npm"  # noqa: S108

# Nobody who is root. The image has a `node` user, but the container does not have to be that
# user: it has to be whoever owns the checkout, because a suite puts its build output there
# and a directory is writable only by its owner. See `the_user_the_checkout_belongs_to`.
NOBODY_WHO_IS_ROOT = 0

# The program that starts a container, and how long each of the two runs may take. An
# install fetches every dependency of a repository, and a suite is a stranger's code that
# may never return, so both are bounded rather than left to the patience of a pipeline.
DOCKER = "docker"
SECONDS_AN_INSTALL_MAY_TAKE = 900
SECONDS_A_SUITE_MAY_TAKE = 1800
# A listing is `--collect-only`: the same import graph as a run and none of the test bodies,
# so it is bounded generously and for the same reason the install is.
SECONDS_A_LISTING_MAY_TAKE = 600

# Read out of a repository's Dockerfile rather than remembered. A guess here produces
# failures that belong to this system and are reported as the repository's tests failing.
A_FROM_LINE_NAMING_A_NODE_IMAGE = re.compile(r"^FROM (node:[\w.-]+)", re.MULTILINE)
THE_DOCKERFILES_A_REPOSITORY_MAY_DECLARE_ITS_NODE_IN = (
    "Dockerfile",
    "Dockerfile.test",
    "docker/Dockerfile",
)
THE_TOOLCHAIN_WHEN_A_REPOSITORY_SAYS_NOTHING = "node:22-bookworm"


class NoDockerError(Exception):
    """The rule is in `the_container_is_reachable`, and only it may say the rule broke.

    Raised rather than worked around. A verification step that fell back to the host when
    no container was available would be the thing §27 forbids with a worse story: a test
    run that silently executed with the developer's keys, and nobody knew.
    """


class RootRunError(Exception):
    """The rule is in `the_user_the_run_may_execute_as`, and only it may say the rule broke.

    §27's guarantee is a container that is not root, and a run started by root has no way to
    keep it while still being able to write the checkout. The guarantee wins: the run is
    refused, by name, so the answer is not a permission error about a build directory nobody
    expected to matter.
    """


# The programs whose purpose is to hand a string to something else, and which are therefore the
# ones this system refuses to build a `docker run` around. A program that does not do that reads
# its own arguments as data and stays allowed: `node -e "…"` gets a string this system wrote, and
# `sh -c "…"` gets one a repository's manifest chose.
INTERPRETERS_THAT_READ_A_STRING = ("sh", "bash", "zsh", "dash")


class ContainerCommand(BaseModel):
    """One `docker run`, with everything it is given said out loud.

    `environment` is empty by construction rather than by convention: there is no code
    path that fills it, so a credential cannot reach this container by someone forgetting
    to filter one, which is what a filtered list does on the day a variable is added to
    the names to exclude and the exclusion runs the wrong way round.

    **And the arguments may not be a shell line, which is now a property of the class rather
    than a function in this file with nothing calling it.** `a_command_that_is_not_a_list` was
    written, documented and tested, and every command this system has run went through this
    class without it — so a `sh -c` carrying a repository's `&& rm -rf /work` was accepted by the
    one thing that builds a `docker run`. A tested rule that nothing enforces is worse than an
    untested one, because a reader who finds the test concludes the rule holds.
    """

    arguments: list[str] = []

    @field_validator("arguments")
    @classmethod
    def _not_a_shell_line(cls, arguments: list[str]) -> list[str]:
        """Refuse an interpreter that would be handed a string, rather than sanitise one.

        **The shape, not the contents.** A check that read the string to decide whether it was safe
        would be reading a pull request's manifest, and this system does not do that in order to
        decide whether it may run it. So `sh -c "ls"` is refused on the same grounds as
        `sh -c "npm test && rm -rf /work"`, and the second one's danger does not make the first one
        a case worth examining.

        **The whole vector is refused and not just the string**, because the dangerous part is the
        interpreter in front of it: `["npm", "test", "&&", "rm"]` is harmless and
        `["sh", "-c", "… && rm -rf /work"]` is not, so the question is what runs it.
        """
        for an_argument in arguments:
            if an_argument in INTERPRETERS_THAT_READ_A_STRING:
                raise ValueError(
                    f"{an_argument!r} is a shell, and this system builds argument vectors rather "
                    "than lines. A repository's own manifest may contain anything, so a container "
                    "here is never handed a string to interpret: every command in this module is a "
                    "list of arguments and a program that reads them as data."
                )
        return arguments
    network: str = "none"
    environment: dict[str, str] = {}
    mounts: dict[str, str] = {}


class ASuiteToRun(BaseModel):
    """One run of a repository's own test suite, and the two commands that make it up."""

    repository: Repository
    checkout: str
    toolchain_image: str
    installation_command: ContainerCommand
    suite_command: ContainerCommand
    announcement_command: ContainerCommand


class SuiteOutcome(BaseModel):
    """What a suite said, as a result rather than as a fault.

    A suite that fails is the answer the verification stage exists to produce, so a
    non-zero exit is a value here and not an exception. Raising would throw away the only
    thing worth knowing, and would make a red suite indistinguishable from a broken
    harness.

    `dependencies_installed` is the half that keeps those two apart. A repository whose
    dependencies would not install has not run its tests at all, and a report that calls
    that a red suite sends whoever reads it after the code that never executed.

    A suite still running when its time ran out arrives as exit code 124 from
    `run_command`, and is reported as not passed — which is true, and is not the same fact
    as a suite that ran and failed.
    """

    exit_code: int
    passed: bool
    dependencies_installed: bool
    output: str
    what_it_collected: str = ""
    """What this runner said it collects, in its own words, when it was asked.

    **A second field because a suite printing its own output and a runner listing its files are
    two questions asked at two moments, and neither answers the other.** `pytest -q` prints nine
    dots and a percentage — the run happened and the report names no file at all, so a check
    reading `output` has nothing to read and either refuses every correct change or passes every
    uncollected one. Six pull requests on this machine were opened by a run and the best documented
    one delivered two test files into a directory its target's runner never collects; its report
    said the suite passed before the change and passed after it, and both were true.

    **So the runner is asked, and the answer travels with the result rather than being left at
    the stage that happened to ask first.** The planning stage already asks — that is what
    `announcement_command` is — and the answer used to be used for planning and then thrown away,
    which left verification guessing from dots. Empty when nothing was asked, and a caller that
    needs the listing says so rather than reading `output` and hoping.
    """


def the_checkout_only_mount(checkout: str) -> dict[str, str]:
    """The one host path a container may see, and where it appears inside.

    One mount, and it is the repository. A second mount is a second way out of the
    sandbox, and every one of them was added for a reason that felt harmless at the time.

    Writable, because a suite has to put its build output somewhere and the checkout is
    the only place it is allowed to. **It is writable because the container runs as the person
    who started the run**, which is who owns a checkout they cloned — "writable" was a claim
    Docker Desktop happened to honour and a Linux kernel does not, and a suite that cannot
    write its build output fails in a way that says nothing about permissions. What it wrote
    is not a secret afterwards: the clone's own history is what says so.
    """
    return {WHERE_THE_CHECKOUT_APPEARS_INSIDE: checkout}


def the_user_the_run_may_execute_as() -> str:
    """The `uid:gid` of whoever started the run, which is who may write in the checkout.

    **This exists because the same command passed on a Mac and failed on a Linux runner, and
    the reason is worth stating exactly.** The container ran as `node`, uid 1000, and a
    checkout on a developer's machine is mode 755 and owned by that developer — so on macOS
    the suite could write to the mount and on Linux it could not. Docker Desktop does not
    enforce bind-mount ownership; a Linux kernel does. No code changed between the two runs.

    So the user is the person running the tool rather than a name written into a constant,
    and a hardcoded uid is the actual defect: it is correct on one machine and wrong on every
    other, and when it is wrong the error names a build directory's permissions rather than
    the identity mistake that caused it. The process is the right identity because the process
    is who cloned the repository — `git clone` writes the files, and the owner of a checkout
    is the person who made it.

    **It is the process rather than the checkout's owner on purpose.** A checkout that does
    not exist still has to reach the "no container here" refusal before anything is looked
    at, and a function that stat'ed a path would raise something else first — the order is a
    rule of its own, and one test says why. Reading the process's own identity cannot fail,
    and it is the identity that matters in every case where the suite is run at all.

    §27's guarantee survives: whoever started the run is a non-root user, and a run started by
    root is refused rather than executed, so "not root" is never traded for "can write".
    """
    if os.getuid() == NOBODY_WHO_IS_ROOT:
        raise RootRunError(
            "this run was started by root, so a container that writes the checkout would "
            "have to run as root, and §27's guarantee is that a repository's own code does "
            "not. Refused rather than run: the guarantee is the reason the tool exists, and "
            "it is not worth a build directory."
        )

    return f"{os.getuid()}:{os.getgid()}"


def the_python_a_repository_declares(checkout: str) -> str | None:
    """The `python:...` its own Dockerfile builds on, read the same way a node one is.

    **Added because this repository is a Python one and could not be verified at all.** Every
    constant that decided how a suite ran named npm, and a run whose change was to this codebase
    installed and ran nothing — so the verification failed, the delivery refused, and no change
    this system could make about itself was ever deliverable.
    """
    for name in THE_DOCKERFILES_A_REPOSITORY_MAY_DECLARE_ITS_NODE_IN:
        path = Path(checkout) / name
        if not path.is_file():
            continue
        declared = A_FROM_LINE_NAMING_A_PYTHON_IMAGE.search(path.read_text(encoding="utf-8"))
        if declared is not None:
            return declared.group(1)
    return None


def the_node_a_repository_declares(checkout: str) -> str | None:
    """The `node:...` its own Dockerfile builds on, or nothing at all.

    A repository that does not ship a Dockerfile gets nothing rather than a guess, and
    the caller decides what a repository staying silent means.
    """
    for name in THE_DOCKERFILES_A_REPOSITORY_MAY_DECLARE_ITS_NODE_IN:
        path = Path(checkout) / name
        if not path.is_file():
            continue
        declared = A_FROM_LINE_NAMING_A_NODE_IMAGE.search(path.read_text(encoding="utf-8"))
        if declared is None:
            continue
        return declared.group(1)
    return None


def how_this_repository_is_tested(checkout: str) -> HowThisRepositoryIsTested:
    """How *this* repository's suite is run, read out of what it declares rather than remembered.

    **A repository that says what it needs is asked; one that says nothing gets npm.** That is the
    rule this file already followed for the *image* — "the toolchain image is read out of the
    repository, not remembered" — and it was never applied to the other two answers. `npm test`
    was hardcoded the way a default should be, next to a comment saying that a repository whose
    suite is `pytest` has no such mode, and the sentence naming where that question would be
    answered pointed at a function that did not exist.

    **It exists now, and the naming is the point.** `HowThisRepositoryIsTested` is the four
    answers together because they are one fact — a repository's toolchain is not four independent
    settings, and asking for them separately is how `node:22-bookworm` came to be paired with
    `npm test` by accident rather than by anybody's decision.
    """
    if _this_repository_declares_uv(checkout):
        return HowThisRepositoryIsTested(
            toolchain_image=THE_UV_IMAGE_THAT_RUNS_A_REPOSITORYS_OWN_TOOLCHAIN,
            installation_command=THE_INSTALL_THAT_FETCHES_WITH_UV,
            suite_command=THE_SUITE_THAT_A_UV_REPOSITORY_DEFINES,
            listing_command=THE_LISTING_THAT_A_UV_REPOSITORY_UNDERSTANDS,
            the_flag_that_points_a_cache_somewhere_writable="--cache-dir",
            where_its_cache_may_be_written="/tmp/.uv",  # noqa: S108
        )
    if _this_repository_declares_python(checkout):
        return HowThisRepositoryIsTested(
            toolchain_image=the_python_a_repository_declares(checkout)
            or THE_PYTHON_WHEN_A_REPOSITORY_DECLARES_NONE,
            installation_command=THE_INSTALL_THAT_FETCHES_A_PYTHON_PACKAGE,
            suite_command=THE_SUITE_THAT_A_PYTHON_REPOSITORY_DEFINES,
            listing_command=THE_LISTING_THAT_A_PYTHON_RUNNER_UNDERSTANDS,
            the_flag_that_points_a_cache_somewhere_writable="--cache-dir",
            where_its_cache_may_be_written="/tmp/.pip",  # noqa: S108
        )
    return HowThisRepositoryIsTested(
        toolchain_image=the_toolchain_image_a_repository_declares(checkout),
        installation_command=THE_INSTALL_THAT_FETCHES_PACKAGES,
        suite_command=THE_SUITE_THAT_THIS_REPOSITORY_DEFINES,
        listing_command=THE_LISTING_THAT_A_NODE_RUNNER_UNDERSTANDS,
        the_flag_that_points_a_cache_somewhere_writable="--cache",
        where_its_cache_may_be_written="/tmp/.npm",  # noqa: S108
    )


def _this_repository_declares_uv(checkout: str) -> bool:
    """Whether this is a uv repository, by what it declares rather than by what it is called.

    **`uv.lock` or a `[tool.uv]` table, and either is enough.** This repository has both. The
    check exists because of a fact about pip that is easy to miss until a suite fails to import:
    **pip does not read `[dependency-groups]`** — that is a `uv` idea — so installing a uv-managed
    project with pip gets the project and none of its development dependencies. `langchain` is
    an *extra* here, and pytest lives in the dev group, so the pip branch can install this
    repository and still be unable to run its suite.

    **And uv is the branch that can persist, which is the other half of it.** `uv sync` writes its
    environment to `.venv` **inside the project**, on the checkout mount, which is the one thing
    the install container and the suite container share. That is exactly what `npm ci` does with
    `node_modules`, and it is why the node path worked and `pip install -e .` did not: pip wrote
    to the interpreter, which is thrown away with the container.
    """
    if Path(checkout, "uv.lock").is_file():
        return True
    pyproject = Path(checkout, "pyproject.toml")
    return pyproject.is_file() and "[tool.uv" in pyproject.read_text(encoding="utf-8")


def _this_repository_declares_python(checkout: str) -> bool:
    """Whether this is a Python repository, by what it declares rather than by what it is called.

    **`pyproject.toml` and not the presence of `.py` files**, for the same reason the image is
    read from a declared `FROM` line rather than from the file extension: a repository that
    contains Python and runs a Node suite is common, and one that runs pytest nearly always
    declares it.
    """
    return Path(checkout, "pyproject.toml").is_file()


def the_toolchain_image_a_repository_declares(checkout: str) -> str:
    """The base a repository's tests are run on, which is the one it says or none of ours.

    Falling back to a default is a decision, so it is a decision with a reason recorded
    rather than a silent second answer: a repository with no Dockerfile is not one we
    cannot verify, it is one that did not tell us, and guessing is then the only thing
    left to do.
    """
    declared = the_node_a_repository_declares(checkout)
    if declared is not None:
        return declared
    return THE_TOOLCHAIN_WHEN_A_REPOSITORY_SAYS_NOTHING


def a_command_that_is_not_a_list(command: str) -> list[str]:
    """Refuse a shell line rather than sanitise one."""
    raise ValueError(
        f"{command!r} is a shell line, not a command. A repository's own manifest may "
        "contain anything, so a command here is an argument vector and never a string "
        "some shell would interpret."
    )


def _an_invocation_of(
    toolchain_image: str,
    the_command: tuple[str, ...],
    mounts: dict[str, str],
    network: str,
    the_user: str,
) -> ContainerCommand:
    """One `docker run`, with every property it is given written into the arguments.

    Built *from* those values rather than described beside them, because a `network` that
    says "none" while the arguments carry no `--network` is a claim the container never
    received, and it is the sort of claim that survives a review because it looks like a
    field.
    """
    arguments = [
        "run",
        "--rm",
        "--cap-drop=ALL",
        f"--user={the_user}",
        f"--network={network}",
        # **One environment variable, and it is a constant rather than a parameter.** This
        # container has never been given any, and the reason was good: an empty map cannot be
        # filtered wrong, because there is nothing in it to filter. But a toolchain that writes
        # to `$HOME` cannot run without one — `pip install` reaches for `~/.local` and dies with
        # `Permission denied: /.local` on an image whose home is `/` and whose user is not root.
        # A *constant* is the stronger version of the same property: there is no parameter to
        # pass a credential through, so forgetting to exclude one cannot happen. `/tmp` is the
        # directory this file already names as the one any uid can create inside a toolchain.
        "-e",
        f"HOME={WHERE_THE_TOOLCHAIN_MAY_WRITE_ITS_HOME}",
        f"-v{mounts[WHERE_THE_CHECKOUT_APPEARS_INSIDE]}:{WHERE_THE_CHECKOUT_APPEARS_INSIDE}",
        f"-w{WHERE_THE_CHECKOUT_APPEARS_INSIDE}",
        toolchain_image,
        *the_command,
    ]
    return ContainerCommand(arguments=arguments, network=network, mounts=mounts)


def a_suite_to_run(repository: Repository, checkout: str) -> ASuiteToRun:
    """The run, as two containers: one that may fetch, and one that may not.

    **No image is built.** The repository's own images do not contain its tests, so
    building one here would only imitate respecting it; what the repository does declare is
    the `node:` its Dockerfile builds on, and that is what the suite runs in, with the
    checkout mounted over the working directory.
    """
    how_it_is_tested = how_this_repository_is_tested(checkout)
    toolchain_image = how_it_is_tested.toolchain_image
    mounts = the_checkout_only_mount(checkout)
    the_user = the_user_the_run_may_execute_as()

    return ASuiteToRun(
        repository=repository,
        checkout=checkout,
        toolchain_image=toolchain_image,
        installation_command=_an_invocation_of(
            toolchain_image,
            (
                *how_it_is_tested.installation_command,
                how_it_is_tested.the_flag_that_points_a_cache_somewhere_writable,
                how_it_is_tested.where_its_cache_may_be_written,
            ),
            mounts,
            "bridge",
            the_user,
        ),
        suite_command=_an_invocation_of(
            toolchain_image,
            how_it_is_tested.suite_command,
            mounts,
            "none",
            the_user,
        ),
        announcement_command=_a_listing_command_for(
            toolchain_image, mounts, the_user, checkout
        ),
    )


def _a_listing_command_for(
    toolchain_image: str,
    mounts: dict[str, str],
    the_user: str,
    checkout: str,
) -> ContainerCommand:
    """The container that asks the runner what it collects.

    **The same image and the same single mount as the suite**, because the runner being asked has
    to be the runner that will later run the tests, and a listing taken in a different environment
    answers a question about an environment nothing will run in.

    **`--network=none`, and the listing may not fetch.** It is asked about files on the checkout in
    front of it; a command that reached the network for that would be a worse answer as well as a
    slower one, and the install already had its turn at the network.

    **Asked in whichever runner this repository uses, which is the sentence that used to name a
    function that did not exist.** `the_toolchain_image_a_repository_declares` fell back to a node
    image for any repository that named none, so the branch "a toolchain this system cannot ask
    gets no listing" was true for every input including a `FROM python` Dockerfile. A guard that
    cannot fail is a branch a reader has to check to learn nothing. `npm test` was hardcoded, so
    every suite this system could run was a node suite — which was true, and not because anybody
    decided it. Both runners print a collection listing, so there is no branch here.
    """
    return _an_invocation_of(
        toolchain_image,
        how_this_repository_is_tested(checkout).listing_command,
        mounts,
        "none",
        the_user,
    )


def the_container_is_reachable() -> bool:
    """Whether a container can be started on this machine, asked of Docker itself.

    A machine without Docker installed and a machine with a stopped Docker Desktop are the
    same fact to a caller, so both answer False and neither raises: they mean the same
    refusal, and `the_tests_in` is where that refusal is worded in the terms of §27.
    """
    try:
        asked = the_outcome_of(
            ACommand(program=DOCKER, arguments=["info"], seconds_it_may_take=60)
        )
    except NoSuchProgramError:
        return False
    return asked.exit_code == 0


def the_tests_in(
    the_run: ASuiteToRun,
    the_container_is_reachable: Callable[[], bool] = the_container_is_reachable,
) -> SuiteOutcome:
    """The suite's answer, or the refusal to go and look for one.

    **The refusal comes first, and there is nothing behind it.** §27 forbids arbitrary
    repository code executing with unrestricted host permissions, and the tempting way to
    be useful when no container is available is to run the suite on the host anyway. That
    is not a degraded mode, it is the exact thing the rule exists to prevent, wearing a
    green tick: the suite passes and nobody knows it just executed with the developer's
    credentials, their SSH keys and their file system.

    So the reachability of a container is asked first, before the checkout is looked at,
    and a machine without one gets `NoDockerError` and no suite. The seam is a parameter
    rather than a patched module because the decision is the thing under test — a reader
    should be able to see that nothing is attempted on the far side of this `if`.

    **The install runs first, and its failure is not a red suite.** A repository whose
    dependencies would not install has not run anything, and reporting that as failing
    tests points whoever reads the report at code that never executed — so the outcome
    says which of the two happened, and says nothing about the other.
    """
    if not the_container_is_reachable():
        raise NoDockerError(
            "There is no container on this machine, so a repository's tests were not run. "
            "§27 forbids running them here instead: a pull request's suite is arbitrary "
            "code, and on the host it would run with the developer's credentials and file "
            "system. Start Docker, and nothing else about this run changes."
        )

    installation = _a_container(the_run.installation_command, SECONDS_AN_INSTALL_MAY_TAKE)
    if installation.exit_code != 0:
        return SuiteOutcome(
            exit_code=installation.exit_code,
            passed=False,
            dependencies_installed=False,
            output=_what_a_run_said(installation),
        )

    # **Asked before the suite, because the suite's own output cannot answer this and the answer
    # is what makes the suite's report readable.** `--collect-only` is cheap next to a run and
    # this is the one question a container can answer that a report of dots cannot.
    what_the_runner_collects = _a_container(
        the_run.announcement_command, SECONDS_A_LISTING_MAY_TAKE
    )

    suite = _a_container(the_run.suite_command, SECONDS_A_SUITE_MAY_TAKE)
    return SuiteOutcome(
        exit_code=suite.exit_code,
        passed=suite.exit_code == 0,
        dependencies_installed=True,
        output=_what_a_run_said(suite),
        what_it_collected=_what_a_run_said(what_the_runner_collects),
    )


def _a_container(the_invocation: ContainerCommand, seconds_it_may_take: int) -> CommandOutcome:
    """One container, started, waited for, and gone — `--rm` takes it away afterwards."""
    return the_outcome_of(
        ACommand(
            program=DOCKER,
            arguments=the_invocation.arguments,
            seconds_it_may_take=seconds_it_may_take,
        )
    )


def _what_a_run_said(outcome: CommandOutcome) -> str:
    """What a person would have watched: what it printed, then what it complained about."""
    return outcome.standard_output + outcome.standard_error


def what_the_suite_says_it_collects(what_the_suite_said: str) -> list[str]:
    """The `include` patterns out of a suite's own opening lines, as the suite printed them.

    **A runner that printed no `include` line yields an empty list, and that is not the same claim
    as "nothing is collected".** The first is a runner this system could not read, and the rule in
    `plan_the_change` asks nothing when it is handed one; the second is a fact about a repository
    and would refuse every plan in it. Keeping them apart is the whole reason this is a reader of
    output rather than a reader of a config file — a file with no `include` key and a file with an
    empty one are the same three lines, and only one of them says anything.

    **A line is split into patterns on the commas that separate them and not inside braces**,
    because `tests/unit/**/*.{test,spec}.ts` is one pattern and splitting it on its comma yields
    `tests/unit/**/*.{test` and `spec}.ts` — two globs that match nothing, for a runner that is
    working perfectly. The brace is what tells the two apart, and a runner that prints `a, b, c`
    needs the same rule to become three patterns rather than one.

    **A pattern split anywhere else stays whole**, so a directory whose name contains a comma is
    not silently turned into two. That is a real possibility in a path and a hypothetical in a
    glob, and the cost of the mistake is a runner that looks like it collects nothing.
    """
    the_patterns: list[str] = []
    for a_line in what_the_suite_said.splitlines():
        stripped = a_line.strip()
        if not stripped.startswith("include:"):
            continue
        for one_pattern in _the_patterns_on_a_line(stripped.removeprefix("include:")):
            if one_pattern:
                the_patterns.append(one_pattern)
    return the_patterns


def _the_patterns_on_a_line(what_the_runner_printed: str) -> list[str]:
    """The comma-separated patterns of one `include` line, with braces left unbroken."""
    the_patterns: list[str] = []
    the_current: list[str] = []
    how_many_braces_are_open = 0

    for a_character in what_the_runner_printed:
        if a_character == "{":
            how_many_braces_are_open += 1
        elif a_character == "}":
            how_many_braces_are_open = max(0, how_many_braces_are_open - 1)

        if a_character == "," and how_many_braces_are_open == 0:
            the_patterns.append("".join(the_current).strip().strip("'\""))
            the_current = []
            continue
        the_current.append(a_character)

    the_patterns.append("".join(the_current).strip().strip("'\""))
    return the_patterns


def the_test_files_the_suite_reported_running(what_the_suite_said: str) -> list[str]:
    """The files a suite named as having run it, in the order it named them.

    **Read from a suite's own report rather than asked of the filesystem**, because the filesystem
    says which files exist and the question is which ones ran. Counting `*.test.ts` on disk is a
    guess about a repository's conventions made by something that has never read them, and on the
    run that delivered #9 it would have answered "seven files" for a change whose two files were
    invisible to the runner.

    ****A skipped file counts as run**, because the suite says so: `↓ tests/integration/…` is
    vitest naming a file it collected and chose not to execute. A file the runner collected and
    skipped was not left out of the change's coverage, and treating it as unrun would make every
    suite with a skipped test look like one that dropped it.

    **A suite that reports in JSON is read from the JSON, because that is where the paths are.**
    vitest's own default reporter names no file at all, which is why this repository asked for a
    separate listing command for years and why that command does not exist on the version this
    repository pins. Its JSON reporter writes one entry per file it opened, with the path under
    `name` — so the run that proved the suite green is itself a complete witness, and reading it
    removes both the phantom listing and a container run per verification.

    **Three markers, and they were read out of a container rather than remembered.** I first wrote
    four and one of them (BALLOT X) appears nowhere in the output of a suite that actually failed,
    which I then made it do: a MULTIPLICATION SIGN on `tests/unit/probe-red.test.ts`. Written as
    escapes in the constant below so
    the source is ASCII and nobody's editor has to guess what a lone mark means; a file a reader
    cannot see is a file a reader cannot check.
    """
    the_files = _the_files_a_json_report_named(what_the_suite_said)
    for a_path in _the_files_a_node_suite_named(what_the_suite_said):
        if a_path not in the_files:
            the_files.append(a_path)
    for a_path in _the_files_a_python_suite_named(what_the_suite_said):
        if a_path not in the_files:
            the_files.append(a_path)
    return the_files


def _the_files_a_json_report_named(what_the_suite_said: str) -> list[str]:
    """The files a JSON report named under `testResults[].name`, from vitest's own shape.

    **vitest 1.6.1's JSON reporter, read out of its source rather than remembered:**

    ```js
    testResults.push({ assertionResults, startTime, endTime, status, message, name: file.filepath })
    ```

    **The JSON is looked for inside the output rather than parsed out of all of it.** A run
    invoked through `npm test` has npm's own banner in front of it — `> package@1.0.0 test` and
    `> vitest run` — so parsing the whole stream would fail on a report that is perfectly good, and
    a parser that fails silently is how this reader came to answer nothing about a real run.

    **A `name` is only a file when it is one.** The same array is the place a runner puts a test's
    name in some shapes, so a value with no path in it is skipped rather than reported as a file
    nobody can open.
    """
    the_files: list[str] = []
    for a_path in _the_names_a_json_report_declared(what_the_suite_said):
        if "/" not in a_path:
            continue
        if a_path not in the_files:
            the_files.append(a_path)
    return the_files


def _the_names_a_json_report_declared(what_the_suite_said: str) -> list[str]:
    """Every `testResults[].name` in whatever JSON the output carries, in the order written.

    **Every JSON object in the output is looked at, not only the first.** npm's banner is not JSON
    and a suite that printed a warning before its results would otherwise be unreadable, and the
    shape that is being looked for is checked before anything is believed — a report that parses is
    not a report that has a `testResults`.

    **`raw_decode`, and the text is stepped over by exactly what it read.** That is what makes a
    stream with a banner in front of it readable at all: `json.loads` raises on the banner and takes
    the whole report with it, while `raw_decode` says how much of the stream was one value. **A
    decoder that did not advance would loop for ever on the value it had just read**, which is what
    the first version of this did and what the timeout caught.
    """
    the_names: list[str] = []
    where = 0
    while True:
        a_brace = what_the_suite_said.find("{", where)
        if a_brace < 0:
            return the_names
        try:
            a_value, read = json.JSONDecoder().raw_decode(what_the_suite_said[a_brace:])
        except ValueError:
            where = a_brace + 1
            continue
        where = a_brace + read
        if not isinstance(a_value, dict):
            continue
        the_entries = a_value.get("testResults")
        if not isinstance(the_entries, list):
            continue
        for an_entry in the_entries:
            if not isinstance(an_entry, dict):
                continue
            a_name = an_entry.get("name")
            if isinstance(a_name, str) and a_name:
                the_names.append(a_name)


def _the_files_a_python_suite_named(what_the_suite_said: str) -> list[str]:
    """The files `pytest --collect-only -q` named, from its own output rather than from the disk.

    **Read because pytest prints `path::test_name`, and the file is everything before the `::`.**
    That is a different shape from a node suite's marks, so a parser that only understood one of
    them reported nothing for the other — and "nothing" is the answer that makes an uncollected
    test look like a suite that passed over it.

    **A summary line is not a file.** pytest ends its output with something like `68 tests
    collected in 3s`, and reading that as a path would put a line of prose into the list of files
    that ran.
    """
    the_files: list[str] = []
    for a_line in what_the_suite_said.splitlines():
        stripped = a_line.strip()
        if not stripped or "::" not in stripped:
            continue
        a_path = stripped.split("::", 1)[0].strip()
        if a_path and a_path.endswith((".py",)) and a_path not in the_files:
            the_files.append(a_path)
    return the_files


def _the_files_a_node_suite_named(what_the_suite_said: str) -> list[str]:
    """The files a node runner named with the three marks `THE_MARKS_A_SUITE_NAMES_A_FILE_BY` holds.

    The marks are written as escapes in that constant so this file stays ASCII; writing them here
    literally would put a glyph a reader's editor has to guess at into a docstring.
    """
    the_files: list[str] = []
    for a_line in what_the_suite_said.splitlines():
        stripped = a_line.strip()
        if not stripped or stripped[0] not in THE_MARKS_A_SUITE_NAMES_A_FILE_BY:
            continue
        the_rest = stripped[1:].strip()
        for a_marker in ("(", " - "):
            where = the_rest.find(a_marker)
            if where != -1:
                the_rest = the_rest[:where].strip()
                break
        if the_rest:
            the_files.append(the_rest)
    return the_files


def the_runners_announcement_of(output: str, exit_code: int) -> str:
    """What a runner announced, taken from what it printed rather than from how it ended.

    **The exit code is not consulted, and that is the whole point of this function.**
    `vitest list --run` prints its `include` and then reports no test files and exits 1 — on a
    repository with 74 tests, because the listing mode is a configuration dump that a later vitest
    still got wrong. Reading the exit code first would make the listing unreadable for exactly the
    repository this exists to protect against, and the failure would look like the green run behind
    PR #9: a suite that said nothing wrong and a delivery that was never exercised.

    **Everything printed is returned, not just the `include` line.** A reader cannot tell a real
    include from a truncated one, and half an answer that looks like an answer is the failure mode
    this repository keeps meeting.

    **Nothing printed is `""`, which is how a rule stays quiet rather than refusing everything.**
    A container that failed to start has announced nothing, and a plan asked with an empty
    announcement is a plan this system has no grounds to refuse.

    **A line saying no test files were found is dropped, because this listing never asks the
    question that line answers.** `vitest list` was added in vitest 2.1 and this repository pins
    **1.6.1**, whose own help offers `run`, `related`, `watch`, `dev`, `bench`, `typecheck` and
    nothing else — so `vitest list --run` is `vitest` with the *filter* `list`, which matches no
    file, and the four words are vitest reporting that it was asked something it does not have.
    **Relaying them puts a false claim in a delivered report**: a repository of 79 tests, recorded
    as one that collects none.

    **Dropping it does not unblock anything, and this function is not what stands in the way.**
    With nothing announced, `the_test_files_the_suite_reported_running` reads only the report —
    and vitest 1.6.1 has no reporter that names a file, which is why the run this was written for
    was refused on real evidence. **The refusal stands and the record stops lying about why.**
    """
    del exit_code
    return "\n".join(
        a_line
        for a_line in output.splitlines()
        if not a_line.startswith("No test files found")
    )
