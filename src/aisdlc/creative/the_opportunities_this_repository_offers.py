"""What a repository could be given, as a person reads it beside the clone.

**An empty list is a result and not a failure, and the report still says what it found.** "This
repository has nothing worth doing" is a true sentence about a repository, and it is the most
useful thing a briefing can conclude. A briefing sent to a repair supervisor for finding nothing
would be a supervisor asked to make work up, and a run that refuses to deliver because a
repository is in good shape is a run that delivers nothing on a repository nobody needs changing.

**Every citation is proved before a person is asked to rule on the report.** The same rule as a
discovery report's evidence and for the same reason — a model once cited a directory that resolved
to nothing, with a link in the report shaped exactly like a link to a file, so nothing downstream
could tell. A refusal carries **all** of the report's citations, because a refusal naming only the
failure produces a second answer naming a different file that also does not exist.

**A class method and not a free function,** so the rule is a property of the artifact: any caller
holding one can ask it to prove itself, and there is no second way to obtain an unproved report.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, model_validator

from aisdlc.agents.a_value_that_says_something import a_value_that_says_something
from aisdlc.agents.what_an_agent_judged import (
    NOTHING_WAS_FOUND,
    NOTHING_WAS_UNSETTLED,
    WhatAnAgentJudged,
)
from aisdlc.creative.an_opportunity import AnOpportunity
from aisdlc.domain.repository import Repository


class AnOpportunityCitingAFileTheCloneDoesNotHoldError(Exception):
    """An opportunity pointed at a path the clone does not have, and nobody was asked about it.

    **Named for what was wrong and not for what was claimed.** "Citing a file the clone does not
    hold" sends a reader to look for the path; "invalid evidence" sends them to the model.
    """

    def __init__(self, cited: str, what_the_clone_holds: Sequence[str], all_of_them: str) -> None:
        """Carry every citation, not only the one that failed.

        A refusal naming only the failure produces a second answer naming a different file that
        also does not exist, and this model has been asked to correct itself before.
        """
        self.cited = cited
        self.what_the_clone_holds = tuple(what_the_clone_holds)
        super().__init__(
            f"this briefing cites {cited!r}, and the clone does not hold it. The clone holds "
            f"{len(self.what_the_clone_holds)} paths and this report cited {all_of_them!r}. A "
            "citation a reader cannot open is not evidence: cite a path the repository actually "
            "has, and if what you found is not in a file at all, leave the opportunity out rather "
            "than pointing at a directory"
        )


class TheOpportunitiesThisRepositoryOffers(BaseModel):
    """What a repository is, what it could be given, and what the briefing could not settle."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    about: Repository
    what_this_repository_is: str
    opportunities: list[AnOpportunity]
    what_the_briefing_could_not_settle: list[str]
    agent_judgement: WhatAnAgentJudged = WhatAnAgentJudged(
        what_it_found=NOTHING_WAS_FOUND,
        what_it_could_not_settle=NOTHING_WAS_UNSETTLED,
        what_it_expects_next="a person picks which of these become issues",
    )

    @model_validator(mode="after")
    def _refuse_a_briefing_that_said_nothing_at_all(self) -> TheOpportunitiesThisRepositoryOffers:
        """Refuse a blank description of the repository.

        **The opportunity list may be empty and the description may not.** An empty list is the
        finding; a blank description is a model that filled a shape without reading anything, and
        the two are indistinguishable from a board unless one of them is refused.
        """
        if not a_value_that_says_something(self.what_this_repository_is):
            raise ValueError(
                "what_this_repository_is is blank. A briefing that proposes nothing is a true "
                "sentence, and a briefing that does not say what the repository *is* is a model "
                "that filled a shape without reading it"
            )
        return self

    def in_words(self) -> str:
        """The report as a person reads it, and it says so when there is nothing to say."""
        if not self.opportunities:
            return (
                f"{self.what_this_repository_is}\n\n"
                "This briefing found nothing worth doing. That is a result, not a failure: a "
                "repository in good shape is a repository nobody needs changing."
            )

        return "\n\n".join(
            [
                self.what_this_repository_is,
                *(an_opportunity.in_words() for an_opportunity in self.opportunities),
            ]
        )

    def how_many_were_proposed(self) -> int:
        """How many the briefing proposed, including the ones a person passed over."""
        return len(self.opportunities)

    @classmethod
    def proving_what_they_cite(
        cls,
        report: TheOpportunitiesThisRepositoryOffers,
        what_the_clone_holds: Sequence[str],
    ) -> TheOpportunitiesThisRepositoryOffers:
        """The report, once every path every opportunity cites is proved to be in the clone.

        **`the_files_that_show_this` is what is checked, and `evidence_files` is what came back.**
        The model writes the first and cannot write the second, which is a field it has no way to
        know the answer to — so checking the second proves nothing at all. This was the shape the
        type arrived in, and it is only right with a node that fills the second from the first;
        without one, a briefing that cited three files the repository does not have passed, and a
        real briefing did exactly that, naming `src/App.jsx` four times in a repository with no
        `src/` at all.

        **Every citation in the report, and not only the first failure.** A model correcting
        itself needs the whole list, and a report where three of five opportunities cite invented
        paths is a different finding from one where a single opportunity does.
        """
        the_paths = set(what_the_clone_holds)
        every_citation = [
            a_file
            for an_opportunity in report.opportunities
            for a_file in an_opportunity.the_files_that_show_this
        ]

        for cited in every_citation:
            if cited not in the_paths:
                raise AnOpportunityCitingAFileTheCloneDoesNotHoldError(
                    cited, what_the_clone_holds, ", ".join(every_citation)
                )

        return report.model_copy(
            update={
                "opportunities": [
                    an_opportunity.model_copy(
                        update={"evidence_files": list(an_opportunity.the_files_that_show_this)}
                    )
                    for an_opportunity in report.opportunities
                ]
            }
        )
