"""A policy in charge of the approval gate, and the setting that puts one there.

**The gate is a hard architectural boundary and nothing in this module is inside it.** A model
cannot be imported by `src/aisdlc/approval/`, because a model deciding a decision would make the
gate an agent. So the policy answers from outside, where `ApprovalScript` answers in the tests:
it reads the artifact a person would read, asks a model, and hands the gate a decision. The gate
validates that decision exactly as it validates one typed at a terminal.

**Nothing here is a person, and the record must never say it is.** A decision naming somebody for
a judgement a model made is a forged audit trail, and `AgentDecidedError` cannot catch it because
the name is not in the `aisdlc-` namespace. So the policy signs in its own namespace, and the
setting that turns it on states a *name* — the namespace belongs to the code that knows what a
policy is, and a deployment spelling it twice is stating two things that can disagree.

**Off unless a deployment says otherwise.** A person's run is the ordinary case, and the setting
is what makes the substitution visible in the directory a run produced: a table of gates with a
policy's name on every row, which is the difference between a choice somebody made and a
behaviour a version happened to have.
"""

from __future__ import annotations

import os
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, ValidationError, field_validator

from aisdlc.agents.the_prompt_to_a_policy import the_prompt_to_a_policy
from aisdlc.approval.approval_decision import ApprovalDecision
from aisdlc.approval.approval_gate import THE_POLICY_NAMESPACE
from aisdlc.approval.approval_question import ApprovalQuestion
from aisdlc.domain.work_item import WorkItem
from aisdlc.graph.agent_state import AgentState
from aisdlc.llm.asking_a_model_for import (
    AModelAnsweredInAShapeThisSystemCannotReadError,
    ask_a_model_for,
)
from aisdlc.llm.correction_budget import may_this_run_keep_asking
from aisdlc.tools.the_project_directory import the_project_directory_of
from aisdlc.tools.what_a_run_leaves_behind import A_FILE_EXTENSION_A_PERSON_CAN_READ

# Stated by a deployment rather than written here, in this package's convention.
# `AISDLC_REPEAT_BUDGET` is the other one.
THE_SETTING_NAMING_THE_APPROVAL_POLICY = "AISDLC_APPROVAL_POLICY"


class APolicySettingThatNamesNoPolicyError(Exception):
    """A deployment set the setting to something that names no policy.

    **Refused rather than ignored, and this is the one setting where a fallback is the worst
    answer available.** Every other broken setting is a ceiling nobody noticed or a budget
    nobody meant. This one is a statement that the gate may be answered by something other than
    a person, and a truncated value is the shape it actually takes. Falling back would hand a
    run the right to approve its own work and leave no name in the record to quote in the
    argument about whose run it was.
    """

    def __init__(self, stated: str) -> None:
        """Quote what was set, because the fix is in a deployment's own configuration."""
        self.stated = stated
        super().__init__(
            f"{THE_SETTING_NAMING_THE_APPROVAL_POLICY} was read as {stated!r}, which names no "
            f"policy. A deployment says the name of the policy that answers the gate, and the "
            f"namespace is added for it — so the value is a bare name, not {THE_POLICY_NAMESPACE}"
            f"<name>."
        )


class APolicyAnsweredWithSomethingUnusableError(Exception):
    """The gate was answered by something that is not a verdict, and the run ran out of chances.

    **A named error where the pipeline had a raw `ValidationError`, and that is the whole of
    what this changes.** A person reading a trace should see that the gate received something
    unusable and that the run exhausted its corrections; `validation error` with a line number
    says neither and is the one failure in this pipeline a reader cannot act on.

    **Raised with the last refusal as its cause, so nothing is lost.** A run that ran out of
    budget raising something it had already raised teaches a reader nothing, so the last
    refusal travels with the error rather than being replaced by a nicer name for it.
    """

    def __init__(self, how_many_times_the_question_was_put: int, refused: Exception) -> None:
        """Say how many chances were spent, because that tells a reader what to change next.

        Whether to raise the budget or to fix the prompt is a decision only the reader can
        make, and the count is what makes it possible.
        """
        self.how_many_times_the_question_was_put = how_many_times_the_question_was_put
        super().__init__(
            f"The gate was asked its question {how_many_times_the_question_was_put} times and "
            f"was answered with something that is not a verdict each time. The artifact is on "
            f"disk beside the clone and can be read, and the answer is the one that is unusable: "
            f"{refused}"
        )


