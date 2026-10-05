"""How an agent asks a model for a structured artifact, and why it is not `with_structured_output`.

**The tool is forced, not offered, and two dead runs are why.** LangChain's
`with_structured_output` hands the model a tool and lets it answer however it likes; the
`openai_compatible` gateway this deployment uses does not enforce the JSON-schema method that
call defaults to. Left to itself, `space-bunny-free` answered a structured request three ways
across three runs: prose, then YAML (`test_strategy: "Run an a...livery-pipeline check."`),
then JSON carrying one of four fields. Each became a `ValidationError`, and each ended a run
at a different stage.

A direct request to the same gateway, with `tool_choice` naming the function, came back with
all four fields and every one of them non-empty, in thirty-one seconds. So the model was never
the difficulty and neither was the correction budget — which had been raised in my head and
which this made pointless to raise.

**Function calling rather than JSON mode**, because only a tool call can be forced. `json_mode`
asks for JSON inside a message, and a gateway that does not enforce `response_format` returns
prose from it; this system reads the answer as an artifact either way, so a request it cannot
compel is a request whose failure it pays for.

**The artifact's own name is the tool name**, so the forcing names the artifact rather than a
label invented here. A model told to call `QaPlanAnswer` and shown a tool by that name is being
asked for the same thing twice, and a mismatch between the two would be a refusal to explain.
"""

from __future__ import annotations

import threading
from typing import TypeVar

from langchain_core.exceptions import ModelError, OutputParserException
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import BaseModel

from aisdlc.llm.llm_configuration import how_long_a_model_may_take

Artifact = TypeVar("Artifact", bound=BaseModel)

# **The deployment's own bound, read once at import so the wait and the number cannot
# disagree.** It is read here rather than passed in because every agent's ask goes through
# this one function, and a second reading is a second place for the setting to be wrong.
THE_LONGEST_A_CALL_MAY_TAKE = how_long_a_model_may_take()

AnAnswerIsNotYetAnArtifact = dict[str, object] | BaseModel


class AModelAnsweredInAShapeThisSystemCannotReadError(Exception):
    """A model's answer could not be read as an artifact, and this says what the reader hit.

    **A real run, at the sixth gate, and the run died of somebody else's bug.** The planner asked
    for a plan. The model returned a tool call whose arguments were not valid JSON, and
    LangChain's handler for *that* case builds its own message by reading the field it was about
    so the exception that escaped was a bare `KeyError` from inside the handler:

        File "langchain_core/output_parsers/openai_tools.py", line 66,
            in _parse_ai_message_tool_call
            except JSONDecodeError as e:
                msg = (
                    f"Function {raw_tool_call['function']['name']} arguments:\n\n"
        ...
        KeyError: 'name'

    **The failure is in the error handler rather than in the parse**, which is why the run's
    traceback does not point at anything recognisable and why a reader would spend a long time
    looking for a mistake in this repository. A `JSONDecodeError` in the model's own arguments is
    the most ordinary wrong answer a tool-calling model can give.

    **And a `KeyError` is caught by none of this repository's nine correction loops**, so the run
    ended where it had a budget and a prompt written for exactly this. The answer was wrong in the
    most ordinary way there is, and the machinery to ask again was never reached.

    **The reader's failure is named rather than swallowed, and both halves of it are carried.** The
    correction prompt is written from a refusal's own words, so a refusal saying only "the answer
    was unreadable" buys a second question that repeats the first — and the cause is kept so
    whoever reads the trace can see which reader failed, which this package does not own.
    """

    def __init__(
        self, what_the_reader_hit: BaseException, the_artifact: type[BaseModel] | None
    ) -> None:
        """Say which artifact was being read, and what the reader raised saying.

        **The type and the message, and not a paraphrase.** `KeyError('name')` says a field was
        absent and names it; "the parser failed" says neither, and costs the model the one fact it
        could have acted on.
        """
        if the_artifact is None:
            super().__init__(
                f"{what_the_reader_hit} — nothing was asked for, or nothing came back to be read."
            )
            return
        super().__init__(
            f"{the_artifact.__name__} was asked for and the answer could not be read as one. "
            f"Reading it raised {type(what_the_reader_hit).__name__}: {what_the_reader_hit}. "
            f"Answer with a single call to the {the_artifact.__name__} function and nothing else "
            f"— no prose, no YAML, and no field left out, because a field left out is what this "
            f"refusal is about."
        )


