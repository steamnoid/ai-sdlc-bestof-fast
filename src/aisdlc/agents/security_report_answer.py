"""What the security analyst concluded, in the shape the model is asked to fill.

**It is an object holding one named list, and the protocol is why.** A function call's
`arguments` field is a JSON object, so a schema of `type: array` cannot be answered at all: the
model has to wrap it, and a model asked for something impossible does not fail clearly — it
invents `{"items": {"item": [...]}}`. A real run sent that four times and `null` five more, and
each was refused, because nothing was wrong with the reasoning and no answer would ever have
satisfied the shape.

`RootModel` was right when this answer arrived as a message body, where a top-level array is
expressible. Forcing the tool — which is what stopped the model answering in prose and in YAML,
and which this repository now does on every structured question — is what made the bare array
unanswerable. Two fixes that each removed a failure, and the second removed what the first had
been relying on.

**The field is `findings`, and that is not decoration.** `SecurityReport.findings` is the name
the rest of the package uses for the same thing, and one concept has one name. A wrapper called
`root` or `items` would be the same concept under a second name, and a model shown a field
called `root` has nothing to understand it by.

Nothing is loosened to get here: each finding is still validated against a closed
`SecurityFinding`, and `SecurityReport` still refuses a run that found nothing.
"""

from __future__ import annotations

from pydantic import BaseModel, model_validator

from aisdlc.agents.security_finding import SecurityFinding


class SecurityReportAnswer(BaseModel):
    """The security analyst's findings, in the one shape a tool call is able to carry."""

    findings: list[SecurityFinding]

    @model_validator(mode="before")
    @classmethod
    def a_bare_list_is_what_the_model_sent(cls, what_the_model_sent: object) -> object:
        """Accept the findings on their own, because a model demonstrably sends them that way.

        **A model asked to fill an object with one field fills the field**, and two real runs
        answered `Input should be an object [input_value=[{'statement': '...'}]]` — a JSON
        array where an object was asked for. That is the opposite failure from the one the
        object shape exists to answer, and both are real, so this node reads either rather than
        picking the one it would prefer.

        The alternative is refusing a correct set of findings over its packaging, and a refusal
        here costs a correction and, on a flaky gateway, several.
        """
        if isinstance(what_the_model_sent, list):
            return {"findings": what_the_model_sent}

        return what_the_model_sent
