"""A model answer this system cannot read is repaired, and not the end of a run.

**A real run, at the sixth gate, and the run died of somebody else's bug.** The planner asked for a
plan. The model returned a tool call whose arguments were not valid JSON — the most ordinary wrong
answer a tool-calling model can give — and LangChain's handler for *that* case builds its own
message by reading the field it was about, so what escaped was a bare `KeyError` from inside the
handler rather than the `JSONDecodeError` it was written for:

    File "langchain_core/output_parsers/openai_tools.py", line 66,
        in _parse_ai_message_tool_call
        except JSONDecodeError as e:
            msg = (
                f"Function {raw_tool_call['function']['name']} arguments:\n\n"
    ...
    KeyError: 'name'

**And a `KeyError` is not something any of this repository's correction loops catch.** Each of the
nine has a budget, a prompt that says what was wrong last time, and a named `except` — and six of
the nine do not even name `ValidationError`. So the answer was wrong in the most ordinary way there
is, the budget existed to buy a second question, and **the run ended instead of asking it**.

**The fix is at the one seam every agent goes through, not in nine places.** `ask_a_model_for` is
where the answer stops being text and starts being data, so it is where "this is not an artifact
and here is why" belongs. Converting the failure there means **no agent's loop has to change to
catch it** — and the failure it becomes is one four loops already name.

**What is asserted is the conversion and not the library's behaviour.** LangChain's parser will be
fixed, or replaced, or configured differently, and this test must not care: the claim is that
whatever a parser does, this package's model boundary turns a read-it-failed into a refusal it can
say out loud, because the correction prompt is written from the refusal's own words.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from aisdlc.llm.asking_a_model_for import (
    AModelAnsweredInAShapeThisSystemCannotReadError,
    ask_a_model_for,
)


class AnArtifact(BaseModel):
    """Something a model is asked for, so the seam has a real type to force a tool for."""

    what_the_run_should_do: str


class _AParserThatCannotReadTheAnswer:
    """Stands in for LangChain's tool parser, which raised a bare `KeyError` on a real run.

    **The failure is raised from `invoke` and not from the model's method**, because that is where
    it happened: the model returned a tool call, and the parser read it. A double that raised while
    being asked would test a different thing — that `with_structured_output` can raise — and
    that is not the seam this file is about.
    """

    def __init__(self, what_the_parser_hit: Exception) -> None:
        self.what_the_parser_hit = what_the_parser_hit

    def with_structured_output(self, *arguments: object, **keywords: object) -> Any:
        """LangChain's entry point; the parser is decided, so this runnable is the answer."""
        return self

    def invoke(self, the_question: str) -> dict[str, object]:
        """Refuse to read the answer, the way the library did, with the library's own failure."""
        raise self.what_the_parser_hit


def test_a_parser_that_cannot_read_the_answer_is_named_rather_than_raised() -> None:
    """The raw failure never reaches the caller, and the reason is a refusal this package owns.

    **`KeyError` and not `Exception`, because the raw failure here was a `KeyError`** — a `dict`
    subscript on a key the answer did not carry. Anything broader would also swallow a genuine bug
    in a caller's own code and report it as a model that misbehaved, which is the one thing a
    correction prompt must never claim.
    """
    asking = ask_a_model_for(
        _AParserThatCannotReadTheAnswer(KeyError("name")), AnArtifact
    )

    with pytest.raises(AModelAnsweredInAShapeThisSystemCannotReadError) as the_refusal:
        asking.invoke("plan the change")

    assert isinstance(the_refusal.value.__cause__, KeyError), (
        f"the refusal was raised from {the_refusal.value.__cause__!r} rather than from the "
        "KeyError the parser raised, so the chain that caused it has been lost — and a "
        "correction prompt built from this refusal would tell a model nothing about what it "
        "did wrong"
    )


def test_the_refusal_says_what_failed_and_what_was_being_read() -> None:
    """The words are what the correction prompt is built from, so they have to be here.

    **A refusal that says only "the answer was unreadable" buys a second question that repeats
    the first.** The correction budget is spent on telling a model *what was wrong with its last
    answer*, so the refusal has to carry the parser's own failure — its type and its message —
    or the second question is a blank one and the budget is spent for nothing.
    """
    asking = ask_a_model_for(
        _AParserThatCannotReadTheAnswer(KeyError("name")), AnArtifact
    )

    with pytest.raises(AModelAnsweredInAShapeThisSystemCannotReadError) as the_refusal:
        asking.invoke("plan the change")

    what_it_says = str(the_refusal.value)
    assert "KeyError" in what_it_says, (
        f"the refusal is {what_it_says!r} and does not name the failure, so the correction prompt "
        "would tell a model its answer was unreadable without saying that a field was missing"
    )
    assert "name" in what_it_says, (
        f"the refusal is {what_it_says!r} and does not carry the parser's own message, which is "
        "the one fact about what was wrong that this system has"
    )


def test_an_answer_the_parser_could_read_is_returned_untouched() -> None:
    """The other half, because a seam that refuses everything is a run that delivers nothing.

    **The plain data comes back exactly as the model produced it**, because `ask_a_model_for`
    already declares its return type as `AnAnswerIsNotYetAnArtifact` — data, not an artifact —
    and every caller validates for itself. A wrapper that copied, re-encoded or checked the answer
    would make that declaration untrue.
    """
    what_the_model_answered = {"what_the_run_should_do": "remove the fallback"}

    asking = ask_a_model_for(_AModelThatReturns(what_the_model_answered), AnArtifact)

    assert asking.invoke("plan the change") == what_the_model_answered, (
        "a readable answer came back changed, and the seam's own return type says the answer is "
        "data until something validates it — a seam that alters it makes that declaration a lie"
    )


class _AModelThatReturns:
    """A model whose answer the parser read without complaint, which is every other run."""

    def __init__(self, the_answer: dict[str, object]) -> None:
        self.the_answer = the_answer

    def with_structured_output(self, *arguments: object, **keywords: object) -> Any:
        """LangChain's entry point; the answer is decided, so this runnable is the answer."""
        return self

    def invoke(self, the_question: str) -> dict[str, object]:
        """Hand back the answer, which is what a parser that could read it would have done."""
        return self.the_answer
