"""A pathspec git cannot match stops the whole undo, and the undo does not say so.

**Found by running git, after I concluded the opposite by reading the argument list.** Two claims
about this mechanism have been written down in this repository and only one of them survived
running it. **The surviving one is here**, and it is the dangerous one:

```text
$ git checkout HEAD~1 -- tests/unit/the-regression.test.ts web-app/src/lib/auth.js
error: pathspec 'tests/unit/the-regression.test.ts' did not match any file(s) known to git
$ cat web-app/src/lib/auth.js
const fallback = 'dev-secret-change-me';
$ git checkout HEAD~1 -- web-app/src/lib/auth.js        # the same file, alone
$ cat web-app/src/lib/auth.js
const secret = process.env.JWT_SECRET || 'from-the-environment';
```

**`git checkout` aborts at the first pathspec it cannot match and undoes nothing at all** — and it
aborts wherever the unmatched path sits in the list, because git resolves the whole list before
writing. `apply_the_plan._the_suite_with_the_change_put_back` hands it `plan.files_to_change` in one
call, so **a plan that names a file it also created makes the third suite run happen against the
repository *with* the change.**

**Which is why a change nothing observed looks exactly like a change that was never checked.**
`refuse_a_change_nothing_observed` reads that third run as *the suite without the change*, and a
suite that still contains the change is green for exactly the reason the rule exists to detect — the
change was invisible to the tests. **The refusal is right and its reason is wrong**, and nothing in
the record says which happened: both are one `StateMachineError`-shaped stop with a message.

**A real run is why this is worth a test.** A supervisor wrote, on the card, *"the approved plan
still names only test files and no product file, so the new test cannot fail when the change is
undone"* — and **the second half of that sentence was true for a reason neither of us could see from
the argument list.** The first half was a guess; the second was the mechanism, exactly.

**And the fix is to not ask git a question it will refuse to answer**, which is why this file
asserts the behaviour of the list rather than the behaviour of git: a path the plan *added* is not
in `HEAD~1`, and there is no `checkout` that removes a file.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def test_an_undo_that_names_a_file_git_cannot_match_undoes_nothing(tmp_path: Path) -> None:
    """Real git, a real change, and the list that makes the third suite run measure nothing.

    **Three facts asserted, in the order they can be checked.** That the checkout reports a
    pathspec it cannot match; **that the file it was asked to undo still holds the change** — which
    is the fact this file exists for; and that the same file undoes cleanly on its own, which is
    what makes the first half a fact about the list rather than about git being unable to undo.
    """
    the_repository = tmp_path / "the-repository"
    the_repository.mkdir()
    _git(the_repository, "init", "--initial-branch=main")

    the_file_the_change_edits = the_repository / "web-app" / "src" / "lib" / "auth.js"
    the_file_the_change_edits.parent.mkdir(parents=True)
    the_file_the_change_edits.write_text(
        "const secret = process.env.JWT_SECRET || 'from-the-environment';\n", encoding="utf-8"
    )
    _git(the_repository, "add", ".")
    _git(the_repository, "commit", "-m", "what the repository had")

    the_file_the_change_edits.write_text(
        "const fallback = 'dev-secret-change-me';\n", encoding="utf-8"
    )
    the_test_the_plan_added = the_repository / "tests" / "unit" / "the-regression.test.ts"
    the_test_the_plan_added.parent.mkdir(parents=True)
    the_test_the_plan_added.write_text("it('no literal fallback', () => {});\n", encoding="utf-8")
    _git(the_repository, "add", ".")
    _git(the_repository, "commit", "-m", "the change")

    what_git_said = _git_allowing_an_unmatched_pathspec(
        the_repository,
        "checkout",
        "HEAD~1",
        "--",
        str(the_test_the_plan_added.relative_to(the_repository)),
        str(the_file_the_change_edits.relative_to(the_repository)),
    )

    assert "did not match any file(s) known to git" in what_git_said, (
        f"git said {what_git_said!r} about a path its parent commit does not have. **This test is "
        "reading a git whose message for an unmatched pathspec has changed**, and the behaviour "
        "below is worth more than the message — so the message is asserted, not depended on"
    )
    assert "dev-secret-change-me" in the_file_the_change_edits.read_text(encoding="utf-8"), (
        "the file the change edited was undone, so on this git an unmatched pathspec does not stop "
        "the checkout. **Then the third suite run really is a suite without the change, the rule's "
        "assumption holds, and this file is measuring something git no longer does** — which is "
        "worth knowing rather than assuming, because it is the whole of `apply_the_plan`'s undo"
    )

    _git(
        the_repository,
        "checkout",
        "HEAD~1",
        "--",
        str(the_file_the_change_edits.relative_to(the_repository)),
    )
    assert "dev-secret-change-me" not in the_file_the_change_edits.read_text(encoding="utf-8"), (
        "the same file undoes cleanly on its own, so the first half is about the list and not "
        "about git being unable to undo an edit"
    )


def _git(where: Path, *what: str) -> str:
    """One `git` call, with an identity named on it so nothing here reads the machine's config."""
    return _run(where, check_a_failure=True, what=what)


def _git_allowing_an_unmatched_pathspec(where: Path, *what: str) -> str:
    """`git checkout` naming a path its parent commit does not have, which is what a plan does.

    **Not swallowed to make a test pass.** This git exits non-zero for a checkout that undid
    nothing, which is correct of git and useless to a caller: `_the_outcome_of` in this repository
    ignores the exit code of a `git checkout` and carries on. **So the helper asserts only that the
    command ran, and the assertions about what it did are the two in the test above.**
    """
    return _run(where, check_a_failure=False, what=what)


def _run(where: Path, *, check_a_failure: bool, what: tuple[str, ...]) -> str:
    what_happened = subprocess.run(
        [
            "git",
            "-c",
            "user.name=a test run",
            "-c",
            "user.email=a-test-run@example.com",
            *what,
        ],
        cwd=where,
        capture_output=True,
        text=True,
        check=False,
    )
    if check_a_failure and what_happened.returncode != 0:
        raise AssertionError(f"git {' '.join(what)} failed: {what_happened.stderr}")
    return f"{what_happened.stdout}{what_happened.stderr}"
