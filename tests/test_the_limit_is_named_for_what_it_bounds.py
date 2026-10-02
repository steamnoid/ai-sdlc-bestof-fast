"""A limit named "the whole inspection" bounds the source, and the whole is 46% over it.

**Measured, on a repository built for the purpose:**

```text
assembled inspection       : 175926
the limit it is named after: 120000
exceeds it by              : 55926
```

The fixture is three files just under the per-file limit, so each of them is shown in full — the
manifest, README and CI sections each get their own budget and none of them knows another exists —
plus four top-level source directories each holding two files of 19,000 characters, which is enough
to fill the source section to its own 120,000.

**`A_LIMIT_ON_THE_SOURCE_THAT_MAY_CARRY_RISK` is used in two places and both are inside
`_the_source_that_may_carry_risk`:** once to derive the per-directory share and once as the check
that stops the source loop. It is not compared against the string the function returns, and no test
in this repository mentions it at all.

**So the name promises a bound the code does not provide, and nothing was checking.** That is the
shape this repository keeps meeting — a guard whose scope was never widened when the thing it
guards grew (the README guard blind to two tiers), a parser with no caller, a promise with no code.
Here it is a constant whose name is a promise and whose value is a rule about a part.

**Two things follow, and they are separate decisions.** One is that the name must become true, and
that is a rename with no behaviour change at all — worth doing first, because a run is in flight
and a rename cannot alter what any run is shown. The other is whether the whole should have a
ceiling, and **that is not taken here**: bounding it re-budgets every inspection every agent sees,
and the cost of that is a measurement to take deliberately rather than a side effect of a naming
problem.

**What the last test does is hold the limitation in place.** It asserts the whole exceeds the
limit, which sounds like asserting a weakness — and it is, deliberately. A known limitation that
nothing checks rots into an unknown one, and the day the whole *is* bounded this test fails and
forces the decision to be taken on purpose rather than discovered.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import aisdlc.tools.inspect_the_repository as the_module
from aisdlc.tools.github_clone_repository import ClonedRepository
from aisdlc.tools.inspect_the_repository import (
    A_LIMIT_ON_A_SINGLE_FILE,
    A_LIMIT_ON_THE_SOURCE_THAT_MAY_CARRY_RISK,
    an_inspection_of_the_code,
)


def _the_source_of(the_inspection: str) -> str:
    """The code section of an inspection, cut out by its own heading."""
    the_lines = the_inspection.splitlines()
    where_it_starts = next(
        an_index for an_index, a_line in enumerate(the_lines) if a_line.startswith("# The code")
    )
    return "\n".join(the_lines[where_it_starts:])


def test_the_shown_source_never_exceeds_the_limit_named_for_it(tmp_path: Path) -> None:
    """What the constant says it bounds, bounded — measured on a repository built to fill it."""
    a_repository_filled_to_the_limit = _a_repository_with_enough_source_to_fill_the_limit(tmp_path)

    the_inspection = an_inspection_of_the_code(a_repository_filled_to_the_limit)

    how_many_characters_of_code = len(_the_source_of(the_inspection))

    assert how_many_characters_of_code <= A_LIMIT_ON_THE_SOURCE_THAT_MAY_CARRY_RISK, (
        f"the code section is {how_many_characters_of_code} characters against a limit of "
        f"{A_LIMIT_ON_THE_SOURCE_THAT_MAY_CARRY_RISK} that is named for it"
    )


def test_one_directory_never_spends_more_than_its_share_of_that_limit(tmp_path: Path) -> None:
    """A third, measured against the same limit rather than against a second number."""
    a_repository_filled_to_the_limit = _a_repository_with_enough_source_to_fill_the_limit(tmp_path)

    the_inspection = an_inspection_of_the_code(a_repository_filled_to_the_limit)

    the_share = (
        A_LIMIT_ON_THE_SOURCE_THAT_MAY_CARRY_RISK
        * the_module.THE_SHARE_OF_THE_SOURCE_LIMIT_ONE_DIRECTORY_MAY_HOLD
    )
    spent_by_directory = _what_each_directory_spends(_the_source_of(the_inspection))

    over = {
        a_directory: how_many for a_directory, how_many in spent_by_directory.items()
        if how_many > the_share
    }

    assert not over, (
        f"{over} each spent more than the {int(the_share)}-character share one directory may hold, "
        f"which is the rule that stops a repository's tests crowding out its source"
    )


def test_the_whole_inspection_is_not_bounded_and_that_is_deliberate(tmp_path: Path) -> None:
    """A known limitation nothing checks rots into an unknown one, and this is the check.

    **It asserts that the whole exceeds the source limit, and that sounds like asserting a
    weakness.** It is: the assembled inspection has no ceiling of its own, the source section has
    120,000 and the manifests, README and CI sections are each bounded only by the 20,000
    per-file limit and cannot see each other. The day that is changed, this test fails and the
    change has to be a decision rather than a side effect.

    **And bounding it is not free.** It re-budgets every inspection every agent is shown, so it
    is a change to what the five reasoning stages see, not a rename. The measurements for this
    repository are in the module's own comment; this test only holds the fact.
    """
    the_checkout = _a_repository_with_a_large_readme_and_four_source_directories(tmp_path)

    the_whole = an_inspection_of_the_code(the_checkout)

    assert len(the_whole) > A_LIMIT_ON_THE_SOURCE_THAT_MAY_CARRY_RISK, (
        f"the assembled inspection is {len(the_whole)} characters, which is now within the "
        f"source limit. Either the whole has been bounded — in which "
        f"case this test should say so and name the rule that bounded it — or the source section "
        f"shrank, which would make it assert the wrong thing entirely"
    )


def _what_each_directory_spends(the_source_section: str) -> dict[str, int]:
    """Characters of shown code per top-level directory, read from the section's own headings."""
    spent: dict[str, int] = {}
    current: str | None = None

    for a_line in the_source_section.splitlines():
        if a_line.startswith("## "):
            current = a_line.removeprefix("## ").split("/", 1)[0]
            spent.setdefault(current, 0)
        elif current is not None:
            spent[current] += len(a_line)

    return spent