def ask_a_model_for[Artifact: BaseModel](
    the_model: BaseChatModel, the_artifact: type[Artifact]
) -> Runnable[LanguageModelInput, AnAnswerIsNotYetAnArtifact]:
    """The model, bound to a tool it is not allowed to answer without.

    **The answer is not typed as the artifact, and the name says why.** Nothing guarantees the
    model honoured the tool, so what comes back is data until something validates it, and every
    caller does that itself. Naming the type `AnAnswerIsNotYetAnArtifact` is what stops a reader
    from treating a returned dictionary as a plan.

    **And a reader that fails becomes a refusal of ours, which is a real run's finding.** Every
    agent's correction loop is built to spend a second question on an answer it cannot use, and
    nine loops name their own failures while none of them named the framework's — so a run died at
    the planner of a `KeyError` with a budget in hand. This function is where an answer stops being
    text and becomes data, so it is where "this is not an artifact and here is why" belongs, and
    converting it here means **no agent's loop has to be edited to catch it**.

    **A `KeyError` and not `Exception`, and the reason is the evidence rather than caution.** The
    failure that killed the run was a subscript on a key the answer did not carry. A broader catch
    would also convert a bug in a caller's own code into "the model misbehaved" — the one claim a
    correction prompt must never make, because it would send a model to fix something that was not
    its fault and spend the budget doing it.
    """
    the_forced_asking = the_model.with_structured_output(
        the_artifact,
        method="function_calling",
        tool_choice=the_artifact.__name__,
    )
    return RunnableLambda(
        lambda the_question: _the_answer_read_or_the_refusal_raised(
            the_forced_asking, the_question, the_artifact
        )
    )


class AProviderWouldNotAnswerError(AModelAnsweredInAShapeThisSystemCannotReadError):
    """The provider would not answer at all, rather than answering something unreadable.

    **Three runs in a row died at `make_and_verify_the_change` and two of them were this**, with
    the provider's own words:

    ```text
    OpenAIInvalidRequestError: 400 — 'Thinking mode does not support this tool_choice'
    OpenAIConnectionError: Connection error.
    OutputParserException: Unknown tool type: 'TOOL_NAME'.
    ```

    **The request shape is valid** — sent directly, the same call came back clean, three for three.
    So these are not a defect in what this system sends and no rewrite of it would fix them; they
    are a gateway that refuses or drops a fraction of the calls it accepts. **The run treated every
    one as the end of the run**, which is the wrong place to end one: the correction loop exists
    for a model that could not be read and is bounded precisely so that asking again is cheap, and
    **a provider that says no deserves the same second turn as a model that said something
    unreadable.**

    **A subclass rather than a new name in nine correction loops.** The two are the same fact to a
    caller — *there is no artifact here* — and the difference is only what a person reading the
    card after it is told. **Subclassing means nine loops need no edit and one name says both**, and
    the message says which kind this was.

    **An `__init__` of its own, because the base one takes two arguments** — the reader's
    exception and the artifact — and this refusal is handed one message. **A subclass inheriting a
    two-argument constructor and raised with one fails inside its own construction**, which is
    worse than the failure it was added for: the traceback names a `TypeError` about `__init__`
    rather than the provider's refusal.
    """

    def __init__(
        self, what_the_provider_said: BaseException, the_artifact: type[BaseModel] | None
    ) -> None:
        """Say what the provider did, and which artifact was being asked for when it is known.

        **`None` for the artifact, and only for the wait that ran out** — the bound is enforced
        around the call, so a call that never returns is refused before there is an artifact to be
        refused about. **Every other refusal has one**, and a message that names it tells a model
        what to answer.
        """
        super().__init__(what_the_provider_said, the_artifact)
        self.what_the_provider_said = what_the_provider_said
        self.the_artifact = the_artifact


