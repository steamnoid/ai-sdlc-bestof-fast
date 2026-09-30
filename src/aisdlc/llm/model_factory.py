"""The one place a model is built. Nowhere else in this system may import a provider.

§3 requires that the application not hard-code a provider, that model initialisation
not be scattered across agents, and that the factory expose the common LangChain
chat-model interface with structured output. All three are rules about *this* module
being the only seam, and `tests/unit/test_model_factory.py` reads the whole package to
hold the last one.

A visible `if` per provider, rather than a lookup table, on purpose. The set is closed
and small, a table would hide which providers exist behind a dict, and a reader
comparing this against §3 should be able to do it line by line.
"""

from __future__ import annotations

import os

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from aisdlc.llm.llm_configuration import LlmConfiguration
from aisdlc.llm.llm_configuration_error import LlmConfigurationError
from aisdlc.llm.model_provider import LlmProvider
from aisdlc.observability.a_record_of_what_a_model_said import ARecordOfWhatAModelSaid
from aisdlc.observability.saying_what_a_run_is_doing import THE_SETTING_THAT_ASKS_TO_WATCH

# The header a gateway routes by. It is a fact about the gateways, not about our
# request, which is why it is named here and not spelled at the call site.
THE_HEADER_A_GATEWAY_ROUTES_BY = "x-opencode-session"


def the_headers_a_gateway_routes_by(configuration: LlmConfiguration) -> dict[str, str]:
    """Tell a gateway which run is asking, when we know it and it is listening.

    Empty when we do not know the run, and empty for every provider but the compatible
    one, because a gateway that routes by conversation is an OpenAI-shaped gateway and
    nobody else has asked. A run's identity is not a provider's business by default.
    """
    if configuration.thread_id is None:
        return {}

    return {THE_HEADER_A_GATEWAY_ROUTES_BY: configuration.thread_id}


# A deployment that wants to see what a model is saying says so with this, and the default is
# silence. **Imported rather than copied**, because the same switch now decides whether tool calls
# are announced too, and two copies of one setting is how a deployment ends up half-watching — which
# is the same fault as the two branch names this repository has already paid for.


def _the_handlers_watching(
    configuration: LlmConfiguration, asked_for: ARecordOfWhatAModelSaid | None
) -> list[BaseCallbackHandler]:
    """The handlers on this model: the record a caller passed, or one, or none at all.

    **Read here because this is the one place a model is built.** A caller that has to remember
    is a caller that will forget, and the six factories that build a model internally cannot
    remember anything. An empty list rather than `None` because the runtime's own type says a
    list of handlers, and a list holding `None` is a list with a hole in it.
    """
    if asked_for is not None:
        return [asked_for]

    if not os.environ.get(THE_SETTING_THAT_ASKS_TO_WATCH, "").strip():
        return []

    return [ARecordOfWhatAModelSaid(configuration.model)]


