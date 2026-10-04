"""A provider that will not answer becomes a refusal the loop can act on.

**Three runs in a row died at `make_and_verify_the_change`, and two of them were the provider
refusing rather than the model failing:**

```text
OpenAIInvalidRequestError: 400 — 'Thinking mode does not support this tool_choice'
OpenAIConnectionError: Connection error.
OutputParserException: Unknown tool type: 'TOOL_NAME'.
  Available tools: WhatTheImplementerConcluded
```

**The request shape is valid.** Sent directly, the same call came back clean — three for three, and
four ways in a separate check. **So these are not a defect in what this system sends, and no amount
of rewriting it would fix them.** They are a gateway that refuses or drops a fraction of the calls
it accepts, and **the run treats every one of them as the end of the run.**

**Which is the wrong place to end a run.** The correction loop exists for a model that could not be
read, and it is bounded by `AISDLC_CORRECTION_BUDGET` precisely so that asking again is cheap. **A
provider that says no deserves the same second turn as a model that said something unreadable** —
and the difference between the two is that the second one was never given a chance.

**And the catch has to stay narrow, because the existing one is narrow on purpose.**
`_the_answer_read_or_the_refusal_raised` catches `KeyError` alone, and its docstring gives the
reason: *"a broader catch would also convert a bug in a caller's own code into 'the model
misbehaved'"*. That objection holds, and it is why these two names are named rather than
`Exception`:

| what arrives | caught by |
|---|---|
| LangChain's own `400` | `ModelError` |
| a dropped socket | `ModelError` |
| `Unknown tool type: 'TOOL_NAME'` | `OutputParserException` |

**A `TypeError` in a caller's own code still propagates**, which is the whole of what the narrow
catch was for — and this test says so, because a catch that quietly widened would look exactly like
a fix.
"""

from __future__ import annotations

import pytest
from langchain_core.exceptions import ModelError, OutputParserException
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel

from aisdlc.llm.asking_a_model_for import (
    AModelAnsweredInAShapeThisSystemCannotReadError,
    _the_answer_read_or_the_refusal_raised,
)


class AnAnswer(BaseModel):
    """Something to be asked for, so the conversion has an artifact to refuse about."""

    what_it_said: str = ""


def _asking(a_refusal: Exception) -> object:
    """Ask, through the boundary every agent's call goes through, of a model that refuses.

    **The conversion is tested where it happens** — the function that turns whatever the provider
    did into this package's refusal — rather than through a whole chat model, **because a fake
    chat model has to satisfy `BaseChatModel` before it can be refused by anything.** A `Runnable`
    that raises is the shape this function actually takes.
    """
    return _the_answer_read_or_the_refusal_raised(
        RunnableLambda(lambda _question: (_ for _ in ()).throw(a_refusal)),
        "a question",
        AnAnswer,
    )


def test_a_provider_that_refuses_the_request_becomes_a_refusal_the_loop_can_act_on() -> None:
    """The outcome, stated as the property that matters: the loop can ask again.

    **This is the whole fix, and it is one clause in one `except`.** A run that has a correction
    budget and does not spend it on a provider's refusal has a budget for something narrower than
    it was written for.
    """
    with pytest.raises(AModelAnsweredInAShapeThisSystemCannotReadError):
        _asking(ModelError("Thinking mode does not support this tool_choice"))


def test_a_refusal_says_which_kind_it_was() -> None:
    """A provider's refusal and a reader's failure are different facts about different minutes.

    **A person reading the card after a refusal has to be able to tell "the model answered
    something I could not read" from "the provider would not answer at all"**, because the second
    one is worth reporting to whoever runs the gateway and the first is this system's own problem.
    """
    with pytest.raises(AModelAnsweredInAShapeThisSystemCannotReadError) as what_was_said:
        _asking(ModelError("Upstream request failed: thinking mode does not support this"))

    assert "thinking mode does not support this" in str(what_was_said.value), (
        f"the refusal was {what_was_said.value!r}. **A refusal that drops the provider's own words "
        "is a refusal a person cannot hand to whoever runs the gateway**, and this one died three "
        "runs in a row carrying a sentence nobody had read"
    )


def test_an_answer_naming_a_tool_this_system_never_declared_is_also_a_refusal() -> None:
    """The third of the three, which is a different failure wearing the same outcome.

    **`OutputParserException` is not a `ModelError`** — checked against the installed versions, not
    remembered — so a catch written for the provider alone would leave this one ending runs.
    """
    with pytest.raises(AModelAnsweredInAShapeThisSystemCannotReadError):
        _asking(OutputParserException("Unknown tool type: 'TOOL_NAME'."))


def test_a_bug_in_this_system_is_still_a_bug_and_not_the_models_fault() -> None:
    """The objection the narrow catch was written for, asserted so it cannot be quietly dropped.

    **A `TypeError` in a caller's own code is this system's bug and must reach the operator as
    itself.** The moment it becomes "the model misbehaved", the correction prompt sends a model to
    fix something that was never wrong, the budget is spent on it, and the real bug is reported as
    a model fault.
    """
    with pytest.raises(TypeError):
        _asking(TypeError("this package called something with the wrong shape"))

    with pytest.raises(KeyboardInterrupt):
        _asking(KeyboardInterrupt())