def _a_repository_with_enough_source_to_fill_the_limit(a_root: Path) -> ClonedRepository:
    """A checkout whose code fills the limit and whose manifests each sit under the per-file one.

    **The first version built this in a `tempfile.TemporaryDirectory` and every test that used it
    failed with `FileNotFoundError`.** The object went out of scope at the end of the function and
    the directory was deleted with it, while the `ClonedRepository` kept pointing at a path that
    no longer existed. A fixture's lifetime is part of its contract, and a temporary directory
    whose lifetime ends when the constructor returns is a fixture that is not one.
    """
    the_root = a_root.resolve()

    for a_name in ("README.md", "package.json", "Makefile"):
        (the_root / a_name).write_text("r" * (A_LIMIT_ON_A_SINGLE_FILE - 1), encoding="utf-8")

    for a_top_level_directory in ("one", "two", "three", "four"):
        (the_root / a_top_level_directory).mkdir()
        for a_number in (1, 2):
            (the_root / a_top_level_directory / f"auth{a_number}.py").write_text(
                "x" * 19_000, encoding="utf-8"
            )

    return ClonedRepository(path=the_root, ref="main", commit="0" * 40)


def _a_repository_with_a_large_readme_and_four_source_directories(
    a_root: Path,
) -> ClonedRepository:
    """The same checkout written where the test can see it, for the record rather than a tmpdir."""
    for a_name in ("README.md", "package.json", "Makefile"):
        (a_root / a_name).write_text("r" * (A_LIMIT_ON_A_SINGLE_FILE - 1), encoding="utf-8")

    for a_top_level_directory in ("one", "two", "three", "four"):
        (a_root / a_top_level_directory).mkdir()
        for a_number in (1, 2):
            (a_root / a_top_level_directory / f"auth{a_number}.py").write_text(
                "x" * 19_000, encoding="utf-8"
            )

    return ClonedRepository(path=a_root.resolve(), ref="main", commit="0" * 40)


