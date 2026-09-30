"""One thing wrong with a repository's security, and everything needed to weigh it.

A finding without its signal is an opinion, and a finding without a false-positive note is a
finding nobody can dismiss. Both are here because the glossary names them: an advisory report
whose every finding is urgent gets read as noise, and the note is what lets a person tell a
real risk from a scanner's guess without re-reading the code.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from aisdlc.agents.severity import Severity

# What a model is asked to name, in the order the model is asked for it. It lives here and
# not in the prompt because a finding's fields are one fact about one type, and a prompt
# listing them separately is a second place to forget one.
THE_FIELDS_A_FINDING_MAY_NAME = (
    "statement",
    "severity",
    "signal",
    "false_positive_notes",
    "recommendation",
)


class SecurityFinding(BaseModel):
    """One finding, in the five things a reader needs before acting on it.

    The shape is closed, and this is the first nested model in the system: a finding crosses
    the model boundary as itself rather than as a dict, because a dict would let a finding
    arrive with any five keys the model felt like sending.

    **`false_positive_notes` is a list because the glossary says "notes".** A real run
    returned two of them for one finding — the lockfile pinning an exact version, and the
    range being a caret on a package with no advisory — and a single string forces a model to
    concatenate what it genuinely found into prose. Two reasons a reader might doubt a
    finding is the most useful thing in an advisory report, and a field that can only hold one
    of them is a field that loses half of what was found.
    """

    model_config = ConfigDict(extra="forbid")

    statement: str
    severity: Severity
    signal: str
    false_positive_notes: list[str]
    recommendation: str

    @field_validator("false_positive_notes", mode="before")
    @classmethod
    def a_note_sent_alone_is_still_a_note(cls, what_the_model_sent: object) -> object:
        """Take a note the model sent as text in the shape it meant, rather than refusing it.

        Two readings, and neither is a relaxation: a string with newlines in it is several
        notes the model wrote as a paragraph, and a string without is one note. Both are what
        the model meant, and the alternative was a run that spent its correction budget on the
        difference — twice, on this field, in two directions.
        """
        if isinstance(what_the_model_sent, str):
            return [line for line in what_the_model_sent.split("\n") if line.strip()]

        return what_the_model_sent
