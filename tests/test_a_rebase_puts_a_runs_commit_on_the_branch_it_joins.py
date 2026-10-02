"""A run that delivered a conflicting branch can put its commit on the branch it joins.

**This is the repair `WhatToDoAroundAConflict` offers and could not take.** A pull request GitHub
will not merge is a branch that has fallen behind the branch it joins, and the git operation that
fixes it is a rebase — which this repository had no tool for, so the decision it offers was a
contract with no action behind it. **Everything below runs real `git` against three real
repositories made on this machine**: the code everybody works on, this system's copy of it, and a
clone standing on both. A tool that moves a commit between branches is not proved by a transport
that answers.

**The three repositories are the deployment's own shape, and the order is a run's order.** The
run clones its own copy, commits in the clone, pushes that commit to a branch named after the work
item, and only then does the branch it joins move on underneath it — which is what `mergeable:
false` is. So the fixture builds exactly that, in that order, with the agent's identity supplied
on the command line the way `a_commit_recording_the_change` supplies it.

**Two remotes, and both are addressed by name.** `origin` is the copy this run may write to and
the branch it pushed is on it; `upstream` is where the branch it joins lives, and the newest
version of that branch has to be read from there. The obvious way to fetch is to compose an
address, and an address that can be fetched with a credential is an address that prints the
credential in git's own error message — which is why `the_clone_url_of` refuses to read the
environment at all. `test_no_command_this_tool_runs_carries_a_credential` is the assertion about
that, and it reads the arguments rather than trusting a convention.

**The branch may be moved only where this run left it, and git is what checks.** `create_a_branch_
on_a_remote` refuses to push a branch that is already on the remote, because a run must never move
a branch somebody else is using; a rebase has to do exactly that, so that refusal cannot simply be
relaxed. `--force-with-lease` is stated with the commit this run pushed: git compares it against
the branch as it is at the moment of the push and refuses if it is anywhere else. **The condition
is provable rather than assumed, and it is checked inside the operation rather than by a read this
system could lose a race with.**

**A rebase that would change nothing is refused rather than done, and that refusal is a bound.**
A merge refused as a conflict sends the run to this repair; a rebase that changes nothing puts the
pull request back in front of the same `mergeable: false`; the run asks the model again and gets
the same answer, forever. **A decision taken once about a fact that has not changed is not a
decision**, and the tool says so instead of leaving a node to decide it on a second visit.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from aisdlc.tools.github_clone_repository import ClonedRepository
from aisdlc.tools.rebase_the_branch_a_run_pushed import (
    TheBranchIsAlreadyOnWhatItWouldJoinError,
    TheBranchOnTheRemoteWasNotMovedError,
    TheRebaseFoundConflictsError,
    a_rebase_of_the_branch_a_run_pushed,
    rebase_the_branch_a_run_pushed,
)
from aisdlc.tools.run_command import ACommand

THE_BRANCH_A_RUN_DELIVERS_ON = "aisdlc/issue-1-a-run"
WHAT_THE_RUN_CHANGED = "what the run changed\n"
WHAT_THE_BASE_CHANGED = "what the base changed\n"


def _git(where: Path, *what: str) -> str:
    """One `git` call in one directory, and a failure a reader can act on rather than ignore."""
    what_happened = subprocess.run(
        ["git", *what], cwd=where, capture_output=True, text=True, check=False
    )
    if what_happened.returncode != 0:
        pytest.fail(f"git {' '.join(what)} in {where} failed: {what_happened.stderr}")
    return what_happened.stdout


def _a_repository_nobody_may_write(where: Path, what_it_holds: str) -> tuple[Path, Path]:
    """A bare repository and the working copy that fills it, with one commit on `main`."""
    the_bare = where / f"{what_it_holds}.git"
    the_bare.mkdir(parents=True)
    _git(the_bare, "init", "--bare", "--initial-branch=main")
    the_work = where / what_it_holds
    the_work.mkdir()
    _git(the_work, "init", "--initial-branch=main")
    _git(the_work, "config", "user.email", "a-run@example.com")
    _git(the_work, "config", "user.name", "a run")
    (the_work / "README.md").write_text(f"# {what_it_holds}\n", encoding="utf-8")
    _git(the_work, "add", ".")
    _git(the_work, "commit", "-m", "the first commit")
    _git(the_work, "remote", "add", "origin", str(the_bare))
    _git(the_work, "push", "origin", "main")
    return the_bare, the_work


def _our_copy_of(where: Path, the_code: Path) -> Path:
    """A bare repository holding the code's history, which is what a fork is to git."""
    our_copy = where / "our-copy.git"
    our_copy.mkdir()
    _git(our_copy, "init", "--bare", "--initial-branch=main")
    _git(where, "clone", str(the_code), str(where / "the-copy-made-from-the-code"))
    _git(where / "the-copy-made-from-the-code", "push", str(our_copy), "main")
    return our_copy