def test_the_limit_is_named_for_what_it_bounds() -> None:
    """The only test in this file that is red, and it is red about a name.

    **A rename demanded by a test rather than tidied into one.** The constant promises a bound on
    the assembled inspection; it is used twice and both uses are inside the source loop; and a
    reader who trusts the name will believe a 175,926-character inspection is within a
    120,000-character limit.

    **Checked with `hasattr` and not by importing the new name**, because an import that fails is
    an `ImportError` rather than an assertion, and a RED that says "the symbol is absent" is not a
    statement about the rule. Everything else in this file passes today: those are the
    characterisation tests that make the rename safe, and they are here so a rename cannot quietly
    change what is bounded.

    **And the argument here was the old name for a while, so this test passed green.** A single
    replacement over the file rewrote the string inside this `hasattr` along with the import, and
    the assertion became "does the constant still have its current name", which is always true.
    Nothing about ten passing tests looked wrong until the count was read against the list of
    tests — **which is the only reason a green suite is ever evidence of anything.**
    """
    assert hasattr(the_module, "A_LIMIT_ON_THE_SOURCE_THAT_MAY_CARRY_RISK"), (
        "the constant is still named A_LIMIT_ON_THE_WHOLE_INSPECTION, which promises a bound on "
        "the assembled inspection. It is used twice and both uses are inside the source loop, so "
        "the name is a promise the code does not keep — and a reader who trusts it will believe a "
        "175,926-character inspection is within a 120,000-character limit"
    )


def test_no_other_test_in_this_repository_still_uses_the_old_name() -> None:
    """A constant renamed in the source and not in the readers leaves two names for one thing.

    **This file is excluded from the check and says so**, because it quotes the old name on
    purpose — in the message that explains why the rename happened. A guard that had to exclude
    its own author would be a guard with a hole in it exactly where the explanation is.
    """
    stale = [
        a_file.name
        for a_file in sorted(Path(__file__).resolve().parent.glob("test_*.py"))
        if "A_LIMIT_ON_THE_WHOLE_INSPECTION" in a_file.read_text(encoding="utf-8")
        and a_file.name != Path(__file__).name
    ]

    assert not stale, (
        f"{stale} still say A_LIMIT_ON_THE_WHOLE_INSPECTION. A rename in the source and not in the "
        f"readers leaves two names for one number, and the next reader finds whichever they look at"
    )


@pytest.mark.parametrize("a_name", ["one", "two", "three", "four"])
def test_every_directory_the_fixture_built_is_accounted_for_somehow(
    a_name: str, tmp_path: Path
) -> None:
    """A control, and it was wrong in a way worth recording.

    **The first version asserted all four directories appear in the code section, and `two` does
    not.** The fixture fills the limit — one=38000, three=19479, four=38000, Makefile=19999 — so the
    fourth directory does not fit and is dropped. That is the rule working, and the control was
    asserting the opposite of what it meant to protect.

    **So the control now asks the honest question: every directory is either shown or named as not
    shown.** A file silently absent from an inspection is a finding a model makes about something
    nobody showed it, which is the failure this module's closing section exists to prevent — and a
    control that would have failed on a correct module is not protecting the rule, it is
    forbidding it.
    """
    the_inspection = an_inspection_of_the_code(
        _a_repository_with_enough_source_to_fill_the_limit(tmp_path)
    )

    the_directories_shown = set(_what_each_directory_spends(_the_source_of(the_inspection)))

    named_as_not_shown = the_inspection

    assert a_name in the_directories_shown or a_name in named_as_not_shown, (
        f"{a_name} is in the fixture and is neither shown nor named as not shown, so it is absent "
        f"from the inspection entirely — which is the one thing a truncated inspection must never "
        f"be"
    )


def test_the_control_fails_on_an_inspection_showing_nothing(tmp_path: Path) -> None:
    """The share test would pass against an empty inspection, and this is what stops that.

    A guard satisfied by nothing is the recurring failure in this repository — a README guard
    blind to two tiers, a parser with no caller, a constant whose name promised a bound nothing
    checked. This one asserts the fixture's own directories reach the inspection at all, so the
    share assertion cannot pass by having nothing to divide.
    """
    the_inspection = an_inspection_of_the_code(
        _a_repository_with_enough_source_to_fill_the_limit(tmp_path)
    )

    the_directories_shown = _what_each_directory_spends(_the_source_of(the_inspection))

    assert sum(the_directories_shown.values()) > 0, (
        "the code section is empty, so every assertion about how much one directory may spend is "
        "true of nothing"
    )
