"""A conflict is decided by choosing one of two named repairs, and never by writing prose.

**This is the contract and the plumbing, and the reasoning quality is not tested here.** A model
is asked what to do about a collision and is answered with a name out of a closed set; the tests
below hold the shape of the question, the refusal for anything outside the set, and the refusal
for a repair that belongs to a different conflict. **Whether a model picks the better repair is
`evals/`'s question and not a test's** — the same line this repository draws for the supervisor.

**Why a closed set at all, when a prompt could ask nicely.** This repository has a standing rule
about that, learned from a model citing a file that did not exist while being told to cite real
ones: a prompt that forbids something is not a check that it did not happen. So the options are
names, the answer is validated against them, and an answer outside them is refused **by name** —
with the two that were on offer in the message, so a model being corrected learns what it may say.

**Three conflicts and three sets, and a repair from the wrong one is refused too.** "Rebase it and
try again" said about an issue that is already tracked is not a choice between the two things on
offer; it is a decision about a situation nobody put to the model. A run that accepted it would
act on a judgement made in the wrong room.

**One attempt, and no correction budget.** A model handed two exact names and asked to pick one is
the case where a retry buys least and a refusal says most: there is nothing to re-read and nothing
to add, and `AConflictNobodyCouldRuleOnError` is a fact about this run rather than a stage in a
loop. The budget exists elsewhere in this system for answers that were *nearly* right — a plan
that named no file, a report whose evidence was not in the inspection — and this is not that.

**Nothing here is wired into the graph, and the docstring says why.** The decision belongs to a
node that has a conflict to offer; the one situation reachable in a delivery today — a pull
request GitHub will not merge — has a repair that needs a rebase this repository cannot perform,
and offering a model a choice between an action that can be taken and one that cannot is offering
it a coin. The contract is here so that day is a wiring job and not a design.
"""

from __future__ import annotations

import pytest

from aisdlc.agents.what_to_do_around_a_conflict import (
    THE_REPAIRS_OF_EVERY_CONFLICT,
    AConflictNobodyCouldRuleOnError,
    WhatKindOfConflict,
    WhatToDoAroundAConflict,
    WhatToDoWhenThePullRequestCannotBeMerged,
    WhatToDoWhenTheWorkIsAlreadyTracked,
    WhatToDoWhenTwoRunsChangedOneFile,
    what_to_do_around_a_conflict,
)

WHAT_GITHUB_SAID = (
    "GitHub says pull request 7 of steamnoid/wellbeing-tracker-public conflicts with the branch "
    "it would join, and it cannot be merged as it stands."
)


class _AModelThatAnswers:
    """A model that answers whatever it is asked and keeps the question, so a test can read it.

    **The question is kept and not only the answer returned**, because the whole of this
    mechanism is the set the model was offered: a test that only checked the returned decision
    would pass if the model had been asked to write a paragraph.
    """

    def __init__(self, the_answer: dict[str, object]) -> None:
        self.the_answer = the_answer
        self.what_it_was_asked: list[str] = []

    def with_structured_output(self, *arguments: object, **keywords: object) -> object:
        """LangChain's entry point; the answer is already decided, so this is the model."""
        return self

    def invoke(self, the_question: str) -> dict[str, object]:
        """Hand back the prepared answer and keep the question, which is what a test reads."""
        self.what_it_was_asked.append(the_question)
        return self.the_answer


def test_the_model_is_offered_two_named_repairs_and_asked_for_one_of_them() -> None:
    """Both options appear in the question, and what comes back is one of the two.

    **The question is asserted and not only the answer**, because a decision is only as closed as
    the set the model was shown. A prompt that described the two repairs in a paragraph and asked
    for "your decision" is exactly the arrangement this replaces.
    """
    the_model = _AModelThatAnswers(
        {
            "about": WhatKindOfConflict.THE_PULL_REQUEST_CANNOT_BE_MERGED.value,
            "which": WhatToDoWhenThePullRequestCannotBeMerged.LEAVE_IT_OPEN_AND_SAY_WHY.value,
            "why": "the base branch is protected, so a rebase would be merged into nothing",
        }
    )

    the_decision = what_to_do_around_a_conflict(
        the_model, WhatKindOfConflict.THE_PULL_REQUEST_CANNOT_BE_MERGED, WHAT_GITHUB_SAID
    )

    assert the_model.what_it_was_asked, "the model was never asked the question at all"
    the_question = the_model.what_it_was_asked[0]
    assert the_decision.which is WhatToDoWhenThePullRequestCannotBeMerged.LEAVE_IT_OPEN_AND_SAY_WHY
    for a_repair in WhatToDoWhenThePullRequestCannotBeMerged:
        assert a_repair.value in the_question, (
            f"{a_repair.value!r} is not in the question, so the model was asked to choose between "
            f"repairs it was not shown: {the_question}"
        )
    assert WHAT_GITHUB_SAID in the_question, (
        "the facts the decision is made on are not in the question, so the model is choosing "
        "between two repairs with nothing to choose between them"
    )


