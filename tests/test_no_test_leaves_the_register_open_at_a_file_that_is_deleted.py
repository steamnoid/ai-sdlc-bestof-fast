"""No test may leave the register open at a path pytest is about to delete.

**The register is one process-wide connection and four test files open it at a `tmp_path`.**
`the_register_lives_at` closes the previous connection and opens the new one, so the last test
that opens it owns the connection for the rest of the session — pointing at a `tmp_path` pytest
deletes when that test ends. Nothing raises at that moment. The next test that reads the register
inherits a connection to a file that is not there, and whether that fails depends on what the
previous test happened to write and on the order the tests ran in.

**That is a suite whose result is not a function of the code.** It is the worst kind of failure,
because a red run reads as a fact about the change and a green run reads as a fact about the
change, and neither is one.

**Checked by reading the tests rather than by running them twice**, in the idiom the repository
already uses for "every stage reasons about files": a call is looked for, and so is its opposite.
A test that opens the register and never closes it is not a slow test, it is a change to what the
next test means.
"""

from __future__ import annotations

import ast
from pathlib import Path

WHERE_THE_TESTS_ARE = Path(__file__).resolve().parent


def _every_call_in_the_tests() -> list[tuple[Path, str]]:
    """Every `something(...)` call in every test file, with the file it was read from."""
    the_calls: list[tuple[Path, str]] = []

    for a_test_file in sorted(WHERE_THE_TESTS_ARE.rglob("test_*.py")):
        the_tree = ast.parse(a_test_file.read_text(encoding="utf-8"))
        for a_statement in ast.walk(the_tree):
            if not isinstance(a_statement, ast.Call):
                continue
            # **Both shapes, and the first version of this guard had only one.** `the_register_
            # lives_at(x)` parses as an `ast.Name`, whose `.attr` does not exist — so the guard
            # found no calls at all and passed. A guard that reads "no calls" as "no problem" is
            # worse than no guard, because it is green and claims to be looking.
            if isinstance(a_statement.func, ast.Attribute):
                the_calls.append((a_test_file, a_statement.func.attr))
            elif isinstance(a_statement.func, ast.Name):
                the_calls.append((a_test_file, a_statement.func.id))

    return the_calls


def test_one_autouse_fixture_closes_the_register_after_every_test() -> None:
    """Uniform, in one place, rather than per file — because per file is what gets forgotten.

    **My first version of this rule asked each file that opens the register to close it**, and
    that is the wrong shape: four files, four chances to forget, and forgetting is silent. The
    guarantee that matters is that no test can see another's handle, and that is a property of
    the session rather than of any one test.

    So the rule is one autouse fixture in `tests/conftest.py`, and **this test fails if the
    fixture stops being autouse** — which is the change that would quietly undo the fix while
    every test still passed.
    """
    where_the_fixture_is = WHERE_THE_TESTS_ARE / "conftest.py"
    assert where_the_fixture_is.is_file(), (
        f"{where_the_fixture_is.name} is gone, and with it the only thing that closes the "
        "register between tests. Four test files open it at a tmp_path pytest deletes, so "
        "without it the last of them owns the connection for the rest of the session"
    )

    the_fixture = ast.parse(where_the_fixture_is.read_text(encoding="utf-8"))

    the_autouse_fixtures = [
        a_function
        for a_function in the_fixture.body
        if isinstance(a_function, ast.FunctionDef)
        and any(
            getattr(a_decorator.func, "attr", None) == "fixture"
            # **A keyword, not a positional argument**, and the first version of this detector
            # looked in `args` and therefore found no autouse fixture in a file that has one.
            and any(
                a_keyword.arg == "autouse"
                and getattr(a_keyword.value, "value", False) is True
                for a_keyword in a_decorator.keywords
            )
            for a_decorator in a_function.decorator_list
            if isinstance(a_decorator, ast.Call)
        )
    ]

    assert the_autouse_fixtures, (
        f"{where_the_fixture_is.name} opens the register but closes it in no autouse fixture, so "
        "the closing happens only in whichever test happened to remember it"
    )

    for a_fixture_function in the_autouse_fixtures:
        # **Both call shapes again.** The fixture imports what it calls inside its own body,
        # so the call parses as an `ast.Name`; a walk that only looked at `ast.Attribute` found
        # just `fixture` and reported a working fixture as doing nothing. The same trap has been
        # sprung on this file three times now, in three different guards.
        the_names_it_calls = {
            a_statement.func.attr
            if isinstance(a_statement.func, ast.Attribute)
            else a_statement.func.id
            for a_statement in ast.walk(a_fixture_function)
            if isinstance(a_statement, ast.Call)
            and isinstance(a_statement.func, (ast.Attribute, ast.Name))
        }
        assert "the_register_is_closed" in the_names_it_calls, (
            f"{a_fixture_function.name} is autouse but does not close the register, so adding it "
            "changed nothing. This guard is the only thing standing between the suite and a "
            "result that depends on test order"
        )


def test_closing_the_register_leaves_it_closed_and_the_run_greener_for_it() -> None:
    """Closing has to mean closed, not merely quiet — a suppressed handle is still open.

    **The state that matters is `None`.** A connection that has been closed but is still held is
    an open handle to a deleted file wearing a hat, and `the_register()` would hand it out again.
    """
    from aisdlc.store.where_the_register_lives import (
        NoRegisterHasBeenOpenedError,
        the_register,
        the_register_is_closed,
        the_register_lives_at,
    )

    a_directory = WHERE_THE_TESTS_ARE.parent / ".a-register-written-by-a-test"
    a_directory.mkdir(exist_ok=True)
    the_register_lives_at(a_directory / "the-register.sqlite3")
    the_register_is_closed()

    try:
        the_register()
    except NoRegisterHasBeenOpenedError:
        return
    finally:
        the_register_is_closed()
        (a_directory / "the-register.sqlite3").unlink(missing_ok=True)
        a_directory.rmdir()

    raise AssertionError(
        "the_register() answered after the register was closed, so closing it did not close it: "
        "the handle is still held and will be handed out again, pointing at a file that is gone"
    )
