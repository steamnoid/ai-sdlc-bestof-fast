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

# What this repository's own manifest says to run, as two argument vectors. A
# verification step that ran its own idea of the command would report a green run of
# something nobody asked for.
THE_SUITE_THAT_THIS_REPOSITORY_DEFINES = ("npm", "test")

# **How the runner is asked, rather than what it is asked.** The suite is `npm test` because that is
# what this repository's package.json declares, and the listing is vitest's own mode rather than a
# second npm script, because the runner knows its own configuration and npm does not. Written as a
# pair because the pair is the claim: a repository whose suite is `pytest` has no such mode, and
# `a_listing_command_for_a_toolchain` is where that question is asked and answered.
THE_LISTING_THAT_A_NODE_RUNNER_UNDERSTANDS = ("npx", "vitest", "list", "--run")

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
    toolchain_image = the_toolchain_image_a_repository_declares(checkout)
    mounts = the_checkout_only_mount(checkout)
    the_user = the_user_the_run_may_execute_as()

    return ASuiteToRun(
        repository=repository,
        checkout=checkout,
        toolchain_image=toolchain_image,
        installation_command=_an_invocation_of(
            toolchain_image,
            (
                *THE_INSTALL_THAT_FETCHES_PACKAGES,
                "--cache",
                WHERE_THE_TOOLCHAIN_MAY_WRITE_ITS_CACHE,
            ),
            mounts,
            "bridge",
            the_user,
        ),
        suite_command=_an_invocation_of(
            toolchain_image,
            THE_SUITE_THAT_THIS_REPOSITORY_DEFINES,
            mounts,
            "none",
            the_user,
        ),
        announcement_command=_a_listing_command_for(
            toolchain_image, mounts, the_user
        ),
    )


def _a_listing_command_for(
    toolchain_image: str, mounts: dict[str, str], the_user: str
) -> ContainerCommand:
    """The container that asks the runner what it collects.

    **The same image and the same single mount as the suite**, because the runner being asked has
    to be the runner that will later run the tests, and a listing taken in a different environment
    answers a question about an environment nothing will run in.

    **`--network=none`, and the listing may not fetch.** It is asked about files on the checkout in
    front of it; a command that reached the network for that would be a worse answer as well as a
    slower one, and the install already had its turn at the network.

    **Not optional, and that is the suite's limitation rather than a new one.** There is a branch
    here that says "a toolchain this system cannot ask gets no listing", and I wrote it before
    reading `the_toolchain_image_a_repository_declares` — which falls back to a node image for any
    repository that names none, so the branch was true for every input including a `FROM python`
    Dockerfile. A guard that cannot fail is a branch a reader has to check to learn nothing.
    `THE_SUITE_THAT_THIS_REPOSITORY_DEFINES` is `("npm", "test")` unconditionally, so every suite
    this system can run is a node suite and every node suite can be asked. Widening that is a
    separate slice and belongs there.
    """
    return _an_invocation_of(
        toolchain_image,
        THE_LISTING_THAT_A_NODE_RUNNER_UNDERSTANDS,
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

    suite = _a_container(the_run.suite_command, SECONDS_A_SUITE_MAY_TAKE)
    return SuiteOutcome(
        exit_code=suite.exit_code,
        passed=suite.exit_code == 0,
        dependencies_installed=True,
        output=_what_a_run_said(suite),
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

    **A skipped file counts as run**, because the suite says so: `↓ tests/integration/…` is
    vitest naming a file it collected and chose not to execute. A file the runner collected and
    skipped was not left out of the change's coverage, and treating it as unrun would make every
    suite with a skipped test look like one that dropped it.

    **Three markers, and they were read out of a container rather than remembered.** I first wrote
    four and one of them (BALLOT X) appears nowhere in the output of a suite that actually failed,
    which I then made it do: a MULTIPLICATION SIGN on `tests/unit/probe-red.test.ts`. Written as
    escapes in the constant below so
    the source is ASCII and nobody's editor has to guess what a lone mark means; a file a reader
    cannot see is a file a reader cannot check.
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
    """
    del exit_code
    return output
