"""What a model decides when two pieces of work collide, as a closed set and nothing else.

**Three conflicts, and each has its own two repairs.** A pull request GitHub will not merge because
it conflicts with its base is a different problem from an opportunity that is already tracked as
somebody else's issue, which is a different problem again from two runs of this system having
changed one file between them. **They are three sets and not one set with a flag**, because the
repairs do not overlap: rebasing a pull request is not an answer to "an issue says this already",
and a pull request that GitHub calls unmergeable because its base is protected is not a conflict
at all.

**The model chooses a name from the set and writes no prose of its own.** The options are English
sentences and they are the only answers this accepts, for the reason this repository has already
learned the hard way about prompts: a prompt that says *do not do X* is not a check that X did
not happen. So the answer is a name, an answer outside the set is refused by name, and a decision
with no reason behind it is refused too.

**A repair that belongs to another conflict is not an answer here.** "Rebase it and try again" said
about an issue that is already tracked is a category error rather than a choice, and accepting it
would let a run act on a decision about a situation nobody put to it. The refusal says which
conflicts the answer could have been about, because a model that has confused two situations
needs to be told which one it was asked about.

**What is known is passed in as the caller's own words, and never summarised here.** A decision
made on a summary of a conflict is a decision about the summary. Whoever holds the conflict holds
the facts about it — the tool that refused, the gate that noticed — and this module only asks the
question and validates the answer.

**One of the three conflicts is asked about by a node, and the other two are not.** The pull
request that will not merge is the only collision a delivery can reach, so
`settle_the_conflict_in_this_run` asks this question and does what the answer says. The other two
have a caller that would have to notice a refusal and route it — a duplicate in
`filing_what_the_briefing_found`, and a branch that moved under `create_a_branch_on_a_remote` —
and neither does that yet, so a collision there is still refused by its own rule rather than
decided about. **The set was written down for those two first**, and it is still the honest answer
to reach for rather than a new question invented per site.
"""

from __future__ import annotations

from enum import StrEnum

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from aisdlc.llm.asking_a_model_for import ask_a_model_for


class WhatKindOfConflict(StrEnum):
    """Which of the three collisions this decision is about, named rather than described.

    **A closed set, because a decision needs to be about something.** "A conflict" on its own is
    a word that covers a rebase, a duplicate issue and two runs editing one file, and the three
    have no repair in common — so the kind is asked first and the repairs follow from it.
    """

    THE_PULL_REQUEST_CANNOT_BE_MERGED = "the pull request cannot be merged"
    THE_WORK_IS_ALREADY_TRACKED = "the work is already tracked"
    TWO_RUNS_CHANGED_ONE_FILE = "two runs changed the same file"


class WhatToDoWhenThePullRequestCannotBeMerged(StrEnum):
    """The two repairs for a pull request that will not merge, and no third.

    **Both of these can now be taken, which is why this set exists as a choice and not a contract.**
    For a while the first one named a rebase this repository had no tool for, and a model offered a
    choice between an action that could be taken and one that could not is a coin rather than a
    decision — so the set was written down, tested, and left unwired. `rebase_the_branch_a_run_
    pushed` is the operation that was missing and `settle_the_conflict_in_this_run` is the node
    that asks, so both repairs here are things a run can do.
    """

    REBASE_IT_AND_TRY_AGAIN = "rebase it and try again"
    LEAVE_IT_OPEN_AND_SAY_WHY = "leave it open and say why"


class WhatToDoWhenTheWorkIsAlreadyTracked(StrEnum):
    """The two repairs for an opportunity somebody has already filed.

    **The second one files anyway and says what it collides with**, which is the option that does
    not exist in the duplicate refusal the filing path already has. That refusal is deliberate and
    its cost is stated in this repository's own words: a duplicate is noise in somebody's queue
    and a dropped opportunity is work nobody hears about. This set is where a deployment that
    disagrees with that trade would put its decision, and it is not wired to the refusal, so
    nothing here changes the rule that is in force.
    """

    DO_NOT_FILE_IT = "do not file it"
    FILE_IT_WITH_A_NOTE = "file it with a note saying what it collides with"


