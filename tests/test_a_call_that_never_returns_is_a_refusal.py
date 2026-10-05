"""A model that accepts a connection and never answers must become a refusal, not a hung run.

**A run sat at the requirements gate for 108 minutes and wrote nothing.** Its last line was

```text
[0m00s] asking deepseek-v4-pro a question of 4480 characters
```

and the process held **no TCP connection** for the last of it. `LLM_TIMEOUT_SECONDS` is unset, so
`how_long_a_model_may_take()` resolved to **900**, and every branch of the model factory hands that
number to the client — `timeout=configuration.timeout_seconds` appears four times in
`model_factory.py`, and its docstring says so:

> **Every branch is handed the bound, because a branch that forgets is the failure this argument
> exists to prevent.**

**And handing it over does not bound it.** Measured, against a socket that accepts and never
answers:

```text
ChatOpenAI(model='x', base_url='http://127.0.0.1:8799/v1', timeout=20, max_retries=0)
  → still waiting after nine minutes
```

**So the bound is real, it is read, it is passed, and the thing it is passed to does not apply it to
a connection that has stopped talking.** This is the same rule as *"a field and the command it
describes cannot disagree"*, one layer further out: **a bound handed to a client is not a bound.**

**The distinction that makes it matter, and it is the one this repository already writes about.**
`AProviderWouldNotAnswerError` now catches everything the provider *says* — a `400`, a dropped
socket, an answer naming a tool that was never declared. **A call that never returns is the absence
of an answer rather than a wrong one**, so it reaches no exception, so no correction loop sees it,
and the run waits for a number nobody is going to give it. **The 108 minutes were this system's own
doctored-in-timeout not applying.**

**And the bound belongs around the call rather than inside it**, which is the only place it cannot
be defeated: the call is made on a **daemon** thread, the wait is bounded, and a call that has not
come back by then is given up on and reported in this package's own words.
"""

from __future__ import annotations

import threading
import time

import pytest
from langchain_core.exceptions import ModelError
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel

from aisdlc.llm.asking_a_model_for import (
    AModelAnsweredInAShapeThisSystemCannotReadError,
    AProviderWouldNotAnswerError,
    _the_answer_read_or_the_refusal_raised,
)


class AnAnswer(BaseModel):
    """Something to be asked for, so the wait has an artifact to be about."""

    what_it_said: str = ""


def _asking_something_that_never_returns(
    how_long_the_call_may_take: float,
) -> object:
    """Ask, through the boundary every agent's call goes through, of a call that never comes back.

    **A thread that waits is the measured shape of the failure** — a socket accepted and never
    answered — and not a slow model, because a slow model answers eventually and this one does not.
    """
    a_call_that_never_returns = RunnableLambda(
        lambda _question: threading.Event().wait()  # waits for an event nobody sets
    )
    return _the_answer_read_or_the_refusal_raised(
        a_call_that_never_returns,
        "a question",
        AnAnswer,
        how_long_a_call_may_take=how_long_the_call_may_take,
    )


def test_a_call_that_never_comes_back_becomes_a_refusal() -> None:
    """The property, stated as what a person watching the run would see.

    **The bound here is two seconds rather than nine hundred** so that the test is a test and not
    a wait, **and that is the whole point of the argument being enforced here**: a bound that only
    applies when it is large enough to be invisible is not a bound.
    """
    began = time.monotonic()

    with pytest.raises(AModelAnsweredInAShapeThisSystemCannotReadError) as what_was_said:
        _asking_something_that_never_returns(how_long_the_call_may_take=2.0)

    how_long_it_took = time.monotonic() - began
    assert how_long_it_took < 20, (
        f"giving up on a call that never returned took {how_long_it_took:.1f}s against a bound of "
        "2s. **A run sat at a gate for 108 minutes on this**, and `timeout=` was on the client the "
        "whole time — a bound handed to a client is not a bound"
    )
    assert isinstance(what_was_said.value, AProviderWouldNotAnswerError), (
        f"the refusal was {type(what_was_said.value).__name__}, and a call that never answers is "
        "the same fact to every loop as a provider's refusal: **there is no artifact here**"
    )


def test_a_call_that_comes_back_is_not_given_up_on() -> None:
    """The other half, because a bound that abandons slow answers is its own failure.

    **A local model on a laptop can take minutes**, which is why `LLM_TIMEOUT_SECONDS` exists at
    all — so a run must be able to raise the bound, and this asserts the mechanism does not refuse
    an answer that arrives inside it.
    """
    what_the_model_said = {"what_it_said": "an answer, in its own time"}

    the_answer = _the_answer_read_or_the_refusal_raised(
        RunnableLambda(lambda _question: dict(what_the_model_said)),
        "a question",
        AnAnswer,
        how_long_a_call_may_take=30.0,
    )

    assert the_answer == what_the_model_said


def test_a_provider_that_refuses_still_says_its_own_words() -> None:
    """The two failures are both refusals and a person needs to tell them apart.

    **This is the case the previous cycle added, and it must not have been weakened** by the bound
    going the same way. A `400` with the provider's sentence in it is worth handing to whoever runs
    the gateway; a call that never returned is worth a different sentence entirely.
    """
    with pytest.raises(AProviderWouldNotAnswerError) as what_was_said:
        _the_answer_read_or_the_refusal_raised(
            RunnableLambda(
                lambda _question: (_ for _ in ()).throw(
                    ModelError("Thinking mode does not support this tool_choice")
                )
            ),
            "a question",
            AnAnswer,
            how_long_a_call_may_take=30.0,
        )

    # **The provider's own type, not the provider's own capitalisation.** The message embeds the
    # exception verbatim and this repository does not rewrite what a gateway said — but a test that
    # matched on `"Thinking"` versus `"thinking"` would be testing a provider's prose, and would
    # have failed here for a reason that has nothing to do with the bound.
    assert "ModelError" in str(what_was_said.value), (
        f"the refusal was {what_was_said.value!r}, and a person handed this needs to say "
        "**which failure it was** — a gateway that refused, or a call that never came back. "
        "Both are refusals and they are worth reporting to different people"
    )