# **One word, and only one, because one word is what a run has actually produced.** A grounds field
# that announces itself as unfinished is not grounds — and `"Placeholder pending policy retrieval"`
# is the sentence a real policy answered with, which is the whole of what one gate said. `TODO` and
# `TBD` belong to the same class; **they are added when a run produces them, and not before.**
#
# **At the start, and not anywhere inside, because a real ground may name a placeholder
# value mid-sentence and this rule used to refuse that.** The word was matched inside the
# sentence, and the sentence defending it said a rule refusing honest grounds would stop the
# policy explaining itself — while the test beside it never contained the word at all. Then a
# real run about a placeholder test produced sixty-five verdicts the model could only word
# with the word *placeholder* in them, and the correction loop burned thirty-four minutes
# refusing every one: `flags the placeholder assertion` *calls* nothing itself anything. What
# the seen sentence does is *begin* with the announcement, so the match is the start.
ANY_WORD_THAT_ANNOUNCES_UNFINISHED_BUSINESS = "placeholder"

# **One shape, and only the shape that has been seen, because a grounds field that may not
# contain words is a list of banned words.** A real policy refused a real discovery report —
# twenty-two evidence files, the placeholder test named among them — with `Reviewing the
# DiscoveryReport before ruling.` That narrates the act of reviewing and defers the ruling the
# field exists to give, so a run ended on a verdict with nothing behind it and nobody could say
# whether the report or the policy was wrong. The match is the whole reason and not words inside
# it: honest grounds may well say they reviewed something, and a rule matching *reviewing*
# anywhere would stop a policy explaining itself. What is refused is a reason that *is* the
# deferral and nothing else.
ANY_DEFERRAL_OF_THE_RULING_ITSELF = re.compile(
    r"reviewing\s+.+\s+before\s+(ruling|deciding)\.?$", re.IGNORECASE
)


class WhatAPolicyJudged(BaseModel):
    """The RED shell: grounds, not a verdict. The rules come with the implementation.

    Shaped so the tests can prepare an answer, which is the only thing a double needs from a
    shape. What the policy does with the answer is the rule the tests are demanding.
    """

    approved: bool
    reason: str

    @field_validator("reason")
    @classmethod
    def _reject_a_verdict_with_no_grounds(cls, reason: str) -> str:
        """Refuse a verdict with nothing behind it, here and not at the decision.

        **The rule is duplicated deliberately, and the duplication is the point.** The decision
        refuses a blank reason too, and that refusal is the record's. This one is the *model's*,
        and it has to exist here or the correction loop never sees the failure: a blank ground
        would sail through this shape, be caught one step later by `ApprovalDecision`, and the
        run would raise a `ValidationError` from a constructor instead of asking the model
        again. The two refusals guard different boundaries and both have to hold.

        **And the second half of the same rule is a sentence calling itself a placeholder, because
        that is what a real policy answered with.**

        ```text
        Placeholder pending policy retrieval
        ```

        That is not blank, so `if not reason.strip()` waves it through — **and it is the whole of
        what the gate said**, at the one field a person reads. `reason` exists because an
        `approved: bool` with no grounds is a coin flip written down, and a placeholder ground
        defeats that more completely than a blank one: **a blank one is visibly missing and this
        one reads as an answer.**

        **One word, and one word only, because one word is what has been seen.** `TODO` and `TBD`
        belong to the same class and this repository does not guess: **a word joins this check
        when a run has produced it.** And the check is about the reason *calling itself* a
        placeholder, not about the word appearing — a real ground may well describe a placeholder
        value being replaced, and a rule that refused that would stop the policy explaining itself.
        """
        if not reason.strip():
            raise ValueError(
                "a policy that rules without saying why has not ruled, and a record that cannot "
                "be questioned is not a decision"
            )

        if re.match(
            rf"{ANY_WORD_THAT_ANNOUNCES_UNFINISHED_BUSINESS}\b", reason.strip(), re.IGNORECASE
        ):
            raise ValueError(
                f"{reason!r} calls itself a placeholder, so it is not grounds. **A policy that "
                "says it will say why later has not said why**, and the correction loop will "
                "spend its next turn on that.\n\n"
                "Say what made you refuse and what would change it: name the artifact, the claim "
                "you doubt, and what evidence would settle it. 'Placeholder pending policy "
                "retrieval' reads as an answer and is actionable by nobody."
            )

        if ANY_DEFERRAL_OF_THE_RULING_ITSELF.match(reason.strip()):
            raise ValueError(
                f"{reason!r} narrates reviewing and defers the ruling, so it is not grounds. "
                "**A policy that says it is still reviewing has not ruled**, and the correction "
                "loop will spend its next turn on that.\n\n"
                "Say what you found and what would change it: name the artifact, the claim you "
                "doubt, and what evidence would settle it. 'Reviewing the report before ruling' "
                "reads as an answer and is actionable by nobody."
            )

        return reason