class WhatToDoWhenTwoRunsChangedOneFile(StrEnum):
    """The two repairs for two runs of this system having changed one file between them.

    **Pushing and letting GitHub refuse is a real answer and not a shrug**: a push that GitHub
    rejects because the branch moved is a rejection a person can read, and this system re-reads
    the branch before it pushes anything, so a push here is not going to overwrite somebody's
    work. The other answer is to stop and say so, which is what a run does when it would rather
    a person look than have GitHub decide.
    """

    PUSH_IT_AND_LET_GITHUB_SAY = "push it and let GitHub say"
    DO_NOT_PUSH_IT = "do not push it"


THE_REPAIRS_OF_EVERY_CONFLICT = {
    WhatKindOfConflict.THE_PULL_REQUEST_CANNOT_BE_MERGED: (
        WhatToDoWhenThePullRequestCannotBeMerged
    ),
    WhatKindOfConflict.THE_WORK_IS_ALREADY_TRACKED: WhatToDoWhenTheWorkIsAlreadyTracked,
    WhatKindOfConflict.TWO_RUNS_CHANGED_ONE_FILE: WhatToDoWhenTwoRunsChangedOneFile,
}
"""Which repairs belong to which conflict, as one table, and the refusals are written from it.

**One table so the three sets cannot drift apart from each other or from the refusal.** An answer
outside its own set is refused with the two names it could have been, read out of here — so a
reader who has been told "nobody could rule on this" can see the choice that was available.
"""

A_REPAIR_OF_ANY_CONFLICT = (
    WhatToDoWhenThePullRequestCannotBeMerged
    | WhatToDoWhenTheWorkIsAlreadyTracked
    | WhatToDoWhenTwoRunsChangedOneFile
)


class AConflictNobodyCouldRuleOnError(Exception):
    """The answer was not one of the repairs on offer, so there is no decision to act on.

    **Named for the absence of a decision rather than for a bad value.** A model that answered
    "merge it anyway", or that answered a repair belonging to a different conflict, has not
    chosen between the things it was offered — and a run that picked one for it would be acting on
    a judgement nobody made. The refusal quotes the answer and names the two that were on offer,
    because a model that has to be told what it may say is being corrected rather than refused.
    """


