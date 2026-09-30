"""`shell.run_command`: run a program, with no shell in between.

§12 says not to expose arbitrary unrestricted shell execution by default, and the way to
not expose it is structural rather than a matter of care: the program and its arguments
are separate values, handed to the operating system as a list, and the runner never
involves a shell. A caller holding a string it wants interpreted does not get that from
here, and a repository path containing a space is a path rather than two arguments.

A failure is a result rather than an exception, because the exit code and what the
program printed are the only things a caller has to translate a failure into a typed
refusal of its own. The one case that raises is a program that is not installed, which
is the one case with no outcome at all: a missing `git` read as a failed `git` would be
reported as a repository that does not exist.

This is not the tool for running a repository's own test suite — that is
`shell.run_tests`, in a container, because the code in a pull request is not our code.
The `working_directory` here is a convenience for pointing `git` at a checkout and not a
promise that anything may be run there.
"""

from __future__ import annotations

import subprocess
import threading
import time
from typing import TextIO

from pydantic import BaseModel

from aisdlc.observability import saying_what_a_run_is_doing
from aisdlc.observability.announced_by import announced_by
from aisdlc.observability.saying_what_a_run_is_doing import (
    a_person_has_asked_to_watch,
    announcing_what_a_run_is_doing,
)

# `timeout(1)`'s own convention for a command that ran out of time, adopted so the number
# in a log is recognisable rather than invented. Not an operating system code: this
# runner reports it, it does not claim the operating system raised it.
EXIT_CODE_A_COMMAND_THAT_TIMED_OUT = 124


class NoSuchProgramError(Exception):
    """The rule is in `the_outcome_of`, and this is the only thing that may say it broke."""


class ACommand(BaseModel):
    """One program, its arguments, and how long it may take.

    Named in full because it is a value passed around, not a helper, and `command` or
    `cmd` would be the kind of abbreviation a reader has to stop and decode.
    """

    program: str
    arguments: list[str] = []
    working_directory: str | None = None
    seconds_it_may_take: float = 300


class CommandOutcome(BaseModel):
    """What a program did: how it ended, and what it said while doing it."""

    exit_code: int
    standard_output: str
    standard_error: str
    timed_out: bool = False


# How much of a failure to show. **Bounded, because a failed install speaks for pages** and the
# error is in the last of them; unbounded would put a dependency tree on a terminal.
HOW_MANY_LINES_OF_A_FAILURE_ARE_SHOWN = 20


def _the_command_in_words(command: ACommand) -> str:
    """The program and its arguments, as a person would say them.

    **The whole line, because the arguments are the question.** `npm ci` and
    `npm ci --omit=dev` are different jobs and a line naming only the program cannot tell a
    person watching which one ran.
    """
    return " ".join([command.program, *command.arguments])


@announced_by(stage="a tool call", tool=_the_command_in_words)
def the_outcome_of(command: ACommand) -> CommandOutcome:
    """Run the command, and say so if anybody is watching.

    **This is the one decorated function that covers every tool in the package.** `git clone`,
    `git push`, `docker run`, `gh` — `github_clone_repository`, `github_create_branch`,
    `github_create_pull_request`, `run_tests` and every other shell-out build an `ACommand` and hand
    it here, so a decorator on this line announces all of them. A decorator on each caller would
    announce only the ones somebody remembered, and these callers are seams that tests double, so a
    forgotten one is invisible to every suite in the repository.

    **The stage says "a tool call" rather than a stage name, because a command does not know which
    node asked.** The seam is a plain callable and carries no context, and guessing would put a tool
    in the wrong stage for the whole run -- worse than admitting it does not know. What a person
    watching gets is the program and its arguments, which is the part that actually tells them
    where a run is; the stage is what the nodes announce.

    A non-zero exit is returned rather than raised, and the only thing that raises is a
    program that is not there — the one outcome that does not exist, and the one a caller
    has to be able to tell apart from a program that ran and failed.

    **A run clones a repository, installs dependencies in a container and runs a suite on each
    side of a change, and none of it was visible.** Forty seconds of cloning looks exactly like
    forty seconds of nothing, and a person watching has no instrument to tell a slow run from a
    hung one — the same thing the model record exists to make true, and the same failure it was
    built after.

    **The tail of a failure and nothing of a success.** An install or a suite can put a token in
    what it prints, and a run that reports every line a command said is a run that puts it on a
    terminal and into a log. The failure is almost always in the last thing a tool said, so that
    is what is shown; what worked is a transfer rate and a file count, and nobody watching a run
    needs it.
    """
    began_at = time.monotonic()
    the_outcome = _the_command_run_and_what_it_said(command)

    _say_what_came_of_it(command, the_outcome, time.monotonic() - began_at)

    return the_outcome