def the_policy_a_deployment_stated() -> str | None:
    """The name a deployment will answer the gate under, or `None` when a person will.

    **A bare name, because the signer owns the namespace and not this function.** Applying it
    here would have been tidier and weaker: a caller could then hand the bare name straight to
    `ApprovalDecision` and sign a policy's decision as a person. `review_an_artifact` is the only
    thing that writes these records, and it is the only place the namespace has to be applied for
    the record to be honest. A deployment still states the name once and only once.

    **Read at the moment it is asked, not once at import**, for the reason the repeat budget is
    read that way: a deployment that changes this between two runs is stating two runs' policies.
    """
    stated = os.environ.get(THE_SETTING_NAMING_THE_APPROVAL_POLICY)

    if stated is None:
        return None

    name = stated.strip()

    if not name:
        raise APolicySettingThatNamesNoPolicyError(stated)

    # A deployment that wrote the namespace itself is stating the same thing twice, and the
    # second copy is the one that can disagree with the first. Saying it is refused rather than
    # unwrapped, because unwrapping quietly teaches two ways to say the same thing.
    if name.startswith(THE_POLICY_NAMESPACE):
        raise APolicySettingThatNamesNoPolicyError(stated)

    return name


def review_an_artifact(
    work_item: WorkItem,
    projects_root: Path,
    question: ApprovalQuestion,
    policy: str,
    model: BaseChatModel,
) -> ApprovalDecision:
    """Read the artifact, ask for grounds, and sign the answer as the policy rather than a person.

    **The artifact is read from the project directory, not from the question.** The question
    deliberately carries identity and not contents, so a policy answering from it would be
    reviewing nothing and approving on a filename. A person at this gate opens the file beside
    the clone, and so does this.

    **The model is asked for grounds and given the whole artifact**, because a verdict with no
    grounds is a coin flip written down. The reason travels verbatim into the decision — a run
    writing a reason on the model's behalf is the same forgery as a run writing a name.
    """
    the_artifact_on_disk = (
        the_project_directory_of(work_item, projects_root)
        / f"{question.artifact_id}{A_FILE_EXTENSION_A_PERSON_CAN_READ}"
    )
    what_the_run_produced = the_artifact_on_disk.read_text(encoding="utf-8")

    the_question_to_ask = the_prompt_to_a_policy(
        question, what_the_run_produced, the_project_directory_of(work_item, projects_root)
    )

    # **The correction loop, and the policy has one now because a real run proved it needed
    # one.** `plan_the_change` and the other five reasoning nodes catch a `ValidationError` and
    # buy another attempt; the policy did not, so a model that did not honour the forced tool
    # call took a run down at the gate. The budget is the same number and the same question as
    # everywhere else this system spends it: may this run go on asking a model for something it
    # already had?
    began_at = time.monotonic()
    asked_so_far = 0
    the_judgement: WhatAPolicyJudged | None = None

    while may_this_run_keep_asking(asked_so_far, began_at):
        asked_so_far += 1
        try:
            the_judgement = WhatAPolicyJudged.model_validate(
                ask_a_model_for(model, WhatAPolicyJudged).invoke(the_question_to_ask)
            )
            break
        except (AModelAnsweredInAShapeThisSystemCannotReadError, ValidationError) as unusable:
            last_refusal = unusable

    if the_judgement is None:
        raise APolicyAnsweredWithSomethingUnusableError(asked_so_far, last_refusal) from (
            last_refusal
        )

    return ApprovalDecision(
        work_item_id=question.work_item_id,
        artifact_id=question.artifact_id,
        artifact_version=question.artifact_version,
        approved=the_judgement.approved,
        decided_by=f"{THE_POLICY_NAMESPACE}{policy}",
        decided_at=datetime.now(UTC),
        reason=the_judgement.reason,
    )