class WhatToDoAroundAConflict(BaseModel):
    """One decision: which conflict, which repair, and why — with no way to leave any out.

    **Frozen and `extra="forbid"`,** so a conclusion this system did not ask for is one no human
    was ever shown. The `why` is required and may not be blank, for the reason the supervisor's
    verdict requires one: a repair with nothing named behind it reads as an answer and cannot be
    argued with, and "this is not working" is a mood a run acted on.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    about: WhatKindOfConflict
    which: A_REPAIR_OF_ANY_CONFLICT
    why: str

    @field_validator("why")
    @classmethod
    def _refuse_a_repair_nobody_gave_a_reason_for(cls, why: str) -> str:
        """Refuse a blank reason, and say what a decision with nothing behind it is."""
        if not why.strip():
            raise ValueError(
                "a repair says which conflict it is about and why, and a repair with no reason is "
                "a bare name. It reads as a decision and cannot be argued with, which is the one "
                "thing a decision about somebody else's repository must not be"
            )
        return why

    def the_text_of_the_decision_this_is(self) -> str:
        """The decision as a sentence a person reads on a card, naming both halves of it.

        **A method and not a `__str__`,** because the note is a record with a shape: a reader has
        to see which situation was decided and which of the two repairs was chosen without holding
        either enum in their head, and the two sentences are the whole of it.
        """
        return f"{self.about.value}: {self.which.value}. Because {self.why}"


def what_to_do_around_a_conflict(
    the_model: BaseChatModel,
    about: WhatKindOfConflict,
    what_is_known: str,
) -> WhatToDoAroundAConflict:
    """Ask which of two named repairs to make, and refuse anything that is not one of them.

    **Asked once, and the refusal is the answer's own words.** There is no correction budget here:
    a model handed two exact names and asked to pick one is the case where a retry buys least,
    because there is nothing to re-read and nothing to add to the question. A budget earns its
    keep where an answer was nearly right — a plan that named no file, a report whose evidence
    was not in the inspection — and this is not that.

    **The three checks are in this order and the order is the argument.** The answer has to parse
    into the shape before anything can be compared, the repair has to belong to the conflict it
    was asked about, and only then is the reason required to be something. A run that got as far
    as "the reason is blank" before noticing the answer was prose would be complaining about the
    wrong half of a model's mistake.
    """
    what_the_model_answered = ask_a_model_for(the_model, WhatToDoAroundAConflict).invoke(
        the_question_to_put_to_the_model(about, what_is_known)
    )
    the_decision = _a_decision_out_of(what_the_model_answered, about)
    _refuse_a_repair_that_is_not_one_of_the_two_offered(the_decision, about)
    _refuse_a_repair_with_nothing_behind_it(the_decision)
    return the_decision


def the_question_to_put_to_the_model(about: WhatKindOfConflict, what_is_known: str) -> str:
    """The two repairs, the conflict, and the facts — and an instruction to answer with one name.

    **Both repairs are named, because a choice between unnamed things is a preference.** The
    question says what is known in the caller's own words, so the decision is made on the conflict
    rather than on a summary of it.
    """
    the_repairs = THE_REPAIRS_OF_EVERY_CONFLICT[about]
    return "\n".join(
        [
            f"About this conflict: {about.value}.",
            "",
            "What is known about it:",
            what_is_known,
            "",
            "Choose exactly one of these, and answer with that sentence and nothing else:",
            *(f"- {a_repair.value}" for a_repair in the_repairs),
        ]
    )


def _a_decision_out_of(
    what_the_model_answered: object, about: WhatKindOfConflict
) -> WhatToDoAroundAConflict:
    """The validated decision, or a refusal naming what came back and what it could have said.

    **A `ValidationError` is turned into the one refusal a reader can act on.** A traceback
    carrying a field name and a line number says neither what the model said nor what it was
    offered, and the two together are the whole of the correction.
    """
    try:
        return WhatToDoAroundAConflict.model_validate(what_the_model_answered)
    except ValidationError as unusable:
        raise AConflictNobodyCouldRuleOnError(
            f"about {about.value}, the model answered {what_the_model_answered!r}, which is not a "
            f"decision. The repairs on offer were "
            f"{[a_repair.value for a_repair in THE_REPAIRS_OF_EVERY_CONFLICT[about]]}, and the "
            f"answer has to be one of them. This is what was unusable: {unusable}"
        ) from unusable


def _refuse_a_repair_that_is_not_one_of_the_two_offered(
    the_decision: WhatToDoAroundAConflict, about: WhatKindOfConflict
) -> None:
    """A repair from another conflict is a category error, not a choice between two things.

    **This is the rule the three separate sets exist for.** One set for all three conflicts would
    accept "rebase it and try again" as an answer about an issue that is already tracked, and the
    run would go looking for a branch to rebase.
    """
    if the_decision.which in THE_REPAIRS_OF_EVERY_CONFLICT[about]:
        return
    raise AConflictNobodyCouldRuleOnError(
        f"the model was asked about {about.value} and answered {the_decision.which.value!r}, "
        f"which is a repair for a different conflict. The repairs on offer were "
        f"{[a_repair.value for a_repair in THE_REPAIRS_OF_EVERY_CONFLICT[about]]}, and a decision "
        "about a situation nobody put to the model is not a decision about this one"
    )


def _refuse_a_repair_with_nothing_behind_it(the_decision: WhatToDoAroundAConflict) -> None:
    """A name with no reason behind it is a bare decision, and it is refused in the model's words.

    **The rule is duplicated on the type and the duplication is the point.** The validator there
    is what pydantic enforces on the way in; this one is the refusal that names the conflict and
    the repair, because a run that stops with "blank" and a run that stops with "the model chose
    this about that, and said nothing" are very different things to read afterwards.
    """
    if the_decision.why.strip():
        return
    raise AConflictNobodyCouldRuleOnError(
        f"the model chose {the_decision.which.value!r} about {the_decision.about.value} and gave "
        "no reason. A decision with nothing named behind it reads as an answer and cannot be "
        "argued with, and this one would be acted on somebody else's repository"
    )
