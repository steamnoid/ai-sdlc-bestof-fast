"""Where a request was filed, as the filing itself named it.

**Two fields and not one, because a number is ours and an address is theirs.** An issue that
was transferred answers at an address that does not carry the number asked for, and a value
holding only a number would send a link built from it to a page that is not there — the exact
failure that removed `CommissionedIssue`, and now reversed only because `github.read_issue`
returns the address GitHub sent rather than one assembled from `owner/name`.

**The address is checked for the shape a link has.** The old type's failure was not that it composed
an address; it was that the composed string looked exactly like a link and resolved to nothing. A
string that is not a web address is refused at the boundary rather than carried forward to become a
click that goes nowhere.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TheIssueThisAnswers(BaseModel):
    """A filing, named by the one that received it. See the module's own words."""

    model_config = ConfigDict(frozen=True)

    number: int = Field(ge=1)
    address: str

    @field_validator("address")
    @classmethod
    def _reject_a_string_that_is_not_a_link(cls, address: str) -> str:
        """Refuse a shape that is not a link, because it is carried to become one.

        A relative path is the specific case that matters: `issues/7` is what a composed address
        looks like when it is written by somebody who knows the number and not the host.
        """
        if not address.startswith("https://") and not address.startswith("http://"):
            raise ValueError(
                f"{address!r} is not an address a person can open. A work item's record is read "
                "months later by somebody looking for the request it answers, so a string shaped "
                "like a link and going nowhere is worse than no link at all."
            )
        return address
