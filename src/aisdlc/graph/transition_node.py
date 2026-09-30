"""The one node allowed to write a work item, because it goes through transition."""

from __future__ import annotations

from pathlib import Path

from aisdlc.domain.state_machine import transition
from aisdlc.domain.work_item import WorkItem
from aisdlc.graph.agent_state import AgentState
from aisdlc.persistence.the_register_of_work_items import the_work_item_is_recorded_at
from aisdlc.store.what_a_run_records import the_move_was_recorded


def transition_the_work_item(state: AgentState) -> dict:
    """Move the work item on, and hand the moved work item to the next node.

    The only node permitted to write the work item channel, and that is the whole
    reason it is separate. Nothing else in the graph assigns to a work item, so an
    illegal move has nowhere to happen: the transition table and the biconditional are
    checked here, once, for every move the graph ever makes.

    The move itself is named in the state rather than in the signature, because a
    LangGraph node is handed the state and nothing else. Who decided the move is the
    router's business; making it happen is this node's, and it cannot be anything but
    a legal move.

    The role travels with the request for the same reason the agent does. A work item
    carries the discipline accountable for the result from the moment it is commissioned,
    so the role changes exactly when the work item does: here, or nowhere.

    Only the work item is returned. A node that returned the whole state would be a
    writer of every channel, which is the thing the single-writer rule exists to
    prevent.
    """
    where_it_was = state["work_item"]
    moved = transition(
        where_it_was,
        state["requested_stage"],
        state["requested_agent"],
        state["requested_role"],
    )
    _record_where_the_work_got_to(where_it_was, moved, state["projects_root"])
    return {"work_item": the_move_was_recorded(where_it_was, moved)}


def _record_where_the_work_got_to(
    where_it_was: WorkItem, moved: WorkItem, projects_root: Path
) -> None:
    """Put the moved work item in the engine's own register, so a run that resumes finds it.

    **Here and not in a node of its own, because this is the only node allowed to write a work
    item and a second writer would be a second place a stage could be set.** A run interrupted
    after four gates left a register that still said `READY` — a record of four gates on disk and
    a work item claiming nobody had started, which is worse than having no register at all.

    **No way to move a work item and record nothing.** This had a branch that returned early when
    the root was absent, and a test that named the gap it made: a run configured without a
    projects root moved work items and registered none of them, which is a run that cannot be
    resumed and says so quietly. `projects_root` is now a non-optional channel, so the branch was
    dead rather than conditional, and it is gone rather than left as a thing nobody reads.

    A root that was never configured is still refused at `the_project_directory_of`, and that is
    the right place for it: one refusal every caller meets, rather than a check in each.

    **Two registers and one move.** The JSON file here is what a resuming run reads; the SQLite
    row written by the caller is what a board reads. Both are written from this one value at this
    one moment, so the board and the run are describing the same move — and there is no third
    place a stage could be set.
    """
    the_work_item_is_recorded_at(moved, projects_root)
