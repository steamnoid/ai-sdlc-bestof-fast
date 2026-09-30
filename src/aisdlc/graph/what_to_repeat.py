"""What the repair supervisor decided, and why the questions are the ones it was asked.

**The supervisor answers one question per agent, and the answer is a closed set.** Three
failures were observed and each maps onto an agent: a suite that went red after the change is
the implementer's to try again, a test that passes without the change is the planner's — a plan
that named no product file is why there was nothing to observe — and a test in a directory the
repository does not collect tests in is the planner's too. **The product analyst is deliberately
not among them**, because nothing observed said the requirements were wrong, and routing a run
back to it would spend four gates on a guess.

**`what_has_not_changed` is an observation and not a judgement, and that is the whole reason
the supervisor can stop.** A model asked "is another attempt worth it?" has very little reason
to say no: each attempt looks reasonable alone and the failure only changes shape. This system
has an analyst that refused plannable work for six runs in a row. So the stop has to *name
something* — the sentence that has not moved between two attempts — because a named sentence
can be read and argued with, and "this is not working" cannot.

**A verdict is required for every agent, with no default.** An agent the model forgot is a
missing verdict rather than a stage that quietly does not run, which is the same distinction
`AnAmbiguity` forced and the one that made the analyst answerable.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from aisdlc.graph.the_agents_a_run_reasons_with import (
    THE_AGENTS_A_RUN_REASONS_WITH,
    THE_DEVELOPER_IMPLEMENTATION_AGENT,
    THE_DEVELOPER_PLANNING_AGENT,
)


class WhereTheRunShouldStartAgain(StrEnum):
    """The stage a run is put back to, as a closed set of three.

    **The implementer and the planner only, and the product analyst is not here.** The three
    observed failures split cleanly: a red suite is the implementer's to try again, and both
    vacuous-test failures are the planner's, because a plan that named no product file is why
    there was nothing to observe. Nothing observed said the requirements were wrong, and a
    target for the analyst would be a route back past four gates on a guess.
    """

    THE_CHANGE_IS_WRITTEN_AGAIN = "the change is written again"
    THE_CHANGE_IS_PLANNED_AGAIN = "the change is planned again"


class WhatOneAgentMustDoAgain(BaseModel):
    """One agent's verdict, and the reason for it, with no way to leave either out.

    Frozen and `extra="forbid"`: a conclusion this system did not ask for is one no human was
    ever shown, and a verdict with a spare key is a verdict about a stage nobody wired.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    agent: str
    must_repeat_its_work: bool
    why: str

    @field_validator("why")
    @classmethod
    def _refuse_a_verdict_nobody_gave(cls, why: str) -> str:
        """A verdict with no reason is a bare `True`, and a bare `True` is not a decision.

        It reads as an answer and cannot be argued with, which is the failure this whole type
        exists to prevent: a supervisor that repeats an agent's work must be able to say what
        it expected to be different, because that sentence is what a person reads to judge the
        decision afterwards.
        """
        if not why.strip():
            raise ValueError(
                "a verdict says which agent and whether it repeats, and this one says neither "
                "why nor anything else; a bare True is a fact with no decision in it"
            )
        return why


