"""A path a plan says it will add must be a path, and `<…>` is not one.

**A real run wrote a plan that named its own new test as
`tests/unit/<jwt-secret-guard-test>.test.ts`.** Five gates approved and the sixth refused, and the
refusal was exact:

> The plan is not executable as written: `tests_to_add` names a placeholder path
> `<jwt-secret-guard-test>.test.ts` instead of a concrete test file, and `files_to_add` is empty
> even though a new unit test file is being added.

**The gate caught it. The plan should not have been writable that way**, because every check in
`plan_the_change` is a check about the clone — does this file exist, is that directory there, does
the runner collect it — and **none of them can notice that the string is not a path at all.** A file
that does not exist yet is exactly the case `tests_to_add` is for, so existence proves nothing about
it, and `tests/unit/` is a real directory, so that check passes too. **Today this plan passes every
check there is**, which is what these three tests are for.

**This is the same shape as `expect(true).toBe(true)`, filed as #40 on the fork**: a string shaped
like a value, carrying none. Here it is worse, because the string goes into a file written to disk
and into a commit message, and everything downstream is a delivery about a file whose name is
`<jwt-secret-guard-test>.test.ts`.

**Two characters, and no real path has either.** Angle brackets are what prose uses to mark the
place a value would go, and a filesystem path is not prose. **The rule is about the characters
rather than how the string looks**, because *looks like a path* is a judgement a model makes, and
this is a file that does arithmetic: a rule needing taste would be a rule nobody could check later.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from aisdlc.agents.implementation_plan import ImplementationPlan
from aisdlc.agents.plan_the_change import _every_file_to_change_is_in_the_clone
from aisdlc.domain.repository import Repository
from aisdlc.tools.github_clone_repository import ClonedRepository

_A_REPOSITORY = Repository(owner="an", name="owner")


def _a_clone_holding(temporary: Path, what_it_holds: dict[str, str]) -> ClonedRepository:
    """A checkout on disk holding the given files, which is all these checks look at.

    **Built rather than faked, because these checks read the filesystem** and a clone at a path that
    does not exist would make every refusal look correct for the wrong reason.
    """
    for a_relative_path, its_contents in what_it_holds.items():
        where = temporary / a_relative_path
        where.parent.mkdir(parents=True, exist_ok=True)
        where.write_text(its_contents, encoding="utf-8")
    return ClonedRepository(path=temporary, ref="main", commit="0" * 40)


def _the_refusal_for(the_plan: ImplementationPlan, the_clone: ClonedRepository) -> str:
    """What the checks say about this plan, as the message a caller would read.

    **Returns the message rather than raising, because the rule does not exist yet and a test that
    imported its error class would fail to load.** A RED has to fail on an assertion about
    behaviour — an `ImportError` says the name is missing, which is a different finding from *this
    plan is accepted and should not be*.
    """
    try:
        _every_file_to_change_is_in_the_clone(the_clone, _A_REPOSITORY, the_plan)
    except Exception as refused:
        """Any refusal at all counts, because the point is what was said rather than what raised."""
        return str(refused)
    return ""


def test_a_placeholder_in_a_new_tests_name_is_refused(tmp_path: Path) -> None:
    """The exact string a real run produced, and a refusal naming it.

    **The exact path, not a smaller version of it.** The run wrote
    `tests/unit/<jwt-secret-guard-test>.test.ts`, so the test writes that: a check that caught
    `<jwt-secret-guard-test>` but not `<…>` somewhere would be a rule about one model's phrasing
    rather than about placeholders.
    """
    the_clone = _a_clone_holding(tmp_path, {"tests/unit/existing.test.ts": "it('a', () => {})\n"})
    the_plan = ImplementationPlan(
        tests_to_add=["tests/unit/<jwt-secret-guard-test>.test.ts"],
    )

    what_was_said = _the_refusal_for(the_plan, the_clone)

    assert what_was_said, (
        "this plan was accepted. **Its test's directory exists, its file is one the suite will "
        "collect, and the string itself is not a path** — so every check there is passed by a "
        "file named `tests/unit/<jwt-secret-guard-test>.test.ts`, which is what a run "
        "delivered and a gate then had to refuse"
    )
    assert "tests/unit/<jwt-secret-guard-test>.test.ts" in what_was_said, (
        f"the refusal was {what_was_said!r}. **A refusal that does not quote the path is "
        "advice with nothing in it**, and this run lost a whole gate to it"
    )


def test_a_placeholder_in_a_new_files_name_is_refused_too(tmp_path: Path) -> None:
    """`files_to_add` carries the same promise and is checked by the same function.

    **Two lists rather than one because they are two promises.** A file a change brings into being
    and a test a change brings into being are different things with different reasons to exist, and
    a check that guarded one of them would leave the other to be found by a person.
    """
    the_clone = _a_clone_holding(tmp_path, {"README.md": "# the repository\n"})
    the_plan = ImplementationPlan(files_to_add=["src/<the-new-module>.js"])

    assert _the_refusal_for(the_plan, the_clone), (
        "a placeholder in files_to_add was accepted, so the rule reads one of the two lists a plan "
        "makes about the files it brings and not the other"
    )


def test_a_real_path_with_awkward_characters_is_not_a_placeholder(tmp_path: Path) -> None:
    """The rule is two characters, and a real path may contain most others.

    **This is the half that keeps the rule from becoming a taste judgement.** Spaces, dashes, dots,
    parentheses and accents are all legal in a path, and a repository whose tests are named
    `prüfung für Änderung (2).test.ts` must not be refused for its filename.
    """
    the_clone = _a_clone_holding(
        tmp_path,
        {
            "tests/unit/existing.test.ts": "it('a', () => {})\n",
            "tests/unit/prüfung für Änderung (2).test.ts": "it('b', () => {})\n",
        },
    )
    the_plan = ImplementationPlan(
        tests_to_add=["tests/unit/prüfung für Änderung (2).test.ts"],
        files_to_change=["tests/unit/existing.test.ts"],
    )

    assert _the_refusal_for(the_plan, the_clone) == "", (
        "a real filename with spaces, accents and parentheses was refused as a placeholder, so the "
        "rule is about how a path looks rather than about the two characters prose uses for a value"
    )


def _unused(_: Any) -> None:
    """Nothing here needs a value of this type, and an unused import is a lint error."""
