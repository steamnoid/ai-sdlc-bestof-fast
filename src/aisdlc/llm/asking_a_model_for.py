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
from langchain_core.runnables import Runnable
from pydantic import BaseModel

Artifact = TypeVar("Artifact", bound=BaseModel)

AnAnswerIsNotYetAnArtifact = dict[str, object] | BaseModel


def ask_a_model_for[Artifact: BaseModel](
    the_model: BaseChatModel, the_artifact: type[Artifact]
) -> Runnable[LanguageModelInput, AnAnswerIsNotYetAnArtifact]:
    """The model, bound to a tool it is not allowed to answer without.

    **The answer is not typed as the artifact, and the name says why.** Nothing guarantees the
    model honoured the tool, so what comes back is data until something validates it, and every
    caller does that itself. Naming the type `AnAnswerIsNotYetAnArtifact` is what stops a reader
    from treating a returned dictionary as a plan.
    """
    return the_model.with_structured_output(
        the_artifact,
        method="function_calling",
        tool_choice=the_artifact.__name__,
    )
