"""The request a work item answers, carried as text rather than as a link.

A work item used to name a GitHub issue number and derive an address from the repository,
which is a link to a page that does not exist in the one repository this system has been
pointed at. The number bought nothing: the request's *text* was never carried, so the
product analyst read the repository and proposed requirements about the project, while the
one sentence describing what was actually asked for reached the planner and skipped four
stages in between. A requirement is an answer to a question, and the question was not in
the room.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from aisdlc.domain.the_issue_this_answers import TheIssueThisAnswers


class CommissionedRequest(BaseModel):
    """What somebody asked for, in the words they used.

    **The words first, and the filing beside them rather than instead of them.** The type this
    replaced carried a number and a link derived from `owner/name`, and the link resolved to a page
    that does not exist in the one repository this system has been pointed at. That was the right
    call on what was then known, and **the reason for it is now gone**: `github.read_issue` returns
    the address GitHub itself sent, so the address here is read rather than composed, and a link
    that resolves is a different kind of fact from one that does not.

    **The words are still the point, and the filing is not a substitute for them.** A stage that
    reads the request nine times reads the title and the body nine times; `filed_as` is where a
    reader goes for the rest of a conversation, and it is `None` for the ordinary case of somebody
    saying it out loud.

    **One value and not two, and that is why it is here.** A work item carrying `requested` and a
    separate `answers` took six arguments to build, which is a `PLR0913` on the only way a work
    item is born — and a rule about argument counts is a rule about a shape. The words and where
    they were said are one request, and putting them on one value is what the argument count was
    telling me.

    Frozen for the same reason `WorkItem` is: this is a record of what was asked, and a
    record that can be edited after the fact is a record of something else.
    """

    model_config = ConfigDict(frozen=True)

    title: str
    body: str = ""
    filed_as: TheIssueThisAnswers | None = None

    @field_validator("title")
    @classmethod
    def _reject_a_request_that_says_nothing(cls, title: str) -> str:
        """Refuse a request with no subject, because a card with no title is not a card.

        The body may be empty and the title may not, and the difference is that most requests
        really are one sentence: refusing an empty body would have been tidier to write and
        wrong in the only case that matters, because a model asked for detail it was not given
        invents it. The title is the one field a person reads to know what the work is, and a
        blank one leaves the work with no subject and the run with nothing to be about.
        """
        if not title.strip():
            raise ValueError("a commissioned request must say what was asked for")
        return title

    def where_it_can_be_read(self) -> str | None:
        """The address this request can be read at, or `None` for a request out of a sentence.

        **`None` and never a composed address.** A work item's record is read months later by
        somebody looking for the conversation, and a link shaped like a link that resolves to
        nothing is worse than no link at all — which is why the address here is one GitHub
        returned rather than one assembled from `owner/name` and a number.
        """
        if self.filed_as is None:
            return None
        return self.filed_as.address


def a_request_about(title: str, body: str = "") -> CommissionedRequest:
    """The request as somebody worded it.

    A convenience for the one caller that has a title and nothing else, which is discovery
    naming something it found. It adds no default the type does not already carry.
    """
    return CommissionedRequest(title=title, body=body)
