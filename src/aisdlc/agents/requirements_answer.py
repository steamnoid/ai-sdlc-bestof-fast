"""What the product analyst concluded, in the shape the model is asked to fill.

The artifact is `Requirements` and this is not it. The difference is what the glossary
does not name, which is the whole point of the split: the artifact's fields were fixed by
`docs/domain-glossary.md` and by a person, and a shape the model fills has nowhere to put
anything else. Discovery's answer is closed for the same reason and states it more loudly —
an address is derivable, and a model asked for one will invent it.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from aisdlc.agents.what_an_agent_judged import WhatAnAgentJudged


class WhoCanAnswerThisAmbiguity(StrEnum):
    """The two answers there are, and the whole refusal rests on this one distinction.

    **`a person` and `the repository`, and nothing else.** A question nobody can answer is not a
    category this system has, because it cannot be written down usefully: "we are unsure" is where
    every undetermined thing starts and where a plan cannot be built from.
    """

    A_PERSON = "a person"
    THE_REPOSITORY = "the repository"


class AnAmbiguity(BaseModel):
    """One thing the inspection could not settle, and who can settle it.

    **Attributed and not judged, and that is the whole reason this type is in this shape.** The
    field was `does_it_block_the_work: bool`, and a real model answered it wrongly in *both*
    directions: asked whether a work item three delivered pull requests had proved unplannable
    could be planned, it said no to everything; asked whether a request that names its own test
    file could be planned, it refused twice over — *"the contents of `.gitignore` are not in the
    inspection"* — which is true and not a reason, because the implementer reads the file.

    **Tuning one description to satisfy two opposite tests found whichever one was not being
    run.** So the analyst is asked a question about the *sentence* rather than about the whole
    implementation — *who can answer this* — and the judgement is derived here, deterministically,
    from the answer. The analyst holds the request and the inspection, so it is the only one who can
    make the attribution; nothing downstream has to trust a verdict.

    **The descriptions are the prompt, and a model reads a schema rather than a paragraph.** §0.4
    forbids *begging* — a rule that lives only in prose — and a description of what a field means
    is not a rule: it is the field, and the model is handed it either way. The refusal is what a
    test asserts, and it does.

    **No default on either field.** A default of `the repository` puts the run back where it
    started — tests and no route; a default of `a person` makes it refuse everything; and an
    answer that leaves the question out is a `ValidationError`, which is the only outcome in which
    anybody finds out. A field whose default is an answer turns silence into consent.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    what_is_undetermined: str = Field(
        description=(
            "One sentence naming what the inspection could not settle about the request. A person"
            " must be able to answer it, so name the question rather than the doubt."
        )
    )
    who_can_answer_it: WhoCanAnswerThisAmbiguity = Field(
        description=(
            "Who can settle it. Answer 'the repository' when reading a file in the clone would"
            " settle it. Answer 'a person' only when the repository cannot say which answer was"
            " meant and two people reading it would build different things."
            " -- 'the repository': what .gitignore already covers; which directory a database"
            " file is created in; what an existing test asserts; whether a function is already"
            " exported. 'a person': which mechanism holds the schema version; what the body"
            " shape is; whether 'unauthenticated' means a cookie or a header; whether a health"
            " check queries the database or answers from a constant."
            " The test: could the implementer answer this by opening a file? Then it is"
            " 'the repository', even if this inspection did not happen to include it."
        )
    )

    @property
    def does_it_block_the_work(self) -> bool:
        """Whether a person has to answer before any correct plan can be written.

        **Derived here and not asked of the model**, because this is a rule and not a matter of
        judgement: an ambiguity a person must answer is a wall, and one the repository can answer
        is a note the plan carries. A model asked for a verdict had to reason about the whole
        implementation to produce it, and got it wrong in both directions; asked who can answer,
        it is right.
        """
        return self.who_can_answer_it is WhoCanAnswerThisAmbiguity.A_PERSON


class RequirementsAnswer(BaseModel):
    """The product analyst's conclusion, carrying nothing the glossary did not name.

    **The three artefact fields are the glossary's and nothing else, and the judgement sits
    beside them rather than among them.** An `AnAmbiguity` says who can answer a doubt; this
    says what the analyst concluded and what it could not settle about the work as a whole. A
    reader of the requirements set never sees the second, because a requirement is what a
    person approves and a note is what a person reads afterwards.
    """

    model_config = ConfigDict(extra="forbid")

    requirements: list[str] = []
    acceptance_criteria: list[str] = []
    ambiguities: list[AnAmbiguity] = []
    judged: WhatAnAgentJudged