def _a_delivery_that_conflicts(
    tmp_path: Path, what_the_base_changes: str | None
) -> tuple[ClonedRepository, Path]:
    """A run that committed, pushed a branch, and then fell behind — and the remotes to prove it.

    **`what_the_base_changes` names the file the branch it joins moves on in.** `None` for a base
    that has not moved, which is the situation where there is nothing to rebase; `NOTES.md` for a
    base that moved on a different file, which rebases cleanly; `README.md` for a base that moved
    on the same one, which git cannot resolve. Three situations, one fixture, and no mocking of
    git anywhere in it.
    """
    the_code, the_codes_own_copy = _a_repository_nobody_may_write(tmp_path / "the-code", "the-code")
    our_copy = _our_copy_of(tmp_path, the_code)

    the_clone = tmp_path / "the-clone"
    _git(tmp_path, "clone", str(our_copy), str(the_clone))
    _git(the_clone, "remote", "add", "upstream", str(the_code))

    _the_run_wrote_its_change_and_pushed_it(
        the_clone, our_copy, (the_clone / "README.md"), WHAT_THE_RUN_CHANGED
    )

    if what_the_base_changes is not None:
        _the_base_moved_on(the_codes_own_copy, the_code, what_the_base_changes)

    return (
        ClonedRepository(
            path=the_clone, ref="main", commit=_git(the_clone, "rev-parse", "HEAD").strip()
        ),
        our_copy,
    )


def _the_run_wrote_its_change_and_pushed_it(
    the_clone: Path, our_copy: Path, the_file: Path, what_it_says: str
) -> None:
    """The commit a run makes and the branch it delivers on, which is what a rebase has to move."""
    the_file.write_text(what_it_says, encoding="utf-8")
    _git(the_clone, "add", "--", str(the_file.relative_to(the_clone)))
    _git(
        the_clone,
        "-c",
        "user.name=aisdlc-dev-impl",
        "-c",
        "user.email=aisdlc@localhost",
        "commit",
        "-m",
        "the change this run made",
    )
    _git(the_clone, "push", "origin", f"HEAD:refs/heads/{THE_BRANCH_A_RUN_DELIVERS_ON}")


def _the_base_moved_on(the_code_work: Path, the_code: Path, what_it_changes: str) -> None:
    """Somebody landed a change on the branch this run's pull request would join."""
    _git(the_code_work, "pull", "origin", "main")
    (the_code_work / what_it_changes).write_text(WHAT_THE_BASE_CHANGED, encoding="utf-8")
    _git(the_code_work, "add", ".")
    _git(the_code_work, "commit", "-m", "the base moved on")
    _git(the_code_work, "push", "origin", "main")


def _the_rebase_to_make(the_clone: ClonedRepository):
    """The request this tool is for, through its own builder rather than a constructor call."""
    return a_rebase_of_the_branch_a_run_pushed(
        the_clone, THE_BRANCH_A_RUN_DELIVERS_ON, "main"
    )


def _the_branch_as_the_remote_holds_it(our_copy: Path, branch: str) -> str:
    """What the remote has, read without changing it — the same question the push tool asks."""
    what_is_there = subprocess.run(
        ["git", "ls-remote", "--heads", str(our_copy), branch],
        capture_output=True,
        text=True,
        check=False,
    )
    the_words = what_is_there.stdout.split()
    return the_words[0] if the_words else ""


