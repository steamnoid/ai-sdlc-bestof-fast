"""The two gestures a card offers, and why neither of them is a new operation.

**A gesture is a named edge of the transition table, and that is the whole argument for having
two.** The glossary allows exactly two verbs on state — `transition` and `validate_state` — and says
a third is not introduced lightly, because a change that seems to need one usually needs a state
transition instead. A board needs two things a person can do to a card, and both are already in the
table: `AWAITING_AGENT_PICKUP -> IN_PROGRESS_BY_AGENT` and back.

**So each gesture refuses exactly where the table refuses the move.** That is what holds the
design, and it is what would fail if a gesture had quietly grown a code path of its own. A work
item at `AWAITING_HUMAN_APPROVAL` can only be moved by a person answering the gate; a gesture that
could pick it up would be a way past an approval, which is the failure this repository removed a
field over once.

**The agent stays set when work is put back.** The biconditional makes `AWAITING_AGENT_PICKUP` a
stage an agent holds, so releasing hands the work back to the queue without un-assigning it.

**Neither gesture touches the register, the card, or the assignee.** A gesture is a move of the
work item and nothing else, so a person picking a card up cannot thereby change who is accountable
for it — two facts about two different things.

**A turn at the work item is counted by the edge, not by this function.** Picking a card up is
the move `-> IN_PROGRESS_BY_AGENT`, and `transition()` counts it because that is the only
edge which means an agent has begun. Counting it here instead would count nothing in a real
run: the graph asks for the stage and the transition node applies it, so it never comes
through this gesture, and a run that put an agent back on a work item would present a second
version of an artifact as the first. Putting a card back counts nothing — the agent holding
it is the same one, and a hand-back is not a turn.

**Neither gesture reaches `DONE`.** No edge out of it exists and none is named, which is the
`AGENTS.md` debt about `DONE` being unreachable seen from the other side: this module cannot
invent the missing transition, and a test that says so is cheaper than a module that guesses.
"""

from __future__ import annotations

from aisdlc.domain.role import Role
from aisdlc.domain.stage import Stage
from aisdlc.domain.state_machine import transition
from aisdlc.domain.work_item import WorkItem

# The two edges, named once. **Read rather than written inline in each function**, because a
# gesture that spelled its own stage out would be a second statement of the table and the two
# would eventually disagree.
PICKED_UP_MOVES_TO = Stage.IN_PROGRESS_BY_AGENT
PUT_BACK_MOVES_TO = Stage.AWAITING_AGENT_PICKUP


def a_work_item_is_picked_up(
    work_item: WorkItem, by: str, accountable_role: Role
) -> WorkItem:
    """Hand this work item to the agent that picked the card up, and hand back the moved item.

    **`by` is required and not optional, because a work item in progress that nobody is doing is
    a state the table refuses.** Picking a card up is a claim about who is now accountable for the
    next thing this run does, and a gesture that could not say who would be a claim about nobody.

    **Refused wherever the table refuses it**, and the refusal is the design: a work item waiting
    on a person cannot be picked up by an agent, because a person is the only thing that can move
    it on.
    """
    return transition(
        work_item, PICKED_UP_MOVES_TO, agent=by, accountable_role=accountable_role
    )


def a_work_item_is_put_back(work_item: WorkItem, accountable_role: Role) -> WorkItem:
    """Stop being worked on, and hand the work back to the queue.

    **The same agent is still holding it**, because the biconditional makes
    `AWAITING_AGENT_PICKUP` a stage an agent holds. Putting work back is not un-assigning it — a
    transition passing `None` here is refused, which is the invariant working rather than this
    function being difficult to use.

    **Only a work item in progress can be put back.** A card nobody has picked up has nothing to
    put back, and a gesture that invented the move would be a new edge in a table this repository
    says is exhaustive.
    """
    return transition(
        work_item, PUT_BACK_MOVES_TO, agent=work_item.agent, accountable_role=accountable_role
    )
