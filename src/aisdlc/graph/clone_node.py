"""The run's own clone, made once and left alone on resume.

The resume rule is the content of this file. A LangGraph run resumes from a checkpoint and
resuming runs this node again, and the clone it finds is its own from earlier in the same
run — so the state is asked first and git is only reached when the answer is that there is
nothing.

Re-making it would work underneath that clone, and the refusal about a non-empty
destination would then blame somebody else's work for work this run did ten minutes ago.
That message would be a lie about the situation and about the person it names.

One collaborator, and it answers the only question this node cannot answer for itself:
which repository this run may write to. Everything address-shaped is that
collaborator's business, so this node asks one thing and the test can answer it with a
local path.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from aisdlc.domain.repository import Repository
from aisdlc.graph.agent_state import AgentState
from aisdlc.tools.github_clone_repository import (
    RepositoryToClone,
    clone_repository,
)
from aisdlc.tools.the_project_directory import the_clone_directory_of


class TheRepositoryHasNotBeenClonedYetError(Exception):
    """The rule is the order of the graph, and this is what says the order was broken.

    The clone channel is optional because a run has not cloned at the start, and a type cannot
    say "and by the time this node runs it is not optional". So the ordering is stated as a
    refusal: a graph wired with a reading node before the clone fails here saying what is
    wrong, rather than passing a `None` along until something reads an attribute off it.

    **It lives here, beside the node that provides the clone, and both reading nodes import
    it.** It was written twice — once in each of them — and two classes with one name in two
    modules is two rules that will drift into disagreeing about the same ordering.
    """

PlanTheClone = Callable[[Repository, Path], RepositoryToClone]


def clone_the_repository_for_this_run(
    state: AgentState, plan_the_clone: PlanTheClone
) -> dict:
    """The clone this run works on, made now or taken from the state it already has.

    The destination is settled before anything is fetched. A missing root has to be
    refused before a download begins, or the refusal arrives after the cost and leaves an
    operator with a half-finished clone and a message about a setting.
    """
    if state["clone"] is not None:
        return {"clone": state["clone"]}

    where = the_clone_directory_of(state["work_item"], state["projects_root"])

    return {"clone": clone_repository(plan_the_clone(state["work_item"].repository, where))}
