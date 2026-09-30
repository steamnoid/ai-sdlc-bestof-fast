"""The discipline accountable for a work item. A closed set of five."""

from __future__ import annotations

from enum import Enum


class Role(Enum):
    """The discipline accountable for the work.

    A discipline, and only that. Who asked for the work is a different question in a
    different field, `WorkItem.commissioned_by`, because "a machine was commissioned"
    is not a discipline, and a set whose own definition excludes one of its members is
    not a set of disciplines.

    Removing `AI` from here deleted the transience rule with it, which is the point.
    That rule existed only because `AI` was a role, it was rewritten twice, and it
    spanned ten commits. A special case that exists only to manage a special case is
    better removed than redefined.

    Values are the member names, for the same reason as `Stage`: an integer would be
    opaque in a trace and would renumber if a member were inserted.
    """

    PO = "PO"
    DEV = "DEV"
    QA = "QA"
    SEC = "SEC"
    ARCH = "ARCH"

    def in_words(self) -> str:
        """The discipline spelled out, because a card is read and a routing table is not.

        `PO` is a route segment and `DEV` is a column heading; neither is a word a person
        reading a board would recognise as naming a discipline.
        """
        return _WHAT_EACH_ROLE_IS_CALLED[self]


_WHAT_EACH_ROLE_IS_CALLED = {
    Role.PO: "the product analyst",
    Role.DEV: "the developer",
    Role.QA: "the quality analyst",
    Role.SEC: "the security analyst",
    Role.ARCH: "the architect",
}
