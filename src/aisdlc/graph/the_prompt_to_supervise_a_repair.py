"""The question the repair supervisor is asked, built from the card and the count.

**The material is the whole card, and the card is on disk because a resumed run finds it there.**
The count says how many turns each agent has already had, the comments are what every agent
concluded and what it could not settle, the refusal says what stopped the run, and the list of
agents that left no note says whose judgement is missing rather than quiet. A supervisor handed
anything less is guessing.

**The question is a closed one and the model is bound to it.** A verdict per agent, a starting
point from a set of two, and a sentence naming what has not moved. That last one is the whole
reason a supervisor can be trusted to stop: a model asked whether another attempt is worth it
has very little reason to say no, and this system has an analyst that refused plannable work for
six consecutive runs with a reasonable sentence every time.

**The verdict is asked for every agent, including the ones that plainly did nothing.** The
product analyst is upstream of a failure three stages later and will almost always be told to
stand down — and the point is that the run records that it was told, rather than the supervisor
having simply not been asked.
"""

from __future__ import annotations

from aisdlc.domain.work_item import WorkItem
from aisdlc.graph.the_agents_that_leave_a_note import (
    THE_AGENTS_THAT_LEAVE_A_NOTE,
    THE_AGENTS_THAT_LEAVE_NO_NOTE,
)
from aisdlc.graph.what_to_repeat import WhereTheRunShouldStartAgain
from aisdlc.tools.what_people_said_about_a_work_item import AComment

THE_AGENT_THAT_SUPERVISES_A_REPAIR = "aisdlc-repair-supervise"


def the_work_done_so_far(work_item: WorkItem) -> str:
    """One line per agent: how many turns it has already had on this work item.

    **The count is read rather than asked for**, because the count is a fact about the run and
    a model asked to infer it from the comments would be guessing. Zero is stated rather than
    omitted: an agent absent from the count has not worked, and a reader has to be able to tell
    that from one nobody looked up.
    """
    return "\n".join(
        f"{agent}: {work_item.work_done.how_many_times_this_agent_has_worked(agent)}"
        for agent in sorted(
            set(THE_AGENTS_THAT_LEAVE_A_NOTE) | set(THE_AGENTS_THAT_LEAVE_NO_NOTE)
        )
    )


def the_notes_left_so_far(comments: list[AComment]) -> str:
    """What every agent that left a note said, oldest first, with its author named.

    **Sorted by when rather than by the order the file system gives**, for the reason
    `a_comment_was_left` sorts: a note left while a run was going is older than one left after
    it, and the only order a reader would find wrong is the accidental one.
    """
    if not comments:
        return "No agent has left a note on this work item."

    return "\n\n".join(
        f"{comment.said_at.isoformat()} — {comment.said_by}:\n{comment.what_was_said}"
        for comment in sorted(comments, key=lambda comment: comment.said_at)
    )


def the_prompt_to_supervise_a_repair(
    work_item: WorkItem,
    comments: list[AComment],
    what_stopped_the_run: str,
) -> str:
    """The question put to the model about one repair of one work item.

    **Nothing here is a summary written by this function.** The count is read, the notes are
    quoted, and the refusal is quoted — because a supervisor's judgement is only worth as much
    as the evidence it was given, and a paraphrase is not the evidence.
    """
    the_agents_who_left_no_note = ", ".join(sorted(THE_AGENTS_THAT_LEAVE_NO_NOTE))
    the_places_to_start_again = "\n".join(
        f"- {place.value}" for place in WhereTheRunShouldStartAgain
    )

    return (
        f"A run of this system has stopped on {work_item.repository.owner}/"
        f"{work_item.repository.name}, work item {work_item.work_item_id}.\n"
        f"Here is what stopped it:\n{what_stopped_the_run}\n"
        "\n"
        f"Turns each agent has already had on this work item:\n{the_work_done_so_far(work_item)}\n"
        "\n"
        f"What every agent that left a note said, oldest first:\n"
        f"{the_notes_left_so_far(comments)}\n"
        "\n"
        f"Agents that leave no note, so their absence is not a silence you may read as "
        f"reassurance: {the_agents_who_left_no_note}\n"
        "\n"
        "Decide which agents must repeat their work, and which stand down.\n"
        "\n"
        f"Answer with three things:\n"
        f"- `what_each_agent_must_do`: one entry per agent, every agent, with the agent, "
        f"whether it must repeat its work, and why. An agent you say nothing about will be "
        f"refused.\n"
        f"- `where_to_start_again`: exactly one of these, and nothing else:\n"
        f"{the_places_to_start_again}\n"
        f"- `what_has_not_changed`: one sentence naming the thing that has not moved between the "
        f"attempts so far. A sentence, not a verdict: *this is not working* cannot be checked, and "
        f"a run that stops on something nobody can check has stopped for a reason nobody can argue "
        f"with afterwards. If every agent should stand down, this is still the sentence that says "
        f"why they should.\n"
        "\n"
        "If another attempt cannot change anything, say so by standing every agent down and "
        "naming what has not changed. Do not repeat an agent's work to look busy: a second attempt "
        "costs a repository's own test suite in a container, and three attempts at a plan that "
        "names no product file is a circle, not a repair.\n"
    )
