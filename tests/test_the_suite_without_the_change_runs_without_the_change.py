"""The third suite run must be a suite *without* the change, and a plan can stop that.

**The undo hands git one list, and git stops at a path the parent commit does not have.** This
repository's own finding about that is in `test_an_undo_git_cannot_do_stops_it.py`: a
`git checkout HEAD~1 -- a b` where `a` is new aborts with `pathspec ... did not match any file(s)
known to git` and **undoes nothing at all**, not even `b`.

**And `_the_suite_with_the_change_put_back` hands it `plan.files_to_change` verbatim.** So a plan
that lists a file it also created does not undo its change for the third suite run — it runs the
suite against the repository **with** the change, reads the result as *without*, and
`refuse_a_change_nothing_observed` refuses a change that was never checked. **The refusal is
right and its reason is wrong**, and the two are indistinguishable from outside: one
`StateMachineError`-shaped stop with a message.

**A real run is why this is a test and not a note.** A supervisor wrote on its card, *"the
approved plan still names only test files and no product file, so the new test cannot fail when the
change is undone."* **The first half was a guess about the plan and the second half was this
mechanism**, and neither the run nor the person reading it could tell them apart.

**A plan is allowed to be wrong about which list a file belongs in.** `plan_the_change` proves the
paths of `files_to_change` exist, and a model that puts a new file there anyway has not broken a
rule so much as answered wrongly. **So the undo does not trust the plan's arithmetic** — it asks
git about paths git can answer about, which is the only version of the question git answers.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from aisdlc.agents.apply_the_plan import _the_suite_with_the_change_put_back
from aisdlc.agents.implementation_plan import ImplementationPlan
from aisdlc.domain.repository import Repository
from aisdlc.tools.github_clone_repository import ClonedRepository
from aisdlc.tools.run_tests import SuiteOutcome

_A_REPOSITORY = Repository(owner="an", name="owner")

_A_PLAN_THAT_NAMES_THE_FILE_IT_ADDED = ImplementationPlan(
    files_to_change=[
        "web-app/src/lib/auth.js",
        "tests/unit/the-regression.test.ts",
    ],
    files_to_add=[],
    tests_to_add=["tests/unit/the-regression.test.ts"],
)


def test_the_suite_without_the_change_runs_without_the_change(tmp_path: Path) -> None:
    """A real repository, a real change, and what is on disk at the moment the suite is asked.

    **The stub suite reads the working tree rather than returning a value**, because the value is
    not what is in question — the repository the suite would have run is. It records the two files
    that matter and hands them back, so the assertion below is about **the state the third run
    actually met** rather than about what the function returned.

    **Both files, because they are the two halves of the mechanism.** The edited one has to be
    back to its previous contents, or the run is not a run without the change. The added one has to
    still be there, or the suite is one test short of the one it is comparing against — and it
    cannot be undone, because there is no `checkout` that removes a file.
    """
    the_repository = _a_repository_where_the_change_committed_one_file(tmp_path)
    what_the_suite_found: dict[str, str | None] = {}

    def read_the_working_tree(clone: ClonedRepository, repository: Repository) -> SuiteOutcome:
        what_the_suite_found["the_edited_file"] = (
            the_repository / "web-app/src/lib/auth.js"
        ).read_text(encoding="utf-8")
        what_the_suite_found["the_added_test"] = (
            the_repository / "tests/unit/the-regression.test.ts"
        ).read_text(encoding="utf-8")
        return SuiteOutcome(
            exit_code=0, passed=True, dependencies_installed=True, output="the stub suite"
        )

    answering_without_the_change = _the_suite_with_the_change_put_back(
        ClonedRepository(path=the_repository, ref="main", commit="0" * 40),
        _A_REPOSITORY,
        _A_PLAN_THAT_NAMES_THE_FILE_IT_ADDED,
        read_the_working_tree,
    )
    answering_without_the_change()

    assert "dev-secret-change-me" not in (what_the_suite_found["the_edited_file"] or ""), (
        "the suite ran while the change was still in the working tree, because the plan named a "
        "file the change added and git would not undo a list holding one. **This is the whole of "
        "the bug**: the run reads that result as a suite without the change, and it is a suite "
        "with it, so a change nothing observed and a change that was never checked look identical"
    )
    assert what_the_suite_found["the_added_test"] is not None, (
        "the suite ran with the test the plan added taken away, and a suite without the test that "
        "watches the change says nothing either way — so the answer it gives is about a suite "
        "nobody wrote"
    )


def test_the_change_is_back_after_the_run(tmp_path: Path) -> None:
    """The `finally` that puts the change back, asked for with a plan that broke the first undo.

    **This is here because the fix makes the first undo work, and that is what exposes the
    second.** Until the undo does anything, the `finally` had nothing to undo; once it does, a
    suite that raises leaves the delivery pushing a working tree without the change — and the
    module's own docstring says that is worse than the bug this rule exists to catch.
    """
    the_repository = _a_repository_where_the_change_committed_one_file(tmp_path)

    def refuse_to_run(clone: ClonedRepository, repository: Repository) -> SuiteOutcome:
        raise RuntimeError("the suite could not be run at all")

    answering_without_the_change = _the_suite_with_the_change_put_back(
        ClonedRepository(path=the_repository, ref="main", commit="0" * 40),
        _A_REPOSITORY,
        _A_PLAN_THAT_NAMES_THE_FILE_IT_ADDED,
        refuse_to_run,
    )

    try:
        answering_without_the_change()
    except RuntimeError:
        pass
    else:
        raise AssertionError("the suite was supposed to refuse to run, and did not")

    assert "dev-secret-change-me" in (
        the_repository / "web-app/src/lib/auth.js"
    ).read_text(encoding="utf-8"), (
        "the suite failed and the change stayed undone, so the delivery that follows pushes a "
        "working tree without the work — a pull request that silently drops the change instead of "
        "reporting that its tests could not be run"
    )


def _a_repository_where_the_change_committed_one_file(tmp_path: Path) -> Path:
    """A repository with one commit behind the change, and a change that edits one file and adds
    another.

    **Built rather than copied, because the shape is the claim.** The added file has to be new in
    the change's commit, or git would match it in `HEAD~1` and there would be nothing here to find.
    """
    the_repository = tmp_path / "the-repository"
    the_repository.mkdir()
    _git(the_repository, "init", "--initial-branch=main")

    the_edited_file = the_repository / "web-app" / "src" / "lib" / "auth.js"
    the_edited_file.parent.mkdir(parents=True)
    the_edited_file.write_text(
        "const secret = process.env.JWT_SECRET || 'from-the-environment';\n", encoding="utf-8"
    )
    _git(the_repository, "add", ".")
    _git(the_repository, "commit", "-m", "what the repository had")

    the_edited_file.write_text("const fallback = 'dev-secret-change-me';\n", encoding="utf-8")
    the_added_test = the_repository / "tests" / "unit" / "the-regression.test.ts"
    the_added_test.parent.mkdir(parents=True)
    the_added_test.write_text("it('no literal fallback', () => {});\n", encoding="utf-8")
    _git(the_repository, "add", ".")
    _git(the_repository, "commit", "-m", "the change")
    return the_repository


def _git(where: Path, *what: str) -> str:
    """One `git` call, with an identity named on it so nothing here reads the machine's config."""
    what_happened = subprocess.run(
        ["git", "-c", "user.name=a test run", "-c", "user.email=a-test-run@example.com", *what],
        cwd=where,
        capture_output=True,
        text=True,
        check=False,
    )
    if what_happened.returncode != 0:
        raise AssertionError(f"git {' '.join(what)} failed: {what_happened.stderr}")
    return what_happened.stdout