def a_model_for(
    configuration: LlmConfiguration,
    record: ARecordOfWhatAModelSaid | None = None,
) -> BaseChatModel:
    # A model built here and nowhere else, so **the deployment's wish to watch is read here and
    # nowhere else.** Six of a run's eight agents build their model through a
    # `*_using_the_configured_model()` factory and have nowhere to pass a record, so a switch
    # carried by the caller reached two stages and missed five. A whole run was silent for most
    # of itself and the log read as a hang.
    """The chat model the configuration names, ready to be asked for a typed answer.

    Every provider returns the same `BaseChatModel`, so an agent downstream cannot read
    the configuration and branch on it — the abstraction holds only if there is nothing
    to branch on, and that is a property of the return type rather than a promise in a
    docstring.

    **Every branch is handed the bound, because a branch that forgets is the failure this
    argument exists to prevent.** The container's run carries `seconds_it_may_take` for the
    same reason: a tool that waits forever cannot be told from one that is working. The
    spelling differs — `timeout` to one library, `request_timeout` to the other — and the
    test asserts on what each branch was handed rather than on the object that comes back,
    because `ChatOllama` consumes its timeout into an httpx client and keeps nothing to read.
    A test against the object would have covered three providers and left the fourth unbounded.

    **Streaming is off, and a live run is why.** Turning it on is the obvious way to get
    `on_llm_new_token`, and I did it: a token-by-token run then failed in 46 seconds with
    `ValueError: expected ident at line 1 column 2`, seven of seven tests, on a model that
    answers a structured request in prose. Without streaming the same model raises the same
    refusal *after* the whole answer has been assembled, the text survives inside the error, and
    an agent's correction loop gets its chance to re-ask.

    The reason is in the SDK: with `streaming=True` it parses each tool call's arguments as
    JSON **as the chunks arrive**, so a model that answered prose fails there and the chunks
    never reach LangChain's callbacks at all. Streaming therefore does not merely hide the
    answer on failure — it removes the recovery path the agents depend on, and it cost the
    whole tier its correction loops.

    `record` therefore still works and is still worth installing: `on_llm_start` names the model
    and the size of the question and `on_llm_end` says how long the answer took, and a provider
    that streams successfully gets word-by-word output for free without an agent knowing that
    observability exists. That is why no agent has been changed.

    **`record` has no behaviour of its own.** A caller that wants silence passes nothing and
    gets silence, which is what the default suite and CI need.

    The endpoint is required for `openai_compatible` and optional for `ollama`, which is
    not an inconsistency. A self-hosted model on this machine is the point of a local
    provider, so it has a sensible place to be and the provider's own default is the
    right one. "Compatible" names no machine at all, so a configuration that does not
    say where would otherwise build a model pointed at a cloud nobody asked for, and the
    mistake would surface as a network error against the wrong host.
    """
    if configuration.provider is LlmProvider.OPENAI:
        return ChatOpenAI(
            model=configuration.model,
            timeout=configuration.timeout_seconds,
            callbacks=_the_handlers_watching(configuration, record),
        )

    if configuration.provider is LlmProvider.OLLAMA:
        # **`sync_client_kwargs`, and not `request_timeout`, which is not a parameter.** Passing
        # the name anyway does not fail — `ChatOllama` swallows it — so the model comes back
        # holding a bound it never applies, and the only symptom is a run that hangs exactly as
        # it did before this line existed. That is the whole of "a field and the command it
        # describes cannot disagree", in a client library rather than in this repository.
        return ChatOllama(
            model=configuration.model,
            base_url=configuration.endpoint,
            sync_client_kwargs={"timeout": configuration.timeout_seconds},
            async_client_kwargs={"timeout": configuration.timeout_seconds},
            callbacks=_the_handlers_watching(configuration, record),
        )

    # Everything below speaks an OpenAI-shaped API at an address, so the address is
    # required rather than optional. `openai_compatible` and `openai_responses` each
    # name a protocol and neither names a machine, and a message that named one of them
    # instead of the configured one sent an operator to the wrong setting.
    if configuration.endpoint is None:
        raise LlmConfigurationError(
            f"{configuration.provider.value} names no machine to run on. Set "
            "LLM_ENDPOINT to the address that serves it."
        )

    if configuration.provider is LlmProvider.OPENAI_RESPONSES:
        return ChatOpenAI(
            model=configuration.model,
            base_url=configuration.endpoint,
            default_headers=the_headers_a_gateway_routes_by(configuration),
            use_responses_api=True,
            timeout=configuration.timeout_seconds,
            callbacks=_the_handlers_watching(configuration, record),
        )

    return ChatOpenAI(
        model=configuration.model,
        base_url=configuration.endpoint,
        default_headers=the_headers_a_gateway_routes_by(configuration),
        timeout=configuration.timeout_seconds,
        callbacks=_the_handlers_watching(configuration, record),
    )
