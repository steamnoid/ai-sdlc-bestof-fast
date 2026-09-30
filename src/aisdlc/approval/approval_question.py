"""What the human is asked about, named so nothing crosses the gate as a dict."""

from __future__ import annotations

from pydantic import BaseModel


class ApprovalQuestion(BaseModel):
    """The exact work item, artifact and version a human is being asked to rule on.

    This is what the gate puts in front of somebody, and it names the thing rather
    than carrying it. The artifact's own contents are a separate question, because the
    gate's job is to say precisely what is being approved, and a model that held the
    whole artifact would blur that with the job of showing it.
    """

    work_item_id: str
    artifact_id: str
    artifact_version: int
