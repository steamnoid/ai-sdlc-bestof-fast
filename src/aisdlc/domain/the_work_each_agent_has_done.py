"""Who has worked on a work item, and how many times each of them has.

One structure holding both, because *which agents* and *how many times* are one
fact asked two ways: a count per agent answers both, and two collections would
be able to disagree.

**A tuple of frozen entries, and not a dict.** `WorkItem` is `frozen=True`, and
frozen is shallow -- it blocks `__setattr__` and says nothing about a mutable
object sitting inside the model. A dict field would be changed in place by a
caller holding the work item, so the work item would stop being frozen exactly
where it mattered. A tuple of frozen entries has no such door, and the entries
sort themselves so two counts of the same work item read the same way.

**The count is raised in the pickup and nowhere else**, and `transition()` carries
it with the work item. A count a caller could pass, omit or reset on the way is a
count nobody may rely on, and the second door that would let it be changed is the
one this package deleted a field over once.

**It is the version of what an agent produces.** The plan `aisdlc-dev-plan` wrote
on its second turn is a different artifact from the one a person approved on its
first, so the plan is presented at the number of times the planning agent has
worked on that work item -- which is what makes `Approval.applies_to` able to
tell the two apart. Attempts and presentations can differ, because an agent may
be stopped before it produces anything, and a number skipped is harmless: what
`applies_to` needs is that a version is never reused, not that none is missed.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

NO_AGENT_HAS_WORKED_ON_THIS = 0


class TheWorkOneAgentHasDone(BaseModel):
    """One agent, and how many times it has worked on one work item.

    **`how_many_times` is at least one**, so an entry cannot record that an agent
    worked no times. "Nobody has worked on this" is what an empty
    `TheWorkEachAgentHasDone` says, and a zero sitting in a list of counts would be
    a second, contradictory way of saying the same thing.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    agent: str
    how_many_times: int = Field(ge=1)

    @field_validator("agent")
    @classmethod
    def _refuse_a_count_of_nobody(cls, agent: str) -> str:
        """Refuse a blank agent, because an entry is about somebody.

        A real run sent the contents of a one-field object where the object was asked
        for — the security report's shape is a bare array, and the other four answers
        carry three to eight fields each, so a model asked for one of those sends the
        field's contents instead. A count of nobody is not work anybody did, and
        refusing it here is the same defence `WorkItem` makes on `commissioned_by`.
        """
        if not agent:
            raise ValueError(
                "an entry says which agent worked and how many times, and this one says "
                "neither; a count of nobody is not work"
            )
        return agent


class TheWorkEachAgentHasDone(BaseModel):
    """What every agent has done on one work item, counted.

    **Empty is not a default that hides anything**: a work item that was
    commissioned a moment ago really has had nobody work on it. That is a fact
    about a new work item rather than a value standing in for an answer nobody
    gave, which is the difference between a default and a fallback.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    worked: tuple[TheWorkOneAgentHasDone, ...] = ()

    @field_validator("worked")
    @classmethod
    def _refuse_one_agent_twice_in_two_places(
        cls, worked: tuple[TheWorkOneAgentHasDone, ...]
    ) -> tuple[TheWorkOneAgentHasDone, ...]:
        """One entry per agent, sorted, so a reader counts agents rather than entries.

        Two entries for one agent are not a count of two: they are two answers to one
        question, and which of them a reader would believe is not a thing this type
        can decide. Sorting is what makes two counts of the same work item read the
        same way round, so they can be compared without being put in order first.

        **A field validator rather than a model one**, because a model validator
        returning a rebuilt model validates that model again and asks this question
        of its own answer for ever. A field validator is handed the value the field
        already holds -- the entries, each built and checked -- so returning a
        different order of them ends the argument.
        """
        agents = [entry.agent for entry in worked]
        if len(set(agents)) != len(agents):
            repeated = sorted({agent for agent in agents if agents.count(agent) > 1})
            raise ValueError(
                f"{repeated} are each recorded more than once, and which of two counts to "
                f"believe is not a question this can answer; one agent has one count"
            )
        return tuple(sorted(worked, key=lambda entry: entry.agent))

    def how_many_times_this_agent_has_worked(self, agent: str) -> int:
        """How many times this agent has worked on this work item, zero if never.

        **Zero is arithmetic rather than a fallback.** An agent absent from the
        count has worked no times, and that is the answer to the question rather
        than a value standing in for one nobody gave. The distinction that matters
        in this package is between a fact and a silence, and "has not worked here
        yet" is a fact.
        """
        for entry in self.worked:
            if entry.agent == agent:
                return entry.how_many_times
        return NO_AGENT_HAS_WORKED_ON_THIS

    def and_another_turn_at_it_was_worked_on(self, agent: str | None) -> TheWorkEachAgentHasDone:
        """Hand back the same count with one more turn at the work item, by `agent`.

        The only function here that changes anything, and the only one anybody may
        call, so a count changes in one place or not at all. An agent already in
        the count has its number raised; an agent absent from it joins at one,
        because a turn is what puts it in the count.

        **A move that names no agent counts nothing**, and that is not a caller who
        forgot: a move onto `IN_PROGRESS_BY_AGENT` with nobody holding the work item
        is refused a line later by `validate_state`, because the biconditional says
        the two always agree. Counting it would only be a number for a work item
        nobody will ever see, and refusing it here would be a second error for one
        fault.
        """
        if agent is None:
            return self
        entries = [
            TheWorkOneAgentHasDone(agent=entry.agent, how_many_times=entry.how_many_times)
            for entry in self.worked
            if entry.agent != agent
        ]
        entries.append(
            TheWorkOneAgentHasDone(
                agent=agent,
                how_many_times=self.how_many_times_this_agent_has_worked(agent) + 1,
            )
        )
        return TheWorkEachAgentHasDone(worked=tuple(entries))
