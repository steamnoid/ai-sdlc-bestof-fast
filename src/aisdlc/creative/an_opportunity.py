"""One piece of work a repository could be given, and the files that show it.

**Six fields, all of them required, and a blank in any one is refused.** The field that earns its
keep is `how_it_would_be_known_to_have_worked`: an opportunity with no way of knowing it worked is
a wish, and the work item that comes out of it is a work item whose verification agent is handed
nothing to assert.

**`the_files_that_show_this` is what the model proposes and `evidence_files` is what survived
being proved against the clone.** Two fields, and the split is the point: the report is built from
what a model said, and then every citation in it is checked against the files the clone actually
holds before a person is asked to rule on it. A model once cited a directory that resolved to
nothing, and the link in the report was shaped exactly like a link to a file — so nothing
downstream could tell.

**`the_discipline_that_owns_it` is a word here and a `Role` on the work item.** The analyst is
writing prose for a person, and a work item's role is a field the state machine reads. Turning one
into the other at the moment of filing is where the two meet.

**`the_risk_of_it` is required and is not a weakness.** A card saying *high: touches the
authentication middleware* and a card saying nothing are both proposals, and only one of them lets
a person decide.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from aisdlc.agents.a_value_that_says_something import a_value_that_says_something


class AnOpportunity(BaseModel):
    """A piece of work this repository could be given, and what would show it is worth doing."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    what_could_be_done: str
    why_it_is_worth_doing: str
    the_files_that_show_this: list[str]
    how_it_would_be_known_to_have_worked: str
    the_discipline_that_owns_it: str
    the_risk_of_it: str
    evidence_files: list[str] = []

    @field_validator(
        "what_could_be_done",
        "why_it_is_worth_doing",
        "how_it_would_be_known_to_have_worked",
        "the_discipline_that_owns_it",
        "the_risk_of_it",
    )
    @classmethod
    def _refuse_a_blank(cls, written: str) -> str:
        """Refuse a blank in any of the five sentences.

        **All five, and each one separately.** An opportunity card with a blank on it is a card a
        person rules on and cannot, because the blank is the part that would have told them
        whether the thing was worth doing.
        """
        if not a_value_that_says_something(written):
            raise ValueError(
                "an opportunity says what could be done, why it is worth doing, how you would "
                "know it worked, which discipline owns it and what the risk is. A blank is not a "
                "short answer — it is the part a person is being asked to rule on, so an empty "
                "field here is the absence of the decision rather than a decision to say nothing"
            )
        return written

    @field_validator("the_files_that_show_this")
    @classmethod
    def _refuse_an_opportunity_showing_nothing(cls, showing: list[str]) -> list[str]:
        """Refuse an empty list of files, because an opportunity nothing shows is an opinion.

        This is the field the whole type exists for. A claim of the form *this repository should
        do X* with no file behind it cannot be checked by a person, cannot be checked by the
        citation rule, and cannot be checked by a planner two gates later.
        """
        if not showing:
            raise ValueError(
                "an opportunity names the files that show it is worth doing, and that list is "
                "empty. A claim nobody can open is not a claim, and this one is going to become a "
                "work item a person is asked to rule on"
            )
        return showing

    def in_words(self) -> str:
        """The opportunity as a GitHub issue body, because that is where it is going.

        **Written here and not at the moment of filing,** so what a person reads in the issue and
        what the work item carries as its request are the same sentence. Two renderings of one
        opportunity would be two things that can disagree, and the one a person read on the board
        would not be the one the run worked on.
        """
        return "\n".join(
            [
                f"## {self.what_could_be_done}",
                "",
                "**Why it is worth doing**",
                "",
                self.why_it_is_worth_doing,
                "",
                "**How we would know it worked**",
                "",
                self.how_it_would_be_known_to_have_worked,
                "",
                "**Which discipline owns it**",
                "",
                self.the_discipline_that_owns_it,
                "",
                "**The risk**",
                "",
                self.the_risk_of_it,
                "",
                "**The files that show this**",
                "",
                *[f"- `{a_file}`" for a_file in self.the_files_that_show_this],
            ]
        )