def test_a_run_that_pushed_a_branch_puts_its_commit_on_the_branch_it_joins(tmp_path: Path) -> None:
    """A conflicting delivery becomes one a maintainer can merge, and both changes are in it.

    **Three facts and each is a different failure.** The branch on the remote must carry the
    rebased commit, because a rebase nobody can see has changed nothing about the pull request;
    the run's own file must still be there, because a rebase that dropped the change is a tool
    working perfectly on the wrong thing; and the base's file must be there too, because a rebase
    that overwrote it is the same failure in the other direction.
    """
    the_clone, our_copy = _a_delivery_that_conflicts(tmp_path, "NOTES.md")
    the_commit_the_run_pushed = _git(the_clone.path, "rev-parse", "HEAD").strip()

    what_the_rebase_left = rebase_the_branch_a_run_pushed(
        _the_rebase_to_make(the_clone)
    )

    assert what_the_rebase_left.the_commit_it_was == the_commit_the_run_pushed, (
        f"the rebase says it started from {what_the_rebase_left.the_commit_it_was} rather than "
        f"from {the_commit_the_run_pushed}, which is the commit this run pushed — so the branch "
        "that moved is not the branch this run delivered"
    )
    assert what_the_rebase_left.the_commit_it_is_now != the_commit_the_run_pushed, (
        "the commit is unchanged, so nothing was rebased and this run was told a repair happened"
    )
    assert _the_branch_as_the_remote_holds_it(
        our_copy, THE_BRANCH_A_RUN_DELIVERS_ON
    ) == what_the_rebase_left.the_commit_it_is_now, (
        "the rebased commit is not the one on the remote, so the pull request still points at the "
        "conflicting commit and the conflict is exactly where it started"
    )

    what_the_maintainer_would_get = tmp_path / "what-the-remote-has"
    _git(tmp_path, "clone", "--branch", THE_BRANCH_A_RUN_DELIVERS_ON, str(our_copy),
         str(what_the_maintainer_would_get))
    assert (what_the_maintainer_would_get / "README.md").read_text(
        encoding="utf-8"
    ) == WHAT_THE_RUN_CHANGED, (
        "the run's own change is not in the branch a maintainer would merge, so the rebase threw "
        "away the delivery rather than moving it"
    )
    assert (what_the_maintainer_would_get / "NOTES.md").read_text(
        encoding="utf-8"
    ) == WHAT_THE_BASE_CHANGED, (
        "the base's change is not in the branch a maintainer would merge, so the delivery was "
        "replayed over it rather than onto it"
    )


def test_the_branch_is_only_moved_where_this_run_left_it(tmp_path: Path) -> None:
    """A branch that moved since this run pushed it is refused, and stays where it is.

    **This is the rule that makes a rebase safe, and it is not a read.** Reading the branch and
    comparing it would leave a window between the read and the push, and what that window admits
    is a commit somebody else pushed in between — destroyed. So the expectation goes into the push
    itself as a lease, and git refuses inside the same operation.

    **The branch is asserted afterwards, and not only the exception**, because a tool that raised
    after moving the branch would satisfy the first half of this test perfectly.
    """
    the_clone, our_copy = _a_delivery_that_conflicts(tmp_path, "NOTES.md")
    somebody_elses_work = tmp_path / "somebody-elses-working-copy"
    _git(
        tmp_path,
        "clone",
        "--branch",
        THE_BRANCH_A_RUN_DELIVERS_ON,
        str(our_copy),
        str(somebody_elses_work),
    )
    (somebody_elses_work / "THEIR_FILE.md").write_text("theirs\n", encoding="utf-8")
    _git(somebody_elses_work, "add", ".")
    _git(somebody_elses_work, "-c", "user.email=t@e.com", "-c", "user.name=t", "commit",
         "-m", "somebody else's commit")
    _git(somebody_elses_work, "push", "origin", f"HEAD:refs/heads/{THE_BRANCH_A_RUN_DELIVERS_ON}")
    where_the_branch_was_left = _the_branch_as_the_remote_holds_it(
        our_copy, THE_BRANCH_A_RUN_DELIVERS_ON
    )

    with pytest.raises(TheBranchOnTheRemoteWasNotMovedError):
        rebase_the_branch_a_run_pushed(_the_rebase_to_make(the_clone))

    assert _the_branch_as_the_remote_holds_it(
        our_copy, THE_BRANCH_A_RUN_DELIVERS_ON
    ) == where_the_branch_was_left, (
        "the branch on the remote moved even though the run was refused, which is the one outcome "
        "the lease exists to prevent"
    )


