"""One line per thing that is happening, formatted so a person can read it while it moves.

**This started in the test tier and moved here because production needs it too.** A run of
four minutes with four lines on stdout is already more than a person watching gets, and the
person watching is whoever is operating the deployment.

The elapsed time is on every line because a label alone says nothing while the thing it labels
is still happening: "planning" tells you a call is outstanding and "planned in 41s" tells you
the model answered. `[m:ss]` is what reads at a glance in a terminal, and the seconds are
always two digits so the column does not jump while the numbers move.

**Flushed, because a line buffered until the end is a summary and not a heartbeat.** A summary
cannot distinguish a slow step from a stopped one, which is the only distinction a person
waiting on a model can actually make.
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import TextIO


def saying_what_a_run_is_doing(what: str, seconds: float) -> str:
    """The line a person watching this run sees, and the one a test can read back.

    `what` is a present participle — `planning`, `planned` — because the line is read while it
    is happening and a label that changes tense is a column that moves.
    """
    whole = int(seconds)
    return f"[{whole // 60}m{whole % 60:02d}s] {what}"


# The one switch, and it is the same name the model factory already read. **A person who did not ask
# to watch gets exactly the behaviour they had** -- a write to `sys.stdout`, which on this
# repository means `capsys` can still read it back, so the tests that assert on what a run said
# keep working without knowing any of this exists.
THE_SETTING_THAT_ASKS_TO_WATCH = "AISDLC_WHAT_A_RUN_IS_DOING"

# The terminal, and a hole where a test can put a different one.
WHERE_THE_TERMINAL_MAY_BE = "/dev/tty"


def a_person_has_asked_to_watch() -> bool:
    """Whether this deployment asked to watch a run.

    **Presence, not truth.** `AISDLC_WHAT_A_RUN_IS_DOING=0` is asking, and so is `=false`: the
    setting is a switch somebody threw, not a value anybody parses, and a parser here is one more
    thing to get wrong for a benefit nobody has asked for. A whitespace-only value has not said
    anything either, because a shell that exports an empty string is not asking.
    """
    return os.environ.get(THE_SETTING_THAT_ASKS_TO_WATCH, "").strip() != ""


@lru_cache(maxsize=1)
def a_terminal_at(where: str) -> TextIO | None:
    """The device at that path, opened for writing and kept, or `None` where there is none.

    **Line-buffered, because a buffered line is a summary and not a heartbeat.** The reason this
    exists is that a person watching has to tell a slow step from a stopped one, and a device that
    holds its output until 4 KB says nothing at all until it fills.

    **`OSError` rather than any exception, and `None` rather than a raise.** A process with no
    controlling terminal -- a build agent, or an editor's task runner -- fails here, and a run whose
    *heartbeat* raised would be a run that died for want of a cosmetic feature. On this very machine
    `/dev/tty` answers `Device not configured`, so the fallback is the ordinary path and not an edge
    case.

    **Cached, and only ever the device -- never `sys.stdout`.** A cached `sys.stdout` is a captured
    buffer handed back after the test that owned it ended, and writing to a closed one raises
    `ValueError: I/O operation on closed file`. Three tests in `test_run_command.py` failed exactly
    that way before the two were separated, and the fix is not a teardown: pytest replaces
    `sys.stdout` several times in one session, so the fallback must be read fresh every time.
    """
    try:
        return Path(where).open("w", encoding="utf-8", buffering=1)
    except OSError:
        return None


def where_the_output_goes() -> TextIO:
    """The terminal when somebody asked to watch a run, and `sys.stdout` when nobody did.

    **The device, not `sys.stdout`, wherever the device can be opened.** This is the whole change:
    pytest captures at the file-descriptor level, replacing fd 1 and fd 2, so a `print()` lands in a
    buffer shown only if the test fails -- and `sys.__stdout__` is the same descriptor. `/dev/tty`
    is a *different device*, which pytest does not capture, so writing there reaches the terminal
    with no flag, no conftest hook, and no private pytest API.

    **The fallback is the *current* `sys.stdout`, read fresh.** A saved handle would be the
    pre-capture one: the terminal in a terminal session, and a dangling pipe in a build agent.
    """
    if not a_person_has_asked_to_watch():
        return sys.stdout

    the_device = a_terminal_at(WHERE_THE_TERMINAL_MAY_BE)
    if the_device is None:
        return sys.stdout
    return the_device


def announcing_what_a_run_is_doing(what: str, seconds: float, stream: TextIO | None = None) -> str:
    """Say the line to the terminal the person started the run from, and hand it back.

    **Handed back and written, both.** Returning the line is what lets a test assert on the record
    without capturing anything, which would be a test of the test; writing it is the whole reason
    the module exists. A caller that wants the line on a stream of its own passes one -- and the
    tests do exactly that rather than assuming a machine that has a terminal.

    **The stream defaults to the terminal and never to `sys.stdout` directly.** A `print()` here is
    what four real runs proved nobody watching could see.
    """
    the_line = saying_what_a_run_is_doing(what, seconds)
    the_stream = stream if stream is not None else where_the_output_goes()
    the_stream.write(f"{the_line}\n")
    the_stream.flush()
    return the_line
