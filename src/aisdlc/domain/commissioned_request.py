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
        return _a_title_a_reader_and_a_platform_can_both_hold(title)

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


# **GitHub's own number, and it is here rather than in the delivery because three producers write
# this field and only one of them is a delivery.** A run's first sentence, a briefing's filing, and
# a model's proposal all become `title`, and all three end up as an issue title, a branch name and a
# pull request title. **A bound in the delivery would leave the other two unbounded**, which is the
# same mistake as a rule that only the caller enforces.
THE_LONGEST_TITLE_GITHUB_ACCEPTS = 256


def _a_title_a_reader_and_a_platform_can_both_hold(title: str) -> str:
    """The title, cut to what GitHub accepts and cut where a person would have cut it.

    **A real run built a title of 2472 characters and discovered it at the last node.**
    `PullRequestNotOpenedError` said `Validation Failed; title is too long (maximum is 256
    characters)` — after eight gates approved, three container suite runs and a policy ruling on
    every artifact. **The same string was the branch name too**, so its length was on screen for
    six stages and only the platform noticed it at the end, which is the worst place and the only
    one anybody was checking.

    **Cut and not refused.** A person who explains themselves at length has said something worth
    reading, and this field appears in a list of forty. **Refusing the run over it would be a
    punishment for good manners** — and `a_request_about` puts the whole argument in `title` and
    leaves `body` empty, so a long request becomes a long title with nothing behind it.

    **Nothing is *kept* elsewhere: the text that did not fit is dropped, and that is the honest
    cost of this rule.**
    and it is the price of a run that delivers at all rather than a run that refuses over a title.
    The alternative — refusing — throws away eight gates of work instead, which is worse and would
    have been thrown away by a person whose sentence was merely thorough.

    **Cut at the last space before the bound, and not at the bound itself**, because a title is
    filled from the front and the tail is what is lost. **Ending mid-word would read as a defect**,
    and a title is now permanent in a public repository.
    """
    if len(title) <= THE_LONGEST_TITLE_GITHUB_ACCEPTS:
        return title

    the_room_left = THE_LONGEST_TITLE_GITHUB_ACCEPTS
    the_last_space_before_it = title.rfind(" ", 0, the_room_left)
    if the_last_space_before_it < 1:
        # **One word longer than the bound, and there is no space to cut at.** A title of a single
        # 300-character token is a name rather than a sentence, and cutting inside it would produce
        # a name that matches no file and no issue. Refusing the uncuttable case is better than
        # inventing a word.
        raise ValueError(
            f"the request's first {the_room_left} characters are one word with no space "
            "in it, so "
            "it cannot be shortened to a title. A title is for reading in a list; this is a name."
        )
    return title[:the_last_space_before_it].rstrip()


def a_request_about(title: str, body: str = "") -> CommissionedRequest:
    """The request as somebody worded it.

    A convenience for the one caller that has a title and nothing else, which is discovery
    naming something it found. It adds no default the type does not already carry.
    """
    return CommissionedRequest(title=title, body=body)
