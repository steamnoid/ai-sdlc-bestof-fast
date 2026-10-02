"""The supervisor may ask a second time, because a run that reached it has paid for everything.

**The one agent with no correction loop, and it is the one a run reaches last.** Every other
agent in this repository asks inside `while may_this_run_keep_asking(...)`, and `supervise_a_repair`
asks **once**:

    the_decision = WhatToRepeat.model_validate(
        ask_a_model_for(model, WhatToRepeat).invoke(...)
    )

**And it is the worst place to be the exception.** A run only reaches the supervisor after six
gates, a clone, a commit and two container suite runs. One answer the reader could not parse ends
that, and there is no budget and no prompt in reserve — while the eight agents that reach their
refusal in seconds each have both.

**The budget is the same one, and the reason is that they are the same kind of thing.** The
supervisor's answer is a model's answer like any other, and a model's answer being unreadable is a
wrong answer rather than a refusal to answer. §0.3 says it in one line — *"malformed output is
rejected or repaired deterministically"* — and being the only asker with no repair is the whole of
what this test is about.

**The second question says what was wrong, because that is what the budget buys.** A second attempt
that repeats the first is not a repair; it is the run paying for the same answer twice. The prompt
is therefore asked with the refusal's own words appended, which is what
`how_a_model_is_told_what_was_wrong` exists for and what the other nine loops already do.

**What is *not* claimed.** A supervisor that runs out of budget still raises, and it raises the
same `TheRepeatBudgetRanOutError` an agent does — so a ceiling this node never had is now one it
has, and a run that asked too much ends the same way rather than in a place of its own.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aisdlc.domain.commissioned_request import a_request_about
from aisdlc.domain.repository import Repository
from aisdlc.domain.role import Role
from aisdlc.domain.work_item import WorkItem, a_work_item_commissioned_for_an_agent
from aisdlc.graph.supervise_a_repair import supervise_a_repair
from aisdlc.llm.asking_a_model_for import AModelAnsweredInAShapeThisSystemCannotReadError


@pytest.fixture
def an_open_register(tmp_path: Path) -> Path:
    """A register in this test's directory, because the supervisor leaves a note and that writes.

    **Not ceremony.** A supervisor that cannot record its own decision is a supervisor whose
    decision is unexplainable to whoever reads the run third, which is the whole of why it leaves
    one — so the fixture opens a real SQLite file rather than letting the note fail.
    """
    from aisdlc.store.where_the_register_lives import the_register_lives_at

    the_register_lives_at(tmp_path / "the-register.sqlite3")
    return tmp_path


class _AModelThatCannotReadTheFirstAnswer:
    """A model whose reader fails once, then answers, so the second question is observable.

    **Failing once and not always, because a model that never answers would prove only that the
    budget stops.** The claim here is that the supervisor asks again and takes the second answer,
    and a second answer that is never taken would be a repair in name only.
    """

    def __init__(self) -> None:
        self.the_questions: list[str] = []

    def with_structured_output(self, *arguments: object, **keywords: object) -> object:
        """LangChain's entry point; this model is its own answer."""
        return self

    def invoke(self, the_question: str) -> dict[str, object]:
        """Refuse to read the first answer the way the real reader did, and read the second."""
        self.the_questions.append(the_question)
        if len(self.the_questions) == 1:
            raise AModelAnsweredInAShapeThisSystemCannotReadError(
                KeyError("name"), _WhatToRepeatItIsAskedFor
            )
        return _what_the_second_answer_says()


class _WhatToRepeatItIsAskedFor:
    """Stands in for the artifact's name, so the refusal's message is the one a real one gives."""


def _what_the_second_answer_says() -> dict[str, object]:
    """A complete answer, in the shape `WhatToRepeat` validates."""
    from aisdlc.graph.the_agents_a_run_reasons_with import THE_AGENTS_A_RUN_REASONS_WITH
    from aisdlc.graph.what_to_repeat import (
        WhereTheRunShouldStartAgain,
    )

    return {
        "what_each_agent_must_do": [
            {
                "agent": an_agent,
                "must_repeat_its_work": an_agent == "aisdlc-dev-impl",
                "why": "the suite went red after the change",
            }
            for an_agent in THE_AGENTS_A_RUN_REASONS_WITH
        ],
        "where_to_start_again": WhereTheRunShouldStartAgain.THE_CHANGE_IS_WRITTEN_AGAIN.value,
        "what_has_not_changed": "the second attempt has not been made yet",
    }


