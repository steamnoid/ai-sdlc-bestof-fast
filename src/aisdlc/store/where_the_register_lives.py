"""Where the register is, for the parts of this system that are handed no connection.

**The register is a process-wide fact, and this is the one place it is held.** The board's API is
built over a connection it is passed, which is right — a test can hold a register in a temporary
directory and the application can hold one on disk, with no branch that says which. But the
graph's nodes are not handed a connection: a LangGraph node receives the state and nothing
else, and the state is a `TypedDict` of domain values that must not carry a database cursor.

So there are two doors, and they are the same door. `the_register()` hands the connection the
recorders write through, and `the_api_over` is built over a connection opened by this module.
There is no second connection, which means a board and the run it is showing cannot be reading
two different files — the disagreement a sibling project shipped and could not see from inside
the run.

**One lock, and it is here rather than in each caller.** A SQLite connection opened with
`check_same_thread=False` does not stop two threads interleaving cursors on it; it only stops
SQLite complaining about which thread. The board polls every two seconds and a decision arrives
from the same second, so the contended case is the ordinary one.
"""

from __future__ import annotations

import functools
import sqlite3
import threading
from pathlib import Path

WHERE_THE_REGISTER_LIVES_BY_DEFAULT = "aisdlc.sqlite3"

_the_lock = threading.Lock()
_the_connection: sqlite3.Connection | None = None


class NoRegisterHasBeenOpenedError(Exception):
    """Something asked for the register before anything opened one.

    **Raised rather than opening a file on the spot.** A caller reaching for the register
    before the composition root has run is a wiring mistake, and silently creating a second
    SQLite file in whatever directory the process happened to start in is how a board ends up
    showing an empty register while a run writes a full one somewhere nobody looks.
    """


def the_register_lives_at(where: Path) -> None:
    """Say which file is the register, and open it. Called once, by whatever starts the process."""
    global _the_connection

    with _the_lock:
        if _the_connection is not None:
            _the_connection.close()
        where.parent.mkdir(parents=True, exist_ok=True)
        _the_connection = sqlite3.connect(where, check_same_thread=False)
        _the_connection.row_factory = sqlite3.Row


def where_the_register_should_live() -> Path:
    """The register's file: one file, in the directory every run's directory also hangs off.

    **Beside the projects and not among them.** The register is one file describing many runs; the
    projects are a directory per run. Putting it at the root of the projects directory means a
    person who opens that directory sees a register and a pile of run directories, which is what
    the directory is — and a `glob("*/")` over it does not pick the register up as a run.
    """
    from aisdlc.tools.the_project_directory import where_projects_live

    return where_projects_live() / WHERE_THE_REGISTER_LIVES_BY_DEFAULT


def the_register() -> sqlite3.Connection:
    """The one connection, held for the length of whatever the caller is doing with it.

    **A caller that wants it for one read should use `holding_the_register`** — this hands over
    a connection and the caller is then responsible for not letting two threads touch it, which
    is a rule nobody can follow by accident.
    """
    if _the_connection is None:
        raise NoRegisterHasBeenOpenedError(
            "nothing has opened the register yet. A process that serves a board or runs a "
            "pipeline calls `the_register_lives_at` once at startup, before anything asks for "
            "it — and nothing opens a file on the spot, because a register opened in the "
            "wrong directory is a register nobody is looking at"
        )
    return _the_connection


def holding_the_register():
    """The connection and its lock together, for a caller that is about to use it.

    A context manager rather than a function returning a pair, so the `with` reads as what it
    is: everything inside is the only thing touching the register.
    """

    class _Holding:
        def __enter__(self) -> sqlite3.Connection:
            _the_lock.acquire()
            return the_register()

        def __exit__(self, *_: object) -> None:
            _the_lock.release()

    return _Holding()


def the_endpoint_touches_the_register(an_endpoint):
    """Hold the register's lock for the length of one call, without changing what it takes.

    **A decorator rather than a context manager applied inside each handler,** because a
    handler that acquires the lock by hand is a handler whose author can forget. This one cannot
    be forgotten, and it does not pass a connection in — the endpoint reads the module's
    connection itself, because that is the connection the recorders are writing through and
    passing a different one would be the bug this lock exists to prevent.

    **The same lock the recorders take, not one of its own.** Two locks on one SQLite connection
    is the same as no lock at all: the readers interleave with each other perfectly and then
    collide with the run. That is not a theoretical failure — it is what a board polling every
    two seconds did to a run writing a decision in the same second, and it arrives as
    `InterfaceError: bad parameter or other API misuse` from a query that worked a moment ago.
    """

    @functools.wraps(an_endpoint)
    def one_at_a_time(*arguments: object, **keywords: object) -> object:
        with holding_the_register():
            return an_endpoint(*arguments, **keywords)

    return one_at_a_time