def test_an_answer_outside_the_named_set_is_refused_and_quoted() -> None:
    """Prose is not an answer, and the refusal says what was on offer instead.

    **The refusal names the two repairs**, so a model that has to be corrected learns what it may
    say rather than only that it was wrong. And it quotes the answer verbatim: "merge it anyway"
    is a decision a run must not act on and a person reading the record must be able to see.
    """
    the_model = _AModelThatAnswers(
        {
            "about": WhatKindOfConflict.THE_PULL_REQUEST_CANNOT_BE_MERGED.value,
            "which": "merge it anyway and see what happens",
            "why": "the person will probably not mind",
        }
    )

    with pytest.raises(AConflictNobodyCouldRuleOnError) as the_refusal:
        what_to_do_around_a_conflict(
            the_model, WhatKindOfConflict.THE_PULL_REQUEST_CANNOT_BE_MERGED, WHAT_GITHUB_SAID
        )

    said = str(the_refusal.value)
    assert "merge it anyway and see what happens" in said, (
        "the refusal does not quote the answer, so a person reading this run's record cannot see "
        "what the model said instead of choosing"
    )
    assert WhatToDoWhenThePullRequestCannotBeMerged.REBASE_IT_AND_TRY_AGAIN.value in said


def test_a_repair_belonging_to_another_conflict_is_refused() -> None:
    """A category error is not a choice, and it is the mistake a model is most likely to make.

    **The three sets exist to make this refusal possible.** With one set of repairs for all three
    conflicts, "rebase it and try again" would be a valid answer to a question about an issue that
    is already tracked, and a run would go looking for a branch to rebase.
    """
    the_model = _AModelThatAnswers(
        {
            "about": WhatKindOfConflict.THE_WORK_IS_ALREADY_TRACKED.value,
            "which": WhatToDoWhenThePullRequestCannotBeMerged.REBASE_IT_AND_TRY_AGAIN.value,
            "why": "it is the only thing I know how to do",
        }
    )

    with pytest.raises(AConflictNobodyCouldRuleOnError) as the_refusal:
        what_to_do_around_a_conflict(
            the_model, WhatKindOfConflict.THE_WORK_IS_ALREADY_TRACKED, WHAT_GITHUB_SAID
        )

    assert WhatToDoWhenTheWorkIsAlreadyTracked.DO_NOT_FILE_IT.value in str(the_refusal.value), (
        "the refusal does not name the repairs that were on offer, so a model that answered for "
        "the wrong conflict is not told which conflict it was asked about"
    )


def test_a_repair_with_nothing_behind_it_is_refused() -> None:
    """A name with no reason is a bare decision, and the same rule the supervisor's verdict holds.

    **Asserted here because it is the one field a model can fill with a space.** A decision about
    somebody else's repository that cannot be argued with afterwards is the failure this whole
    mechanism exists to prevent, and it arrives as an empty string rather than as an exception.
    """
    the_model = _AModelThatAnswers(
        {
            "about": WhatKindOfConflict.THE_PULL_REQUEST_CANNOT_BE_MERGED.value,
            "which": WhatToDoWhenThePullRequestCannotBeMerged.REBASE_IT_AND_TRY_AGAIN.value,
            "why": "   ",
        }
    )

    with pytest.raises(AConflictNobodyCouldRuleOnError) as the_refusal:
        what_to_do_around_a_conflict(
            the_model, WhatKindOfConflict.THE_PULL_REQUEST_CANNOT_BE_MERGED, WHAT_GITHUB_SAID
        )

    assert "no reason" in str(the_refusal.value) or "bare name" in str(the_refusal.value), (
        "the refusal does not say that a decision with no reason behind it is not a decision"
    )


def test_every_conflict_offers_its_own_two_repairs_and_shares_none() -> None:
    """Three conflicts, six repairs, and no name in two sets.

    **The table is read rather than restated**, so a repair added to one conflict and forgotten in
    the other cannot pass. This is the rule the three separate types exist for, and it is the one
    thing a reader of the module cannot check by eye once there are three of them.
    """
    every_repair = [
        a_repair
        for the_repairs in THE_REPAIRS_OF_EVERY_CONFLICT.values()
        for a_repair in the_repairs
    ]

    assert set(THE_REPAIRS_OF_EVERY_CONFLICT) == set(WhatKindOfConflict), (
        "a conflict has no repairs, so a decision about it cannot be made at all"
    )
    assert len(every_repair) == len(set(every_repair)) == 6, (
        f"the six repairs are {every_repair}, and a repair that appears in two sets is a repair "
        "that can be offered for a conflict it does not answer"
    )
    assert all(len(the_repairs) == 2 for the_repairs in THE_REPAIRS_OF_EVERY_CONFLICT.values()), (
        "a conflict with three repairs is a closed set this file has not argued for, and one with "
        "four is a preference rather than a choice"
    )
    assert WhatToDoWhenTwoRunsChangedOneFile.DO_NOT_PUSH_IT in (
        THE_REPAIRS_OF_EVERY_CONFLICT[WhatKindOfConflict.TWO_RUNS_CHANGED_ONE_FILE]
    )


def test_the_decision_a_conflict_carries_can_be_read_by_a_person() -> None:
    """The sentence that goes on a card, naming the conflict and the repair in full.

    **One method and not a `__str__`,** because the note is a record with a shape rather than a
    repr: a reader has to be able to see which situation was decided and which of the two repairs
    was chosen, without holding the enum in their head.
    """
    the_decision = WhatToDoAroundAConflict(
        about=WhatKindOfConflict.TWO_RUNS_CHANGED_ONE_FILE,
        which=WhatToDoWhenTwoRunsChangedOneFile.PUSH_IT_AND_LET_GITHUB_SAY,
        why="GitHub refuses a push to a branch that moved, and this run re-reads the branch first",
    )

    assert the_decision.the_text_of_the_decision_this_is() == (
        "two runs changed the same file: push it and let GitHub say. Because GitHub refuses a "
        "push to a branch that moved, and this run re-reads the branch first"
    )
