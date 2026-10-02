"""A rebase names the identity it commits under, because it writes a commit nobody named.

**Found by a GitHub runner, and this repository's own answer was already written down.**
`a_commit_recording_the_change` says it in its module docstring: *"Supplying the identity on the
command line is also what makes a run work on a machine with no git configuration, which is every
CI runner, and the failure there names a missing setting rather than a missing step."* That is
right about `git commit` and **wrong about the rest of this package**, because only that one call
carries the identity.

**`git rebase` makes commits.** A rebase replays this run's commit onto the branch it joins and
writes a new one for it, with a new author and a new committer, both taken from configuration. On a
machine that has none, the rebase does not conflict and does not succeed — it stops at `Committer
identity unknown`, and the tool then reports `TheRebaseFoundConflictsError` naming no file it could
not merge, **because there was no conflict to report**. Three tests of
`test_a_rebase_puts_a_runs_commit_on_the_branch_it_joins.py` passed on a developer machine and
failed on a runner for that reason, and the failure named a conflict.

**This is a tool defect and not a test defect, and that is the whole distinction.** The test that
found it is right: it asked for a rebase and was told a conflict had happened. A machine with no
git configuration is not a broken machine — it is every CI runner, and this package's README says
the suite needs no configuration, which is a promise about this package and not about the
developer's `~/.gitconfig`.

**The commands are read out of a run rather than out of the source, and that is the second version
of this file.** The first parsed the module with `ast` to find which arguments were passed, and
it had to grow a resolver for a spliced call, a spliced name and an f-string before it could see
the arguments at all — at which point it was reading the program's text and reconstructing what git
would have been handed, which is a second implementation of the answer and therefore a second thing
that can be wrong. **A `the_outcome_of` seam already receives the exact `ACommand`**, so the
arguments are read from what the tool built rather than from what the tool's source says it built,
and this file's own docstring records that the first version was the wrong instrument.
"""

from __future__ import annotations

import contextlib
from pathlib import Path

import aisdlc.tools.rebase_the_branch_a_run_pushed as the_tool
from aisdlc.agents.a_commit_recording_the_change import (
    AN_ADDRESS_A_COMMIT_CAN_BE_READ_FROM,
    THE_AGENT_THAT_COMMITTED,
)
from aisdlc.tools.run_command import ACommand, CommandOutcome


def _the_git_commands_a_rebase_builds(monkeypatch) -> list[ACommand]:
    """Every `git` command this tool builds, captured at the one place all of them pass through.

    **Seamed rather than parsed, and the seam is production code rather than a test helper.**
    `the_outcome_of` is the single function in this package every shell-out hands its `ACommand`
    to — `run_command`'s own docstring says so, and `announced_by` decorates it for exactly that
    reason. Replacing it here therefore intercepts every git call the tool makes, and a git call
    the tool makes is the thing being asked about.

    **Every command reports success but one, and that one is chosen.** A rebase refuses to run at
    all when `merge-base --is-ancestor` says the branch already carries what it joins — which is
    the tool refusing a repair that would change nothing, which is a feature and not a failure of
    this harness. So that one command answers "not already there" and everything else succeeds,
    which is a real rebase on a real clone and takes the tool through every command it builds.
    """
    the_commands: list[ACommand] = []

    def recording_the_command(command: ACommand) -> CommandOutcome:
        the_commands.append(command)
        the_branch_already_carries_what_it_joins = "--is-ancestor" in command.arguments
        return CommandOutcome(
            exit_code=1 if the_branch_already_carries_what_it_joins else 0,
            standard_output="",
            standard_error="",
        )

    monkeypatch.setattr(the_tool, "the_outcome_of", recording_the_command)

    the_clone = _a_clone_the_tool_accepts()
    with contextlib.suppress(Exception):
        the_tool.rebase_the_branch_a_run_pushed(
            the_tool.a_rebase_of_the_branch_a_run_pushed(the_clone, "aisdlc/a-branch", "main")
        )

    return the_commands


def _a_clone_the_tool_accepts():
    from aisdlc.tools.github_clone_repository import ClonedRepository

    return ClonedRepository(path=Path("/nowhere/a-clone"), ref="main", commit="0" * 40)