def _the_answer_or_a_given_up_on[Artifact: BaseModel](
    the_forced_asking: Runnable[LanguageModelInput, AnAnswerIsNotYetAnArtifact],
    the_question: LanguageModelInput,
    how_long_a_call_may_take: float,
) -> AnAnswerIsNotYetAnArtifact:
    """The answer, or this package's refusal because the call did not come back in time.

    **The bound is enforced here and nowhere else, because everywhere else it does not hold.**
    `model_factory.py` hands `timeout=configuration.timeout_seconds` to all four branches, and its
    own docstring says *"every branch is handed the bound"* — and the client does not apply it to a
    connection that has stopped talking. Measured against a socket that accepts and never answers:

    ```text
    ChatOpenAI(base_url='http://127.0.0.1:8799/v1', timeout=20, max_retries=0)
      → still waiting after nine minutes
    ```

    **So a run sat at a gate for 108 minutes** with the bound set, passed, and inapplicable, and
    its last line said a question had been asked of a model that never answered. This is the same
    rule as *"a field and the command it describes cannot disagree"* one layer further out: **a
    bound handed to a client is not a bound.**

    **A daemon thread, and `daemon=True` is the load-bearing word.** The first version of this used
    a `ThreadPoolExecutor`, whose worker threads Python **joins at interpreter exit**
    (`concurrent.futures.thread._python_exit` puts `None` on every queue and then `t.join()`s each
    one) — so a worker blocked on a never-answering socket **prevented the process from ending**,
    and the run hung at exit instead of at the call. **That is the same failure moved**, and it is
    why the note here was corrected rather than kept: a bound that stops the waiting but not the
    process has not bounded anything a person is watching.

    **What is not bounded is the thread; what is bounded is the run's waiting.** There is no way to
    stop a thread blocked on a socket, and pretending otherwise would be a lie in a docstring about
    not lying. **The thread dies with the process**, which is why it is a daemon.

    **The call's own exception is carried out rather than raised on the calling thread**, because a
    provider's refusal arrives as an exception and this function must not turn one into an
    `IndexError` on an empty list.
    """
    what_the_call_produced: list[AnAnswerIsNotYetAnArtifact | BaseException] = []
    the_call_is_over = threading.Event()

    def make_the_call() -> None:
        try:
            what_the_call_produced.append(the_forced_asking.invoke(the_question))
        except BaseException as refused:
            what_the_call_produced.append(refused)
        finally:
            the_call_is_over.set()

    a_worker = threading.Thread(target=make_the_call, name="a-model-call", daemon=True)
    a_worker.start()

    if not the_call_is_over.wait(how_long_a_call_may_take):
        raise AProviderWouldNotAnswerError(
            TimeoutError(
                f"the model did not answer within {how_long_a_call_may_take:.0f}s. **A gateway "
                "that accepts a connection and stops talking is indistinguishable from one that "
                "is thinking**, and a run waiting for an answer nobody will give it has no grounds "
                "to refuse anything either"
            ),
            None,
        )

    return _the_value_or_the_exception_raised(what_the_call_produced[0])


def _the_value_or_the_exception_raised(
    what_the_call_produced: AnAnswerIsNotYetAnArtifact | BaseException,
) -> AnAnswerIsNotYetAnArtifact:
    """The answer, or the exception the call raised, raised here where the caller expects it.

    **A function rather than a branch at the call site, so the one `raise` of the call's own
    failure is on a line a reader can find.** Raising it on the worker's thread instead would put a
    traceback nobody reads on a thread that dies with the process.
    """
    if isinstance(what_the_call_produced, BaseException):
        raise what_the_call_produced
    return what_the_call_produced


def _the_answer_read_or_the_refusal_raised[Artifact: BaseModel](
    the_forced_asking: Runnable[LanguageModelInput, AnAnswerIsNotYetAnArtifact],
    the_question: LanguageModelInput,
    the_artifact: type[Artifact],
    how_long_a_call_may_take: float = THE_LONGEST_A_CALL_MAY_TAKE,
) -> AnAnswerIsNotYetAnArtifact:
    """The answer as the reader produced it, or this package's refusal saying why there is none.

    **A function and not an inline `try`, because the refusal is raised *around* the call that
    fails** and a lambda's body is one expression. It is re-raised with `raise ... from`, so the
    chain a reader of the trace follows names LangChain rather than stopping here.
    """
    try:
        return _the_answer_or_a_given_up_on(
            the_forced_asking, the_question, how_long_a_call_may_take
        )
    except KeyError as the_reader_hit:
        raise AModelAnsweredInAShapeThisSystemCannotReadError(
            the_reader_hit, the_artifact
        ) from the_reader_hit
    except (ModelError, OutputParserException) as the_provider_refused:
        # **Two names, and neither of them is `Exception`.** The catch above is a `KeyError` alone
        # on purpose, and its docstring gives the reason: a broader catch would convert a bug in a
        # caller's own code into "the model misbehaved", which would send a model to fix something
        # that was never wrong and spend the budget doing it. **These two are the provider's own
        # classes** — checked against the installed versions rather than remembered, and neither is
        # a subclass of `Exception`-but-one:
        #
        # | what arrives | what it is |
        # |---|---|
        # | `ModelError` | the request was refused, or no answer arrived |
        # | `OutputParserException` | an answer named a tool this system never declared |
        #
        # **A `TypeError` in this package still reaches the operator as itself**, which is the whole
        # of what the narrow catch is for.
        raise AProviderWouldNotAnswerError(
            the_provider_refused, the_artifact
        ) from the_provider_refused
