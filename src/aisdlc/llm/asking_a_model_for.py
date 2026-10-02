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

from typing import TypeVar

from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import BaseModel

Artifact = TypeVar("Artifact", bound=BaseModel)

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

    def __init__(self, what_the_reader_hit: BaseException, the_artifact: type[BaseModel]) -> None:
        """Say which artifact was being read, and what the reader raised saying.

        **The type and the message, and not a paraphrase.** `KeyError('name')` says a field was
        absent and names it; "the parser failed" says neither, and costs the model the one fact it
        could have acted on.
        """
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


def _the_answer_read_or_the_refusal_raised[Artifact: BaseModel](
    the_forced_asking: Runnable[LanguageModelInput, AnAnswerIsNotYetAnArtifact],
    the_question: LanguageModelInput,
    the_artifact: type[Artifact],
) -> AnAnswerIsNotYetAnArtifact:
    """The answer as the reader produced it, or this package's refusal saying why there is none.

    **A function and not an inline `try`, because the refusal is raised *around* the call that
    fails** and a lambda's body is one expression. It is re-raised with `raise ... from`, so the
    chain a reader of the trace follows names LangChain rather than stopping here.
    """
    try:
        return the_forced_asking.invoke(the_question)
    except KeyError as the_reader_hit:
        raise AModelAnsweredInAShapeThisSystemCannotReadError(
            the_reader_hit, the_artifact
        ) from the_reader_hit
