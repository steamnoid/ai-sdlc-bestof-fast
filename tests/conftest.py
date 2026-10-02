"""What every test inherits, and the one thing that must not be inherited.

**The register is one connection for the whole process, and four test files open it at a
`tmp_path`.** Without this fixture the last of those tests owns the connection until the session
ends, pointing at a directory pytest has already deleted — so the next test that reads the
register inherits a handle to a file that is not there, and whether that fails depends on what
the previous test wrote and on the order they ran in.

**That is a suite whose result is not a function of the code.** A red run reads as a fact about
the change and a green run reads as a fact about the change, and neither is one. This was blamed
on stale bytecode for four runs before it was read properly; bytecode was a coincidence, and
attributing a false failure to it is how a false failure becomes normal.

**One fixture, no cleverness.** Anything that opens the register is closed after every test, so a
test cannot see another's handle whether or not it touched the register itself.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def no_test_inherits_the_register() -> None:
    """Close the register after every test, whether or not this one opened it."""
    from aisdlc.store.where_the_register_lives import the_register_is_closed

    yield

    the_register_is_closed()