def _say_what_came_of_it(
    command: ACommand, the_outcome: CommandOutcome, seconds_it_took: float
) -> None:
    """The verdict on a failure, and the tail of it for whoever was not there to read it.

    **The exit code is the one fact no other line carries.** The decorator says started and
    completed with the elapsed time; nothing anywhere says whether the tool worked, because a
    non-zero exit is returned rather than raised and so never reaches a `failed:` branch.

    **The tail only for a reader who was not there.** A watched run has already had every line
    a tool said, written out as it said it, and repeating the last twenty of them is the same
    fault as saying `finished` twice: the second copy is the one a reader's eye lands on once
    the command is over. And a CI log or a captured test holds no other record of why an
    install failed, so for them the bounded tail is written even with the switch off -- it is
    the one line this function exists for.

    **`announcing_what_a_run_is_doing` is not wrapped in `print`.** It writes the line to the
    terminal *and* returns it, so a `print` around it sent a second copy to `sys.stdout` --
    which pytest captures, and which is the whole reason four real runs printed nothing. Half
    of every announcement was going exactly where nobody was looking.
    """
    if the_outcome.exit_code == 0:
        return

    the_verdict = (
        f"{_the_command_in_words(command)} failed after {seconds_it_took:.1f}s with "
        f"exit code {the_outcome.exit_code}"
    )
    if not a_person_has_asked_to_watch():
        said = (the_outcome.standard_error or the_outcome.standard_output).strip()
        tail = "\n".join(said.splitlines()[-HOW_MANY_LINES_OF_A_FAILURE_ARE_SHOWN:])
        announcing_what_a_run_is_doing(f"{the_verdict}:\n{tail}", seconds_it_took)
        return

    announcing_what_a_run_is_doing(the_verdict, seconds_it_took)


def _the_command_run_and_what_it_said(command: ACommand) -> CommandOutcome:
    """Run the command, and decide here whether anybody is going to read what it says.

    **Two runners and one rule: what a person is watching arrives while it happens.** A run with
    nobody watching pays for nothing -- no threads, no pipes to drain -- and a run with somebody
    watching gets every line at the moment the tool says it. The announcing of the call itself is
    the decorator's job, so that a tool cannot be watched but not announced, or the other way
    round.
    """
    if not a_person_has_asked_to_watch():
        return _the_command_run_and_held_in_memory(command)
    return _the_command_run_while_saying_each_line(command)


def _the_command_run_and_held_in_memory(command: ACommand) -> CommandOutcome:
    """Run the command, keep everything it said, and write none of it anywhere.

    **The whole output, because a caller may need all of it.** `what_the_suite_says_it_collects`
    reads a suite's own opening lines out of it and a `gh` caller reads a number out of it, and
    bounding what is kept would bound what those tools can see -- which is not the same decision
    as what a person is shown.
    """
    try:
        finished = subprocess.run(
            [command.program, *command.arguments],
            capture_output=True,
            text=True,
            cwd=command.working_directory,
            timeout=command.seconds_it_may_take,
            check=False,
        )
    except FileNotFoundError:
        raise NoSuchProgramError(
            f"{command.program!r} is not installed on this machine, so nothing was run. "
            "That is a broken installation rather than a job that failed, and the two "
            "must not be reported the same way."
        ) from None
    except subprocess.TimeoutExpired as expired:
        return CommandOutcome(
            exit_code=EXIT_CODE_A_COMMAND_THAT_TIMED_OUT,
            standard_output=_whatever_text(expired.stdout),
            standard_error=_whatever_text(expired.stderr),
            timed_out=True,
        )

    return CommandOutcome(
        exit_code=finished.returncode,
        standard_output=finished.stdout,
        standard_error=finished.stderr,
    )