class WhatToRepeat(BaseModel):
    """What every agent in this run is to do, and what has not changed between attempts.

    **One verdict per agent and no default**, for the reason `AnAmbiguity` has one: an agent
    the model left out is a missing verdict rather than a stage that quietly does not run. The
    set is the closed list the supervisor was asked about, and a name outside it is refused by
    name rather than ignored.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    what_each_agent_must_do: tuple[WhatOneAgentMustDoAgain, ...]
    where_to_start_again: WhereTheRunShouldStartAgain
    what_has_not_changed: str

    @field_validator("what_has_not_changed")
    @classmethod
    def _refuse_a_stop_nobody_can_check(cls, what_has_not_changed: str) -> str:
        """A stop has to name what is the same, or it is a mood the run acted on.

        "This is not working" cannot be read and cannot be argued with. "The plan still names no
        product file" can be checked, and a person who disagrees can say so before the run stops
        or continues on it.
        """
        if not what_has_not_changed.strip():
            raise ValueError(
                "a decision to stop or to go on names the thing that has not changed between two "
                "attempts; a stop with nothing named is a mood, and a run that acts on a mood "
                "cannot be argued with afterwards"
            )
        return what_has_not_changed

    @model_validator(mode="after")
    def _refuse_an_agent_the_supervisor_never_spoke_about(self) -> WhatToRepeat:
        """A verdict for every agent in the run, and the forgotten ones named.

        **This is the rule that makes a supervisor's answer mean anything.** An answer for the
        planner and the implementer and nothing for the other five is indistinguishable from an
        answer for all seven, and the run then either repeats the missing stages or skips them —
        both of which read as a decision and neither of which was one. So the run's agents are
        named here, and an agent nobody gave a verdict for is refused *by name*, because a model
        correcting itself has to be told what it forgot rather than only that it was wrong.

        **The list is the run's own agents and not a list of whoever happens to appear in the
        answer.** A set of names gathered from the answer is a set the answer decided, and
        checking it against itself proves nothing.
        """
        judged = {verdict.agent for verdict in self.what_each_agent_must_do}
        never_spoken_about = set(THE_AGENTS_A_RUN_REASONS_WITH) - judged

        if never_spoken_about:
            raise ValueError(
                f"no verdict was given for {sorted(never_spoken_about)}, and a run cannot tell "
                f"an agent that had nothing to do from an agent nobody spoke about. A verdict is "
                f"required for every one of {sorted(THE_AGENTS_A_RUN_REASONS_WITH)}"
            )
        return self

    @model_validator(mode="after")
    def _refuse_answers_that_contradict_each_other(self) -> WhatToRepeat:
        """A decision whose two answers disagree is refused where it is built.

        **The supervisor is asked two questions in one answer and only one was being used.**
        `where_to_start_again` says where the run begins again; `must_repeat_its_work` says which
        agents have to work again. A model that said the implementer must work again and was
        routed to the planner produced two answers, and honouring the route repeats a stage the
        supervisor did not name. Refusing at the type is the only place both answers are visible
        together, and the refusal has to name both halves or whoever reads it will fix the wrong
        one.

        **The rule is on the route naming an agent nobody named, and not on how many were
        named.** A model may legitimately think the planner and the implementer are both wrong,
        and a guard that refused that would be a guard making the model quieter about what it
        found — the same fault as an analyst refusing a one-word change, which this repository has
        already paid for once.
        """
        named = {
            verdict.agent
            for verdict in self.what_each_agent_must_do
            if verdict.must_repeat_its_work
        }
        the_agent_this_route_names = (
            THE_DEVELOPER_IMPLEMENTATION_AGENT
            if self.where_to_start_again
            is WhereTheRunShouldStartAgain.THE_CHANGE_IS_WRITTEN_AGAIN
            else THE_DEVELOPER_PLANNING_AGENT
        )

        if named and the_agent_this_route_names not in named:
            the_others = sorted(named - {the_agent_this_route_names})
            raise ValueError(
                f"This decision sends the run to the agent behind "
                f"{self.where_to_start_again.value} and names {', '.join(the_others)} as the "
                f"one that has to work again. Both answers came from the same model in the same "
                f"answer, and one of them is being ignored: a run that repeats a stage the "
                f"supervisor did not name, or skips the one it did, is guessing on the "
                f"supervisor's behalf."
            )
        return self

    @model_validator(mode="after")
    def _refuse_one_agent_twice(self) -> WhatToRepeat:
        """One verdict per agent, because two verdicts for one agent is two answers to one.

        Which of them the run would believe is not a thing this type can decide, and the router
        would have to pick one without saying so.
        """
        agents = [verdict.agent for verdict in self.what_each_agent_must_do]
        if len(set(agents)) != len(agents):
            repeated = sorted({agent for agent in agents if agents.count(agent) > 1})
            raise ValueError(
                f"{repeated} are each given a verdict more than once, and which of two to "
                f"believe is not a question this can answer; one agent has one verdict"
            )
        return self

    def the_verdicts(self) -> dict[str, bool]:
        """Which agents must repeat their work, by name -- the run's branch condition."""
        return {
            verdict.agent: verdict.must_repeat_its_work
            for verdict in self.what_each_agent_must_do
        }

    def nobody_is_to_repeat_anything(self) -> bool:
        """Whether every agent was told to stand down, which is how a supervisor stops a run.

        **A separate question rather than something a caller works out**, because a caller
        asking `all(not v for v in ...)` is a caller able to get it backwards, and this is the
        one predicate that decides whether a run does anything at all.
        """
        return not any(
            verdict.must_repeat_its_work for verdict in self.what_each_agent_must_do
        )
