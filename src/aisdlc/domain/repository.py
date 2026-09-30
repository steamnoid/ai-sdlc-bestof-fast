"""The unit of analysis: a public GitHub repository identified by owner and name."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class Repository(BaseModel):
    """A public GitHub repository, named by its owner and its name.

    The system onboards arbitrary public repositories, so this model is built
    from whatever owner and name it is handed and holds no repository of its
    own. Nothing here may be changed after construction: a work item that points
    at a repository must not be able to have its target quietly retargeted.
    """

    model_config = ConfigDict(frozen=True)

    owner: str
    name: str
    default_branch: str = "main"

    @field_validator("owner", "name")
    @classmethod
    def _reject_a_broken_half_of_the_boundary(cls, half: str) -> str:
        """Refuse a half of the `owner/name` boundary that identifies nothing.

        A repository is named by two halves. An empty or whitespace-only half
        names nothing at all, and a half carrying a slash is both halves pasted
        into one field, which would make the boundary ambiguous. Both are refused
        here rather than producing a repository that fails later against GitHub.
        """
        if not half.strip():
            raise ValueError("must not be empty")
        if "/" in half:
            raise ValueError("must be one half of owner/name, not both of them")
        return half

    @property
    def address(self) -> str:
        """`owner/name`, which is what a repository is called when it is written down.

        **One place joins the halves.** A `/` inside a half is refused by the validator
        above precisely so that this cannot produce `a/b/c`, and a caller that assembled
        the string itself would be repeating a rule that already lives here.
        """
        return f"{self.owner}/{self.name}"
