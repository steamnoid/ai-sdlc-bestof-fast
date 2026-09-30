"""Which model to reason with, and the endpoint it answers at.

The field is called `endpoint` and not `base_url`, because `base_url` is the name one
particular provider's constructor happens to use. Naming a field after somebody else's
parameter makes their vocabulary ours, and the day a second provider spells it
differently there is no principled way to choose between them.

There is no credential field here, and that is a decision rather than an omission. A
secret held in a model that gets logged, traced and compared is a secret that leaks,
and the providers already read their own credentials from the environment:
`ChatOpenAI` looks for `OPENAI_API_KEY` and `ChatOllama` needs none. The thing this
configuration has to get right is *who* and *where*, and those are not secret.
"""

from __future__ import annotations

import os

from pydantic import BaseModel

from aisdlc.llm.llm_configuration_error import LlmConfigurationError
from aisdlc.llm.model_provider import LlmProvider

# How long a model may take when a deployment does not say. **It lives here and not in the
# factory, because the factory imports this module and a constant that both needed would be a
# cycle** — and the question "how long may a call take" is about the configuration, not about
# how a client happens to be built. Fifteen minutes: the longest single call a real run has
# made is around three, and a local model on a laptop is the case that needs the rest.
THE_DEFAULT_A_MODEL_MAY_TAKE = 900


class LlmConfiguration(BaseModel):
    """The provider, the model it names, and the endpoint it answers at."""

    provider: LlmProvider
    model: str
    endpoint: str | None = None
    thread_id: str | None = None
    timeout_seconds: int = 900


def a_configuration_from_the_environment() -> LlmConfiguration:
    """The configuration a deployment stated, read from `LLM_PROVIDER` and `LLM_MODEL`.

    Read only from the environment, with no argument a caller could pass instead. An
    override parameter here would exist for the tests' benefit, and a parameter that
    exists so a test can avoid touching the world is a seam in the wrong place: the
    tests set the environment instead, which is the thing this function actually reads
    and therefore the thing worth exercising.

    A provider we do not have is a configuration fault, so it leaves as
    `LlmConfigurationError` naming the value and the variable to change. Left to the
    enum, it would leave as a `ValueError`, which is a Python implementation detail
    reaching through a boundary and does not say which setting was wrong.
    """
    named = os.environ.get("LLM_PROVIDER", "")

    try:
        provider = LlmProvider(named)
    except ValueError:
        raise LlmConfigurationError(
            f"LLM_PROVIDER is {named!r}, which is not a provider this system can reach. "
            f"Choose one of: {', '.join(member.value for member in LlmProvider)}."
        ) from None

    return LlmConfiguration(
        provider=provider,
        model=os.environ.get("LLM_MODEL", ""),
        endpoint=os.environ.get("LLM_ENDPOINT") or None,
        # A deployment's stable session namespace, which is what a gateway routes by.
        # In a real run this is the run's own `thread_id`; from the environment it is
        # the one value every run of this deployment shares, and stable is the part the
        # gateway actually asks for — routing and prompt caching both key on it.
        thread_id=os.environ.get("LLM_THREAD_ID") or None,
        timeout_seconds=how_long_a_model_may_take(),
    )


def how_long_a_model_may_take() -> int:
    """How many seconds a call may take, read from `LLM_TIMEOUT_SECONDS`.

    **There is always a bound, and that is the part this function exists to state.** A
    deployment may raise it — a local model on a laptop can take minutes, and the Definition
    of Done asks for a local model to be proved by a real run — but a missing setting falls
    back to a number this repository chose rather than to *no limit*. Unbounded is the failure
    that cannot be diagnosed from outside a run: a gateway that accepted the connection and
    stopped answering is indistinguishable from one that is thinking.

    A value that is not a positive number is refused rather than ignored, because
    `LLM_TIMEOUT_SECONDS=""` read as "no timeout" is how a bound silently disappears, and
    `LLM_TIMEOUT_SECONDS=0` refused every call is a different failure wearing a timeout's
    name.
    """
    named = os.environ.get("LLM_TIMEOUT_SECONDS", "").strip()

    if not named:
        return THE_DEFAULT_A_MODEL_MAY_TAKE

    try:
        seconds = int(named)
    except ValueError:
        raise LlmConfigurationError(
            f"LLM_TIMEOUT_SECONDS is {named!r}, which is not a number of seconds. It is how "
            "long a model may take before the call is given up on, and a bound is better than "
            "none: leave it unset for the default rather than naming something that is not a "
            "duration."
        ) from None

    if seconds <= 0:
        raise LlmConfigurationError(
            f"LLM_TIMEOUT_SECONDS is {seconds}, which is not a bound a call can be given up "
            "against. A call that may take no time at all is not a call with a short timeout; "
            "it is a call that always fails. Set a positive number of seconds, or leave it "
            f"unset for the default of {THE_DEFAULT_A_MODEL_MAY_TAKE}."
        )

    return seconds