def test_the_rebase_names_the_committer_it_replays_this_runs_commit_under(monkeypatch) -> None:
    """The identity goes on the command, and not read from configuration nobody told us about.

    **`-c user.name` and `-c user.email` before the subcommand, and that position is load-bearing.**
    git reads `-c` as configuration for the invocation that follows it, so `git -c user.name=x
    rebase FETCH_HEAD` sets it for the rebase while `git rebase -c user.name=x FETCH_HEAD` hands
    `-c` to `rebase`, which takes no such option and says so. The order in the argument list is
    therefore part of the rule and not a formatting choice.

    **The same two values `a_commit_recording_the_change` writes, and that is the point.** A
    replayed commit is a commit, and a commit naming a person for work a machine did is a forged
    trail that looks exactly like the real thing at the moment somebody has to tell them apart.
    """
    the_rebase = _the_git_command_that_runs(
        _the_git_commands_a_rebase_builds(monkeypatch), "rebase"
    )

    assert f"user.name={THE_AGENT_THAT_COMMITTED}" in the_rebase.arguments, (
        f"the rebase is run as `git {' '.join(the_rebase.arguments)}` with no committer named, so "
        "the commit it replays this run's change into is written under whatever the machine's git "
        "configuration carries. On a machine with none — which is every CI runner — git stops "
        "with `Committer identity unknown` and the tool then reports a conflict that never "
        "happened, naming no file because there was no conflict. Three tests failed on a GitHub "
        "runner for exactly this and passed on a developer machine"
    )
    assert f"user.email={AN_ADDRESS_A_COMMIT_CAN_BE_READ_FROM}" in the_rebase.arguments, (
        "the rebase names a committer but no address, so the commit it writes is one nothing can "
        "be replied to"
    )


def test_the_identity_comes_before_the_subcommand_git_is_being_told_to_run(monkeypatch) -> None:
    """`-c` reads configuration for what follows it, so its position in the arguments is the rule.

    **`git -c user.name=x rebase` works; `git rebase -c user.name=x` does not.** The second form
    hands `-c` to `rebase`, which takes no such option — a failure naming a missing option rather
    than a wrongly ordered argument list, which is the harder of the two to read.
    """
    the_rebase = _the_git_command_that_runs(
        _the_git_commands_a_rebase_builds(monkeypatch), "rebase"
    )

    where_the_identity_starts = next(
        (
            a_position
            for a_position, an_argument in enumerate(the_rebase.arguments)
            if an_argument.startswith("user.")
        ),
        None,
    )
    where_the_subcommand_is = the_rebase.arguments.index("rebase")

    the_identity_is_named = where_the_identity_starts is not None
    the_identity_comes_first = the_identity_is_named and (
        where_the_identity_starts < where_the_subcommand_is
    )
    assert the_identity_comes_first, (
        f"the identity is at position {where_the_identity_starts} and `rebase` is at "
        f"{where_the_subcommand_is}. git reads `-c` as configuration for the invocation that "
        "follows, so an identity after the subcommand is an argument handed to `rebase` rather "
        "than a setting"
    )


def test_the_rebase_and_its_unwind_both_name_the_committer(monkeypatch) -> None:
    """Both calls, and the second one is unwatched today — which is what this says out loud.

    **`git rebase --abort` runs through the same machinery and writes nothing, so it does not need
    the identity.** A rebase that conflicts is unwound rather than left half-finished, because a
    checkout stopped mid-rebase refuses the next `git` this run makes and the clone is the whole of
    a run's state. The command is not captured by the seam above — the tool stops at the conflicting
    rebase before it builds one — so naming it is this file's own argument rather than something
    read out of a run.

    **Asserted rather than assumed, and the assertion is about the source.** This is the one place
    a text reading is right: the question is whether a call exists that no run has reached, and a
    run that has not happened cannot answer it. The gap is named rather than left for a reader to
    assume the two are covered together.
    """
    the_source = Path(the_tool.__file__).read_text()

    assert '"--abort"' in the_source, (
        "this file reads the source to check the unwind, because the seam above cannot reach it: "
        "the tool stops at a conflicting rebase before it builds one. If the abort were removed "
        "this assertion would fire — which is the only part of the argument that is checked rather "
        "than argued"
    )


def _the_git_command_that_runs(the_commands: list[ACommand], subcommand: str) -> ACommand:
    """The one command that runs `subcommand`, or a refusal saying there was none.

    **Named and not taken first**, because a command list where the first entry is not the one
    asked about means the tool's order changed, and silently reading the wrong command is the way a
    guard stops guarding.
    """
    for a_command in the_commands:
        if subcommand in a_command.arguments:
            return a_command
    raise AssertionError(
        f"no `git {subcommand}` was run. The tool was asked for a rebase and its commands were "
        f"{[a_command.arguments for a_command in the_commands]}, so either the repair no longer "
        "rebases or it stopped earlier than this file assumes"
    )
