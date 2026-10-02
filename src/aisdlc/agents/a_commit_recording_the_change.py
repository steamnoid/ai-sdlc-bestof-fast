"""The commit a change is recorded in, and the identity it is recorded under.

**A delivery pushes a commit, so a change that is only a working tree does not exist to the
person receiving it.** This module exists because a real run proved that: the implementation
wrote its files, the suite passed on both sides, the verification report was honest, and the
branch this system pushed pointed at the same commit as `main`, because nothing had committed
anything. GitHub's answer was `No commits between main and aisdlc/…`, which is the only reason
anybody ever found out.

**Only the paths the plan named are staged.** A sweep — `git add -A` — would put build output,
an editor's scratch file and whatever else happened to be in the tree into somebody's pull
request. This repository's own commit discipline says in one line why: stage the files the
cycle is about, not everything. A delivery is not the place to discover what else was lying
around.

**The author is the agent that made the change, and it does not read the host's identity.** A
commit naming a person for work a machine did is a forged trail, and it looks exactly like the
real thing at the moment somebody has to tell them apart — the same reason an approval keeps
`decided_by` verbatim. Supplying the identity on the command line is also what makes a run work
on a machine with no git configuration, which is every CI runner, and the failure there names a
missing setting rather than a missing step.
"""

from __future__ import annotations

from pathlib import Path

from aisdlc.agents.implement_the_plan import _the_file_a_test_is_written_into
from aisdlc.agents.implementation_plan import ImplementationPlan
from aisdlc.tools.run_command import ACommand, CommandOutcome, the_outcome_of

THE_AGENT_THAT_COMMITTED = "aisdlc-dev-impl"
AN_ADDRESS_A_COMMIT_CAN_BE_READ_FROM = "aisdlc@localhost"


class TheChangeWasNotCommittedError(Exception):
    """The rule is in `a_commit_recording_the_change`, and only it may say the rule broke.

    Raised rather than returned, because every caller of this has the same next step: a
    delivery that pushes a commit it does not have is a delivery of nothing, and that has to
    stop the run at the stage where the truth is still cheap to fix.
    """


def the_paths_a_commit_must_stage(plan: ImplementationPlan) -> list[str]:
    """Every path a commit for this plan has to stage, with any test name reduced to its file.

    **A real run verified a change and then could not commit it.** `git add` was handed a pytest
    node ID — `tests/x.py::test_y` names a test exactly, and is what the verifier needs — and git
    wants the file, so it refused *after* the container suite had already run on both sides:

        fatal: pathspec 'tests/x.py::test_y' did not match any files

    **The node part comes off on the same rule the applied-change guard uses**, because it is the
    same mistake in a second place: a field meant to hold a path holding a name for something
    inside a path.

    **And all three of a plan's lists are staged, where two were.** `files_to_add` was dropped
    entirely, so a plan introducing a file this repository does not have yet — which is exactly
    what a new test file is — would never be staged, and the verification would have passed over a
    change the branch does not carry. A commit that records everything is the whole point of it.
    """
    return [
        _the_file_a_test_is_written_into(path)
        for path in [*plan.files_to_change, *plan.files_to_add, *plan.tests_to_add]
    ]


def a_commit_recording_the_change(
    clone_path: Path, plan: ImplementationPlan, what_the_change_is: str
) -> CommandOutcome:
    """Commit the files the plan named, on a branch off the commit the clone stands on.

    The message is the plan's subject, because a commit with an empty message is a commit
    nobody can find in a list of four hundred, and the branch is the work item's own because
    the branch is the name the run delivers from.
    """
    paths = the_paths_a_commit_must_stage(plan)

    for stage in (
        ACommand(
            program="git",
            arguments=["add", "--", *paths],
            working_directory=str(clone_path),
        ),
        ACommand(
            program="git",
            arguments=[
                "-c",
                f"user.name={THE_AGENT_THAT_COMMITTED}",
                "-c",
                f"user.email={AN_ADDRESS_A_COMMIT_CAN_BE_READ_FROM}",
                "commit",
                "-m",
                what_the_change_is,
            ],
            working_directory=str(clone_path),
        ),
    ):
        outcome = the_outcome_of(stage)

        if outcome.exit_code != 0:
            raise TheChangeWasNotCommittedError(
                f"git {stage.arguments[0]} refused, so the change this run verified is not "
                f"recorded anywhere and a delivery would push a branch carrying nothing. git "
                f"said: {outcome.standard_error.strip() or outcome.standard_output.strip()}"
            )

    return the_outcome_of(
        ACommand(
            program="git",
            arguments=["rev-parse", "HEAD"],
            working_directory=str(clone_path),
        )
    )