# The shape the graph is handed: a node, so the graph never learns about models or policies.
AnswerTheGate = Callable[[AgentState], dict]


def a_policy_answering_this_gate(model: BaseChatModel) -> AnswerTheGate:
    """A node that answers one gate with a model's judgement, when a deployment named a policy.

    **A node rather than the policy itself, because every other collaborator in the graph is a
    node and this one closes over a model the graph has no business knowing about.** The graph
    learns that something can answer a gate; it does not learn what answers it.

    **Answers into `decisions`, the same channel a person answers into.** That is the whole of
    the design: the recording node downstream applies the same rules either way, so a policy gets
    no shortcut past the version check or the agent check, and the assertion that a policy cannot
    be recorded as an agent holds because there is nowhere else for it to go.
    """

    def answering_the_gate(state: AgentState) -> dict:
        the_policy = the_policy_a_deployment_stated()

        if the_policy is None:
            return {}

        the_question = ApprovalQuestion(
            work_item_id=state["work_item"].work_item_id,
            artifact_id=state["presented_artifact_id"],
            artifact_version=state["presented_artifact_version"],
        )

        return {
            "decisions": [
                review_an_artifact(
                    state["work_item"],
                    state["projects_root"],
                    the_question,
                    the_policy,
                    model,
                )
            ]
        }

    return answering_the_gate


class APolicyWasStatedAndNoPolicyAnswersError(Exception):
    """A deployment named a policy and the run was built with nothing to answer the gate with.

    **Raised rather than quietly answering nothing.** The routing read the setting, believed a
    policy was in charge, and handed the gate to a node that does not exist. A run that fell back
    to a person here would look identical to a deployment that never opted in — and the one fact
    somebody needs, that a policy was named and could not be honoured, would be nowhere.

    The two halves of the message are the two facts: the setting said a policy decides, and this
    run was assembled without one. The fix is on the caller's side, and it is a wiring change
    rather than a configuration one.
    """

    def __init__(self) -> None:
        """Carry both facts, because the fix is a wiring change and not a configuration one.

        Whoever reads this is looking at a deployment that set a variable and got a run nobody
        can explain. Saying which of the two halves is wrong is the difference between reading a
        config file and reading the assembly of the run.
        """
        super().__init__(
            f"{THE_SETTING_NAMING_THE_APPROVAL_POLICY} names a policy, so this run sent its "
            f"gates to a policy, and this run was built with no policy to answer them. Either "
            f"unset {THE_SETTING_NAMING_THE_APPROVAL_POLICY}, or build the run with a policy — "
            f"a run that fell back to a person would be indistinguishable from one that never "
            f"opted in."
        )


def no_policy_was_given_to_this_run(state: AgentState) -> dict:
    """The node a graph is registered with when nobody handed it a policy.

    **It raises rather than returning nothing**, because the routing only sends a gate here when
    a deployment named a policy. Reaching it at all means the setting and the wiring disagree,
    and returning an empty update would turn a misconfiguration into a run that quietly asked a
    person instead — the one outcome the setting was meant to make explicit.
    """
    raise APolicyWasStatedAndNoPolicyAnswersError
