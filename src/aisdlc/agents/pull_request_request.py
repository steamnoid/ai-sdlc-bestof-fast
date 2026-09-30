"""The pull request a run will ask for, which is a request and not a step."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from aisdlc.domain.repository import Repository


class PullRequestRequest(BaseModel):
    """What a person rules on before a pull request exists.

    **A request, not an opened pull request.** The gate presents this; a number and an
    address only exist after a person has approved it, and a type that carried both would
    make an artifact whose contents are not yet true presentable as though they were.

    **Nothing here has reached the remote.** The branch is named but not pushed, and the
    pull request is described but not opened. That order is the rule: a branch on somebody's
    fork and a pull request on somebody's repository are both things a human did not ask for
    until a human approved this.
    """

    model_config = ConfigDict(frozen=True)

    repository: Repository
    work_item_id: str
    branch: str
    base: str
    title: str
    body: str

    @field_validator("title")
    @classmethod
    def _reject_a_title_that_says_nothing(cls, title: str) -> str:
        """A title is what a reviewer reads in a list of forty, so it has to say what this is."""
        if not title.strip():
            raise ValueError("a pull request must say what the pull request is about")
        return title

    @field_validator("body")
    @classmethod
    def _reject_a_body_that_says_nothing(cls, body: str) -> str:
        """The body says what was changed and what was verified.

        This is the field a reviewer reads to decide whether the change was checked, so an
        empty one presents a change as though nobody had looked at it — which, for a change
        this system verified by running the repository's own suite on both sides, is the one
        thing worth refusing rather than defaulting.
        """
        if not body.strip():
            raise ValueError("a pull request must say what was changed and what was verified")
        return body

    @field_validator("base")
    @classmethod
    def _reject_a_base_that_is_nobody(cls, base: str) -> str:
        """A pull request joins something. Joining nothing opens against the default branch."""
        if not base.strip():
            raise ValueError("a pull request must say which branch it joins")
        return base
