"""A run's record of what it is doing, on disk, while it is doing it.

A half-hour run that prints its progress to stdout is a half-hour run nobody can see. The
previous heartbeat was `print(..., flush=True)` inside the test, and pytest captures stdout
for the whole duration of a test and only shows it when that test fails — so a run of four
minutes printed nothing, four times, and the operator's log file was zero bytes. A run that
says it is alive and cannot be heard is not a heartbeat.

A file is the fix for both halves of that. It is not captured by anything, and it outlives
the process: a run that is interrupted leaves behind the stage it reached, which is the one
thing worth knowing about a run that stopped.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

WHERE_A_RUNS_RECORD_OF_ITSELF = "progress.txt"


class ARecordOfWhatARunIsDoing(BaseModel):
    """One line per thing the run did, appended as it happens."""

    model_config = ConfigDict(frozen=True)

    where: Path

    def write(self, what: str, elapsed_minutes: float) -> None:
        """Append the line and let it out of the buffer before returning.

        **Appended, because the question a stopped run is asked is "how far did it get"**,
        and a record that overwrites answers "where is it now" and loses the rest. **Flushed,
        because a buffer is the same defect with a delay** — the lines would arrive together
        at the end, or not at all if the process was killed, which is the case this exists for.
        """
        self.where.parent.mkdir(parents=True, exist_ok=True)
        with self.where.open("a") as the_record:
            the_record.write(f"[{elapsed_minutes}m] {what}\n")
            the_record.flush()

    def read(self) -> list[str]:
        """Every line written, or none at all for a run that has not started.

        Empty is a true answer here rather than a missing file: "the run has written nothing"
        and "there is no record" are different facts, and a reader asking what a run did
        deserves to be told the first one without it being an error.
        """
        if not self.where.exists():
            return []
        return self.where.read_text().splitlines()


def a_record_of_what_a_run_is_doing(where: Path) -> ARecordOfWhatARunIsDoing:
    """The record a run keeps at `where`, created when the first line is written."""
    return ARecordOfWhatARunIsDoing(where=where)