def test_a_rebase_that_would_change_nothing_is_refused_by_name(tmp_path: Path) -> None:
    """A branch already sitting on what it joins is refused, and that refusal is what stops a loop.

    **The loop it stops is real and is one hop long.** A merge refused as a conflict sends the run
    to this repair; a rebase that changes nothing puts the pull request back in front of the same
    `mergeable: false`; the run asks the model again and receives the same answer, and walks until
    the runtime's recursion limit. Asserted here rather than in a whole run because the tool is
    where the fact lives.
    """
    the_clone, _ = _a_delivery_that_conflicts(tmp_path, None)

    with pytest.raises(TheBranchIsAlreadyOnWhatItWouldJoinError) as the_refusal:
        rebase_the_branch_a_run_pushed(_the_rebase_to_make(the_clone))

    assert THE_BRANCH_A_RUN_DELIVERS_ON in str(the_refusal.value), (
        "the refusal does not name the branch, so a reader cannot tell which delivery it is about"
    )


def test_a_rebase_git_cannot_finish_leaves_the_clone_as_it_found_it(tmp_path: Path) -> None:
    """Two changes to the same file stop here, and the checkout is left usable afterwards.

    **The clone is the whole of this run's state**, and a clone stopped mid-rebase carries a
    `.git/rebase-merge` that refuses the next `git` command the run makes. So the abort is part of
    the refusal rather than something a caller has to remember — and what is asserted is that the
    next `git` call works, not that an exit code was zero somewhere.
    """
    the_clone, _ = _a_delivery_that_conflicts(tmp_path, "README.md")

    with pytest.raises(TheRebaseFoundConflictsError) as the_refusal:
        rebase_the_branch_a_run_pushed(_the_rebase_to_make(the_clone))

    assert "README.md" in str(the_refusal.value), (
        "the refusal does not name the file git could not merge, and git is the only thing here "
        "that knows which one it was"
    )
    assert "rebase" not in _git(the_clone.path, "status"), (
        "the clone is still in the middle of a rebase after the refusal, so the next git command "
        "this run makes is refused by git for a reason nothing in the record explains"
    )


def test_no_command_this_tool_runs_carries_a_credential(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every address this tool uses is a remote's name, and no argument carries anything secret.

    **A guard rather than a convention, and this is the whole reason it is here.** Every argument
    is read, and one that is an address holding something secret fails the run. The failure is the
    argument's own text: a credential on a command line is printed by git into whatever the
    command's failure is captured in, and this system builds its error messages out of exactly that.
    """
    the_clone, _ = _a_delivery_that_conflicts(tmp_path, "NOTES.md")
    what_it_asked_git_to_do: list[ACommand] = []

    def watching(command: ACommand):
        what_it_asked_git_to_do.append(command)
        from aisdlc.tools.run_command import the_outcome_of

        return the_outcome_of(command)

    monkeypatch.setattr("aisdlc.tools.rebase_the_branch_a_run_pushed.the_outcome_of", watching)

    rebase_the_branch_a_run_pushed(_the_rebase_to_make(the_clone))

    assert what_it_asked_git_to_do, "git was never asked to do anything, so this proved nothing"
    for command in what_it_asked_git_to_do:
        for an_argument in command.arguments:
            _refuse_an_argument_that_carries_a_credential(command, an_argument)


def _refuse_an_argument_that_carries_a_credential(command: ACommand, an_argument: str) -> None:
    """Refuse one argument that names an address holding something a person must not read twice."""
    names_an_address = "://" in an_argument
    carries_a_secret = any(
        a_way in an_argument.lower() for a_way in ("token", "password", "@github.com:")
    )
    assert not (names_an_address and carries_a_secret), (
        f"{command.program} was run with {an_argument!r}, an address holding a credential. "
        "git prints its own arguments back in its error message, so this one ends up in a log "
        "and in the run's own record — and a remote's name is the address to use"
    )