def _a_work_item_somebody_was_holding() -> WorkItem:
    """A work item an agent holds, which is the only state a supervisor is ever reached in."""
    return a_work_item_commissioned_for_an_agent(
        work_item_id="issue-3",
        repository=Repository(owner="an", name="owner"),
        accountable_role=Role.DEV,
        commissioned_by="a person reading a test",
        requested=a_request_about("remove the fallback"),
    )


def test_the_supervisor_asks_again_when_the_first_answer_could_not_be_read(
    an_open_register: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One unreadable answer does not end a run that has already paid for six gates.

    **This is the claim, and the run that needed it** was not this repository's supervisor — it
    was a run killed by the same reader's failure at the *planner*, which proved it was
    real and proved the loops caught it.
    proved the loops caught it. **The supervisor was then found to have no loop at all**, so the …
    answer would have ended a run there too — and later than ever, because the supervisor is the
    last node before a decision about whether the run continues.
    """
    the_model = _AModelThatCannotReadTheFirstAnswer()
    monkeypatch.setenv("AISDLC_CORRECTION_BUDGET", "2")

    where_the_run_goes = supervise_a_repair(
        _a_work_item_somebody_was_holding(),
        an_open_register,
        "the suite went red after the change",
        the_model,  # type: ignore[arg-type]
    )

    assert len(the_model.the_questions) == 2, (
        f"the supervisor asked {len(the_model.the_questions)} times for an answer it could not "
        "use, and every other agent in this repository asks inside a budget. A run reaches this "
        "node after six gates, a clone, a commit and two container suite runs — so the one asker "
        "with no repair is the one where losing it costs the most"
    )
    assert "KeyError" in the_model.the_questions[1], (
        "the second question repeats the first verbatim, which is not a repair — the budget is "
        "spent on telling a model what was wrong with its last answer, and without that the second "
        "attempt buys the same answer a second time"
    )
    assert where_the_run_goes.goto == "offer_the_work_item_to_the_implementer", (
        f"the supervisor's second answer named the implementer and the run went to "
        f"{where_the_run_goes.goto!r} — the second attempt was made and then discarded, which "
        "is a repair in name only"
    )


def test_a_supervisor_that_never_answers_raises_its_own_refusal(
    an_open_register: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A supervisor that cannot rule at all ends on the refusal — not on the repeat ceiling.

    **My first version of this test expected `TheRepeatBudgetRanOutError` and that was wrong.**
    That error is a different fact, and its own docstring says why keeping the two apart matters:

        A separate type from `TheSupervisorJudgedThisIsNotRepairingError` because the two are
        different facts [...] A reader who cannot tell them apart goes to the wrong place — one to
        read the card, the other to read the setting.

    `TheRepeatBudgetRanOutError` means *the supervisor judged a repair worth trying and the
    deployment overruled it* — its judgement failed. A supervisor that never produced a judgement
    has failed differently: it never judged. **Raising the ceiling error here would send a reader
    to `AISDLC_REPEAT_BUDGET` for a run whose budget was never the problem**, and this repository's
    own rule is that the two ways a repair loop ends must not look alike in a record.

    **So it is the refusal, and it is the refusal the nine loops also end on.** A node that could
    not be repaired re-raises what it could not use — that is the whole of `raise last` in each of
    them — and the supervisor is one more asker rather than a place of its own.
    """
    monkeypatch.setenv("AISDLC_CORRECTION_BUDGET", "1")

    class _AModelThatNeverAnswers(_AModelThatCannotReadTheFirstAnswer):
        """Never returns, so the ceiling is what stops it rather than a second answer."""

        def invoke(self, the_question: str) -> dict[str, object]:
            self.the_questions.append(the_question)
            raise AModelAnsweredInAShapeThisSystemCannotReadError(
                KeyError("name"), _WhatToRepeatItIsAskedFor
            )

    the_model = _AModelThatNeverAnswers()

    with pytest.raises(AModelAnsweredInAShapeThisSystemCannotReadError):
        supervise_a_repair(
            _a_work_item_somebody_was_holding(),
            an_open_register,
            "the suite went red after the change",
            the_model,  # type: ignore[arg-type]
        )

    assert len(the_model.the_questions) == 2, (
        f"the supervisor asked {len(the_model.the_questions)} times with a budget of one "
        "correction. The budget is what stops it — one question, one correction, no third — and "
        "a ceiling nobody notices is the same failure wearing a different name"
    )
