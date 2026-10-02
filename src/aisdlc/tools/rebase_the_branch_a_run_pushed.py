"""`git.rebase_the_branch_a_run_pushed`: the one repair a conflicting delivery can take.

**A pull request GitHub will not merge is a branch that has fallen behind the branch it joins, and
replaying it on top of that branch is the whole of the fix.** `merge_a_pull_request` reads
`mergeable: false` and refuses without asking, because GitHub words a conflict and a protected base
branch alike — so something has to act on the conflict once it has been established. This is that
something, and it is the action behind `REBASE_IT_AND_TRY_AGAIN`, which was a name in a closed set
with no operation under it until now.

**Three `git` calls and a decision between them, and the order is the argument.** The branch it
joins is read from where the code came from, the rebase is carried out against what was read, and
the result is put on the remote with the expectation it was fetched under. Fetching before rebasing
is not a detail: a rebase onto a branch this system has not just read is a rebase onto whatever the
remote held at some earlier moment.

**Every address here is a remote's name, and that is the rule the whole file turns on.** `origin`
is the copy this run may write to and the branch it delivered is on it; `upstream` is where the
branch it joins lives. The obvious way to fetch is to compose a URL, and a URL that needs a
credential is a URL that git prints back inside its own error message — which is where this
repository's error messages come from. `the_clone_url_of` refuses to read the environment at all
for the same reason, and this file takes its remotes by name for the same reason.

**The branch may be moved only where this run left it, and git is what checks it.**
`create_a_branch_on_a_remote` refuses to push a branch that is already on the remote, because a run
must never move a branch somebody else is using; a rebase has to do precisely that, so that
refusal cannot be relaxed — it has to be stated precisely instead. The commit the branch is expected
to be at is handed to git as a **lease**, which git compares against the branch inside the same
push that would move it. A read of the branch beforehand would leave a window between the read and
the push, and what that window admits is a commit somebody else pushed in between, destroyed.

**A rebase that would change nothing is refused, and that refusal is what stops a run going round.**
A merge refused as a conflict sends the run to this repair; a rebase that changes nothing leaves the
pull request in front of the same `mergeable: false`; the run reaches the same repair again with
the same facts and walks until the runtime's recursion limit. **A decision taken once about a fact
that has not changed is not a decision**, and this is where that is said — in the tool that knows
the fact, rather than left to a node to notice on a second visit.

**A rebase git cannot finish leaves the clone as it found it.** A checkout stopped mid-rebase
carries a `.git/rebase-merge` that refuses the next `git` command this run makes, and the clone is
the whole of a run's state. So the abort belongs to the refusal rather than to a caller's memory
of it, and the refusal quotes git because git is the only thing here that can say which file it
could not merge.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from aisdlc.tools.github_clone_repository import ClonedRepository
from aisdlc.tools.github_create_branch import THE_REMOTE
from aisdlc.tools.run_command import ACommand, the_outcome_of

THE_AGENT_THAT_COMMITTED = "aisdlc-dev-impl"
"""Who a commit this tool replays is written by, and it is the implementer.

**The agent that made the change, not whoever's git is installed and not this tool.** A rebase
writes a *new* commit, and a commit naming a person for work a machine did is a forged trail that
looks exactly like the real thing at the moment somebody has to tell them apart — the same reason
an approval keeps `decided_by` verbatim. `a_commit_recording_the_change` names the same two values
for the same reason, and this is the second caller of that pair.
"""

AN_ADDRESS_A_COMMIT_CAN_BE_READ_FROM = "aisdlc@localhost"
"""Where a commit this tool writes can be replied to, and it is not a real mailbox.

**`localhost` rather than a plausible domain, because a plausible domain is what a reader mistakes
for an author.** The address has to exist for git and has to be obviously not a person for whoever
reads the commit later, and `aisdlc@localhost` says both in the two seconds it takes to read.
"""


def _the_identity_a_replayed_commit_is_written_under() -> list[str]:
    """The `-c` arguments that name the committer, and their position is part of what they are.

    **Before the subcommand, and that is load-bearing.** git reads `-c` as configuration for the
    invocation that follows it, so `git -c user.name=x rebase …` sets it for the rebase while
    `git rebase -c user.name=x …` hands `-c` to `rebase`, which takes no such option and says so.
    A function rather than a constant because a constant cannot be *placed* — the arguments have to
    come before the subcommand and a reader has to see that they do.
    """
    return [
        "-c",
        f"user.name={THE_AGENT_THAT_COMMITTED}",
        "-c",
        f"user.email={AN_ADDRESS_A_COMMIT_CAN_BE_READ_FROM}",
    ]

THE_REMOTE_THE_CODE_CAME_FROM = "upstream"
"""Where the branch a pull request joins is read from, and it is named rather than composed.