def _the_command_run_while_saying_each_line(command: ACommand) -> CommandOutcome:
    """Run the command, and write each line to the terminal the moment the tool says it.

    **A pipe and a thread per stream, because a tool writes to both.** `git clone` puts its
    progress on stderr and its result on stdout, and `npm ci` does most of its talking on stderr;
    a reader of one that ignored the other would be silent exactly where the waiting is. One
    thread per pipe is also what keeps this from deadlocking: a single process reading two pipes
    in turn fills the one it is not reading and the tool stops.

    **A line at a time and not a block, because the point is the timing.** `capture_output` already
    had every byte of a completed command; what it could not do was hand a line over before the
    command ended, and a forty second clone is the case that is about. `readline` in a loop is
    what makes that true, and it is the ordinary way to say it.

    **The same `CommandOutcome` as the other runner, or the twelve callers would be watching a
    different tool than the one a deployment gets.** Nothing here decides what a line *means*.
    """
    what_it_said: list[str] = []
    what_it_complained_about: list[str] = []
    the_terminal = saying_what_a_run_is_doing.where_the_output_goes()

    the_process = subprocess.Popen(
        [command.program, *command.arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=command.working_directory,
    )
    the_readers = [
        threading.Thread(
            target=_say_each_line_and_keep_it, args=(the_process.stdout, what_it_said, the_terminal)
        ),
        threading.Thread(
            target=_say_each_line_and_keep_it,
            args=(the_process.stderr, what_it_complained_about, the_terminal),
        ),
    ]
    for one_reader in the_readers:
        one_reader.start()

    did_it_run_out_of_time = False
    try:
        exit_code = the_process.wait(timeout=command.seconds_it_may_take)
    except subprocess.TimeoutExpired:
        the_process.kill()
        exit_code = EXIT_CODE_A_COMMAND_THAT_TIMED_OUT
        did_it_run_out_of_time = True
    finally:
        for one_reader in the_readers:
            one_reader.join()

    return CommandOutcome(
        exit_code=exit_code,
        standard_output="".join(what_it_said),
        standard_error="".join(what_it_complained_about),
        timed_out=did_it_run_out_of_time,
    )


def _say_each_line_and_keep_it(
    what_the_tool_is_saying: TextIO, what_was_said: list[str], the_terminal: TextIO
) -> None:
    """One line, to the terminal and to the outcome, in that order and for the same line.

    **Both, and the reason is the same reason there are two runners.** The terminal is for the
    person and the list is for the twelve callers that go on to read what the tool said; a reader
    that kept the line and showed nothing would have fixed the complaint and broken every tool,
    and one that showed the line and kept nothing would have fixed the tools and left the person
    where they were.
    """
    for one_line in iter(what_the_tool_is_saying.readline, ""):
        what_was_said.append(one_line)
        the_terminal.write(one_line)
        the_terminal.flush()


def _whatever_text(what_timeout_kept: str | bytes | None) -> str:
    """Whatever the operating system had managed to collect before the bound was reached.

    A timed-out program may have said something useful on its way out, and a timeout that
    discards the partial output makes debugging a hang harder than the hang.
    """
    if what_timeout_kept is None:
        return ""
    if isinstance(what_timeout_kept, bytes):
        return what_timeout_kept.decode("utf-8", errors="replace")
    return what_timeout_kept
