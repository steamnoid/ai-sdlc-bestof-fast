"""Every tool call says where it came from: which stage, which tool, and which call it is.

**One decorator, on one function, covers every tool in this package.** `the_outcome_of` is where
`git clone`, `git push`, `docker run` and `gh` all go through — `github_clone_repository`,
`github_create_branch`, `github_create_pull_request`, `run_tests` and every other shell-out build
an `ACommand` and hand it over. Decorating that covers all of them; decorating each caller covers
only the ones somebody remembered, and the callers here are seams that tests double, so a forgotten
one is invisible to every suite.

**Three facts on a line, because three questions get asked while watching a run.** *Where in the
pipeline am I*, *what is it doing*, and *is this the second attempt*. The ordinal is not decoration:
the gateway drops roughly one structured answer in three, and a run that retries is
indistinguishable from a run that does not unless something counts.

**The counter is a module-level object with a `reset`, not a value passed in and not an
`lru_cache`.** A caller that had to supply it would supply the wrong one, and a parameter on every
tool call is a parameter nobody sets. `lru_cache` would freeze it, which is the opposite of the
property wanted. `reset` exists so a test's number is a fact rather than a leftover from whatever
ran before it.

**The stage is an argument and not a guess.** A tool does not know which node called it — the seam
is a plain callable and carries no context — so where a tool serves several stages the argument says
so in words, which reads better than a default that is quietly wrong for the rest of the run.

**Off means byte-for-byte the old behaviour**, because a call site nobody thought about has to
behave exactly as it did, and the four hundred tests that assert on what a run said keep reading
it through `capsys`.
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from aisdlc.observability import saying_what_a_run_is_doing
from aisdlc.observability.saying_what_a_run_is_doing import (
    a_person_has_asked_to_watch,
)

TheCall = ParamSpec("TheCall")
TheAnswer = TypeVar("TheAnswer")


class _ACounterThatOnlyGoesUp:
    """One number for the run, handed out once per call, and resettable by a test.

    **A class rather than a bare `itertools.count`, because a test has to be able to put it back to
    zero** and a `count` has no such door. The number is only a sequence if it starts somewhere, and
    a test asserting `[2]` after another test took `[1]` is a test of the order the suite happened
    to run in.

    **Not thread-safe, and it does not need to be.** A run is a graph executed one node at a
    time; two threads incrementing an `int` under the GIL is still one increment at a time, and a
    lock here would be a second thing to reason about for a property nothing can lose.
    """

    def __init__(self) -> None:
        self._how_many: int = 0

    def __call__(self) -> int:
        self._how_many += 1
        return self._how_many

    def reset(self) -> None:
        """Put it back to zero, and say plainly what it is for: a test, and nothing else."""
        self._how_many = 0


the_number_of_this_call = _ACounterThatOnlyGoesUp()


def announced_by(
    *, stage: str, tool: str | Callable[..., str]
) -> Callable[[Callable[TheCall, TheAnswer]], Callable[TheCall, TheAnswer]]:
    """Say on one line when a tool was entered, and again when it finished or failed.

    **Announced and re-raised, never swallowed.** A tool that raises is the one a person most needs
    to see, and a log that hides the failure to keep the output tidy makes the failure happen twice.
    The line carries the exception, so a person watching does not have to wait for a traceback that
    may be minutes away.

    **Entered *and* completed, because a start without an end is the only thing a heartbeat is
    for.** "started" alone cannot distinguish a slow tool from a stopped one, and that is the only
    distinction a person waiting on a container can actually make.

    **`completed` and not `finished`, because a failed command is returned rather than raised.**
    A non-zero exit comes back as an outcome, so the success path is the one that runs, and it used
    to say `finished` immediately after the runner had said `failed … exit code 128`. Both lines
    were true and the pair was unreadable, which defeats the only reason the failure tail is kept.
    The decorator reports that the call *returned*; whether the command *worked* is the runner's
    line to say, and it says it first. Started, failed, completed.

    **`functools.wraps`, so a traceback names the tool rather than the wrapper.** One line, and the
    difference between a stack that says `github_clone_repository` and one that says `<lambda>`.

    **The types are preserved, so a decorated function is still the callable a seam expects.** A
    decorator that widened a signature to `Callable[..., object]` would pass every test and break
    every seam comparison in this repository, and those comparisons are what caught an arity mistake
    in a real run seventeen minutes in.

    **`tool` is a name or a function of the arguments, because some tools can only say what they
    are once they are holding the thing they were called with.** `the_outcome_of` knows it is a
    command and nothing more; the program and its arguments arrive as an argument, and a line that
    said only "a command" would leave a person watching four `git` calls with no way to tell them
    apart. So `announced_by(stage=..., tool=_the_command_in_words)` names the command on both of its
    lines, and the two lines the runner used to print on its own are gone -- a command that says
    "started", says what it is, and then says "finished" says it twice.
    """

    def wrapping(tool_itself: Callable[TheCall, TheAnswer]) -> Callable[TheCall, TheAnswer]:
        @functools.wraps(tool_itself)
        def announced(*args: TheCall.args, **kwargs: TheCall.kwargs) -> TheAnswer:
            if not a_person_has_asked_to_watch():
                return tool_itself(*args, **kwargs)

            which_call = the_number_of_this_call()
            what_it_is = tool(*args, **kwargs) if callable(tool) else tool
            began_at = time.monotonic()
            _say(stage, what_it_is, which_call, "started", 0.0)

            try:
                the_answer = tool_itself(*args, **kwargs)
            except Exception as what_went_wrong:
                _say(
                    stage,
                    what_it_is,
                    which_call,
                    f"failed: {what_went_wrong}",
                    time.monotonic() - began_at,
                )
                raise

            _say(stage, what_it_is, which_call, "completed", time.monotonic() - began_at)
            return the_answer

        return announced

    return wrapping


def _say(stage: str, tool: str, which_call: int, what: str, seconds: float) -> None:
    """One line, in the format the record module already established.

    **The separator is a middot and the shape is fixed**, because these lines are read while they
    move and a column that changes width is a column a reader cannot scan. Stage, tool, number,
    verb — in that order, every time, so the eye learns it once.

    **The time is the tool's own, not the run's.** `time.monotonic()` is a stopwatch and not a
    clock, so passing it straight through printed `[9621m07s]` on the first call of a process that
    had been up for four days. A test caught that, and the number would have been unreadable rather
    than wrong, which is worse. Started is therefore always zero and finished is the elapsed time
    of the call.
    """
    the_whole = int(seconds)
    saying_what_a_run_is_doing.where_the_output_goes().write(
        f"[{the_whole // 60}m{the_whole % 60:02d}s] "
        f"#{which_call} {stage} · {tool} · {what}\n"
    )