**The code's own remote, and not the copy this run may write to.** A fork falls behind the moment
it is made, so rebasing onto the fork's copy of that branch is rebasing onto the commit this
delivery was built from — which is the state the run is already in, and the conflict would survive
it.
"""

WHAT_GIT_WAS_ASKED_TO_FETCH = "FETCH_HEAD"
"""The commit the fetch just read, named because git already gave it one and this file reads it.

**`FETCH_HEAD` rather than a remote-tracking ref**, because the ref's name depends on what the
remote's fetch refspec happens to be configured as, and the one fact a rebase needs is the commit
that was just read. A run on a deployment whose refspec was narrowed would otherwise be rebasing
onto something other than what it fetched.
"""


class TheBranchItJoinsCouldNotBeReadError(Exception):
    """The branch this delivery would join could not be read, so there is nothing to rebase onto.

    **Separate from the rebase failing, because they are different facts about different moments.**
    This is about the repository this run has been working in all along; a person told "the rebase
    failed" would go and look at the rebase, and the rebase is not where the trouble is.
    """


class TheBranchIsAlreadyOnWhatItWouldJoinError(Exception):
    """The branch already carries the branch it would join, so there is nothing to replay.

    **A refusal and not a no-op that reports success, and the difference is the whole point.** A
    rebase that changes nothing leaves the pull request in front of the same conflict, so a run that
    reported one has been told a repair happened and nothing has. It is also the bound on how often
    this repair may be reached: the second visit finds the branch already on what it would join and
    stops, rather than asking a model to decide again about facts that have not changed.
    """


class TheRebaseFoundConflictsError(Exception):
    """git could not replay this run's commit onto the branch it joins.

    **git's own words, because git is the only thing here that knows which file.** This system
    cannot merge two changes to one file on somebody else's behalf, and the files git names are the
    ones a person has to look at. The clone is put back the way it was found, so the run's own
    repository is left usable by whatever reads it next.
    """


class TheBranchOnTheRemoteWasNotMovedError(Exception):
    """The rebased commit did not go onto the branch, so the pull request is where it was.

    **Quoted rather than classified, and the lease is why that is honest.** A lease that git
    refuses is usually somebody else having pushed to that branch since this run left its commit
    there — but it is also what a network gives up looks like, and this system will not read a
    remote's prose and announce a cause it has not established. The condition git was given is
    named, so the sentence carries the check without claiming its verdict.
    """


class ARebaseOfTheBranchARunPushed(BaseModel):
    """The branch this run delivered, the checkout holding it, and the branch it would join.

    **The commit is not an argument, and this is deliberate.** The commit the lease names is the
    one in the clone — the delivery pushed `HEAD` and nothing else has touched the checkout since —
    and a caller stating it would be a second place for that fact to be wrong. `BranchToPush`
    carries a commit as well, and it is written from the clone at clone time, which is *before* the
    run commits anything: so the value there is not the commit the branch was pushed at, and this
    file reads the real one rather than taking it on trust.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    clone: ClonedRepository
    the_branch_this_run_pushed: str
    the_branch_it_would_join: str

    @field_validator("the_branch_this_run_pushed", "the_branch_it_would_join")
    @classmethod
    def _refuse_a_branch_that_is_nobody(cls, name: str) -> str:
        """Refuse a blank before git is asked, because a blank names no branch at all."""
        if not name.strip():
            raise ValueError(
                "a rebase names the branch this run delivered and the branch it would join, and a "
                "blank names neither. Git's own answer about an empty refspec says nothing about "
                "which of the two was meant"
            )
        return name


class WhatTheRebaseLeft(BaseModel):
    """Which commit the branch was at and which it is at now, so a reader can see whether it moved.

    **Two commits and no verdict.** "Rebased" is a claim this system makes about somebody else's
    repository, and the two shas are the fact a person checks it against — the one before is what
    the pull request was pointing at, the one after is what it points at now.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    the_commit_it_was: str
    the_commit_it_is_now: str


def a_rebase_of_the_branch_a_run_pushed(
    clone: ClonedRepository, the_branch_this_run_pushed: str, the_branch_it_would_join: str
) -> ARebaseOfTheBranchARunPushed:
    """The rebase this delivery needs, named by the three things it is about."""
    return ARebaseOfTheBranchARunPushed(
        clone=clone,
        the_branch_this_run_pushed=the_branch_this_run_pushed,
        the_branch_it_would_join=the_branch_it_would_join,
    )


def rebase_the_branch_a_run_pushed(
    wanted: ARebaseOfTheBranchARunPushed,
) -> WhatTheRebaseLeft:
    """Replay this run's commit on the branch it would join, and put that on the remote.

    **The order is the whole contract: read, refuse if there is nothing to do, replay, move the
    branch.** Reading first is what makes the "nothing to do" refusal possible; refusing before
    replaying is what stops a run reaching this repair twice for one unchanged fact; and moving the
    branch is last because it is the only step anything else can see, and it must not happen for a
    rebase that was refused or could not be finished.
    """
    the_commit_it_was = _the_commit_the_clone_stands_on(wanted.clone)

    _the_branch_it_joins_is_read(wanted)
    _refuse_a_branch_that_is_already_on_what_it_joins(wanted)
    _the_commit_is_replayed(wanted)

    _the_rebased_commit_is_put_on_the_branch(wanted, the_commit_it_was)

    return WhatTheRebaseLeft(
        the_commit_it_was=the_commit_it_was,
        the_commit_it_is_now=_the_commit_the_clone_stands_on(wanted.clone),
    )


def _the_commit_the_clone_stands_on(clone: ClonedRepository) -> str:
    """Read out of the clone rather than remembered, because the rebase is about to change it."""
    return the_outcome_of(
        ACommand(
            program="git",
            arguments=["rev-parse", "HEAD"],
            working_directory=str(clone.path),
        )
    ).standard_output.strip()


def _the_branch_it_joins_is_read(wanted: ARebaseOfTheBranchARunPushed) -> None:
    """Fetch the branch it joins from the code's own remote, or quote git's refusal.

    **A named remote rather than a composed address**, which is the rule the whole file rests on:
    an address that can be fetched may have to carry a credential, and git prints its own arguments
    in its error message — and this repository builds its error messages out of exactly that.
    """
    fetched = the_outcome_of(
        ACommand(
            program="git",
            arguments=[
                "fetch",
                THE_REMOTE_THE_CODE_CAME_FROM,
                wanted.the_branch_it_would_join,
            ],
            working_directory=str(wanted.clone.path),
        )
    )

    if fetched.exit_code == 0:
        return

    raise TheBranchItJoinsCouldNotBeReadError(
        f"{wanted.the_branch_it_would_join!r} on {THE_REMOTE_THE_CODE_CAME_FROM} could not be "
        f"read, so {wanted.the_branch_this_run_pushed!r} has nothing to be replayed onto. git "
        f"said: {fetched.standard_error.strip() or fetched.standard_output.strip()}"
    )


def _refuse_a_branch_that_is_already_on_what_it_joins(
    wanted: ARebaseOfTheBranchARunPushed,
) -> None:
    """Refuse a rebase that would change nothing, by asking git rather than comparing shas.

    **`merge-base --is-ancestor` answers the question rather than this file re-implementing it.** A
    base branch that is already in this branch's history is a rebase with nothing to replay, and
    reporting that as a repair is what would send a run round the same conflict twice — so it is
    refused, and the refusal names the branch a reader would go and look at.
    """
    already_there = the_outcome_of(
        ACommand(
            program="git",
            arguments=[
                "merge-base",
                "--is-ancestor",
                WHAT_GIT_WAS_ASKED_TO_FETCH,
                "HEAD",
            ],
            working_directory=str(wanted.clone.path),
        )
    )

    if already_there.exit_code != 0:
        return

    raise TheBranchIsAlreadyOnWhatItWouldJoinError(
        f"{wanted.the_branch_this_run_pushed!r} already carries "
        f"{wanted.the_branch_it_would_join!r} from {THE_REMOTE_THE_CODE_CAME_FROM}, so replaying "
        "it would move nothing and the pull request would be in front of the same conflict it is "
        "in now. A decision taken once about a fact that has not changed is not a decision, and "
        "this repair is not taken again for the same reason"
    )


def _the_commit_is_replayed(wanted: ARebaseOfTheBranchARunPushed) -> None:
    """Run the rebase, and refuse naming the files git could not merge.

    **The files are asked of git and not read out of its prose.** A rebase that conflicts says
    `could not apply` and then prints `git add/rm <conflicted_files>` without ever naming one —
    which backend git chose decides whether a path appears at all. `git diff --diff-filter=U` is
    the query that answers the question on every version, and it has to be asked *before* the
    abort, because a checkout that has been unwound has no conflicted files left in it.

    **The committer is named here, and this is a GitHub runner's finding rather than a tidy-up.** A
    rebase does not move a commit — it *writes a new one*, with a new author and a new committer,
    both taken from configuration. On a machine with none, git stops at `Committer identity
    unknown`, this call exits non-zero, and the refusal below then reports
    `TheRebaseFoundConflictsError` naming no file it could not merge — **because there was no
    conflict**. Three tests of `test_a_rebase_puts_a_runs_commit_on_the_branch_it_joins.py` passed
    on a developer machine and failed on a runner for that reason, and the failure named a conflict.

    `a_commit_recording_the_change` already answers this for `git commit` and says in its own
    docstring why: *"naming the identity on the command line is also what makes a run work on a
    machine with no git configuration, which is every CI runner"*. That claim was true of one call
    and false of this one, which is the same shape as every other defect this repository has found
    — **a fix that landed in one place and the reasoning was never written down anywhere else.**
    """
    rebased = the_outcome_of(
        ACommand(
            program="git",
            arguments=[
                *_the_identity_a_replayed_commit_is_written_under(),
                "rebase",
                WHAT_GIT_WAS_ASKED_TO_FETCH,
            ],
            working_directory=str(wanted.clone.path),
        )
    )

    if rebased.exit_code == 0:
        return

    raise TheRebaseFoundConflictsError(
        _what_stopped_the_rebase(wanted, rebased.standard_error.strip())
    )


def _what_stopped_the_rebase(wanted: ARebaseOfTheBranchARunPushed, what_git_said: str) -> str:
    """The refusal: which files, whether the checkout was put back, and git's own words.

    **"No file it could name" rather than a guess.** git refuses a rebase for reasons that are
    not conflicts — an unstaged change, a detached head — and a refusal that named a file in those
    cases would be naming a thing it never established. So the sentence says what git reported and
    quotes it either way.
    """
    the_files_git_could_not_merge = _the_files_git_could_not_merge(wanted)
    the_files = (
        f"git could not merge {', '.join(the_files_git_could_not_merge)}"
        if the_files_git_could_not_merge
        else "git named no file it could not merge"
    )
    return (
        f"the commit {wanted.the_branch_this_run_pushed!r} carries could not be replayed onto "
        f"{wanted.the_branch_it_would_join!r} — {the_files} — so the branch was not moved and the "
        f"pull request still points at the commit that conflicts. "
        f"{_the_checkout_was_unwound(wanted)}. git said: "
        f"{what_git_said or 'nothing'}"
    )


def _the_files_git_could_not_merge(wanted: ARebaseOfTheBranchARunPushed) -> list[str]:
    """The paths git reports as unmerged, which is a query rather than a reading of its output."""
    what_is_unmerged = the_outcome_of(
        ACommand(
            program="git",
            arguments=["diff", "--name-only", "--diff-filter=U"],
            working_directory=str(wanted.clone.path),
        )
    )
    return [a_path for a_path in what_is_unmerged.standard_output.splitlines() if a_path.strip()]


def _the_checkout_was_unwound(wanted: ARebaseOfTheBranchARunPushed) -> str:
    """Put the checkout back the way it was found, and say whether that worked.

    **The abort is here and not in the caller's hands**, because a checkout stopped mid-rebase
    refuses the next `git` command this run makes and the clone is the whole of a run's state. It
    is allowed to fail: git leaves nothing to unwind when the rebase was refused for a reason other
    than a conflict, so a caller reading "it was put back" would be told something false.
    """
    unwound = the_outcome_of(
        ACommand(
            program="git",
            arguments=["rebase", "--abort"],
            working_directory=str(wanted.clone.path),
        )
    )
    if unwound.exit_code == 0:
        return "The checkout was put back the way this run found it."
    return (
        "git also refused to unwind the checkout, so it may still be in the middle of a rebase: "
        f"{unwound.standard_error.strip()}"
    )


def _the_rebased_commit_is_put_on_the_branch(
    wanted: ARebaseOfTheBranchARunPushed, the_commit_the_branch_was_at: str
) -> None:
    """Move the branch, on the lease that this run's commit is where it left it.

    **`--force-with-lease` is stated with the commit and not with a bare flag.** A bare
    `--force-with-lease` trusts the remote-tracking refs in this checkout, which a fetch just
    changed and which say nothing about whether *this run* left the branch where it thinks; naming
    the commit compares the branch against the fact this tool read out of the clone. Git then
    refuses inside the push itself, so there is no window between deciding and moving.
    """
    moved = the_outcome_of(
        ACommand(
            program="git",
            arguments=[
                "push",
                f"--force-with-lease=refs/heads/{wanted.the_branch_this_run_pushed}"
                f":{the_commit_the_branch_was_at}",
                THE_REMOTE,
                f"HEAD:refs/heads/{wanted.the_branch_this_run_pushed}",
            ],
            working_directory=str(wanted.clone.path),
        )
    )

    if moved.exit_code == 0:
        return

    raise TheBranchOnTheRemoteWasNotMovedError(
        f"{wanted.the_branch_this_run_pushed!r} on {THE_REMOTE} is not the branch that holds "
        f"{the_commit_the_branch_was_at}, so git refused to put the rebased commit on it and the "
        f"pull request still points at {the_commit_the_branch_was_at}. The branch is not moved "
        "unless it is where this run left it — most often because somebody pushed to it since — "
        f"and git's own words are the whole of what can be said about it here: "
        f"{moved.standard_error.strip() or moved.standard_output.strip()}"
    )
