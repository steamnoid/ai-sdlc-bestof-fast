"""Grounds that narrate reviewing instead of ruling carry no grounds.

**A real run worked thirty minutes to its first gate and was refused with these words:**

```text
Reviewing the DiscoveryReport before ruling.
```

**The report was good.** Twenty-two evidence files, every one a file of the clone, the
placeholder test this run answers named among them, and its first suggested change is the
very issue the run was commissioned for. So the refusal says nothing about the report — and
it says nothing else either. It narrates the act of reviewing and defers the ruling the
field exists to give, which ended the run on a verdict nobody can argue with because there
is nothing in it.

**The sixth instance of one defect.** A value shaped like an answer and carrying none —
`expect(true).toBe(true)`, `<…>` as a filename, `evidence_files: []`, the gateway's
`TOOL_NAME`, `"Placeholder pending policy retrieval"`, and now this. The rule that
generalises is the same: **a value that exists to be read must be checked against announcing
itself as unfinished.**

**The match is the whole reason and not words inside it.** Honest grounds may well say they
reviewed something — *"after reviewing the report I refuse, because…"* — and a rule matching
*reviewing* anywhere would be a list of banned words stopping a policy explaining itself.
What is refused is a reason that *is* the deferral and nothing else, so the correction loop
sees the failure and asks again instead of recording a verdict nobody gave.
"""

from __future__ import annotations

import pytest

from aisdlc.agents.review_an_artifact import WhatAPolicyJudged


def test_grounds_that_defer_the_ruling_are_refused() -> None:
    """The exact sentence a real policy answered with, refused at the shape rather than later.

    **The string is the one from the register**, not a paraphrase, because a rule that caught
    one model's capitalisation but not its sentence would be a rule about the capitalisation.
    """
    with pytest.raises(ValueError) as what_was_said:
        WhatAPolicyJudged(
            approved=False, reason="Reviewing the DiscoveryReport before ruling."
        )

    assert "say what" in str(what_was_said.value).lower(), (
        f"the refusal was {what_was_said.value!r}. **The correction loop builds its next "
        "question from this sentence**, and a refusal that says only *that is deferred* tells "
        "a model to produce a different deferral"
    )


def test_grounds_that_say_they_reviewed_something_are_untouched() -> None:
    """The half that keeps the shape from becoming a filter on ordinary English.

    **A refusal that reviewed and then ruled is the ordinary case**, and the word *reviewing*
    appears in plenty of honest grounds. What is refused is a reason that is nothing but the
    deferral — so a refusal carrying a finding alongside the review must pass untouched.
    """
    a_judgement = WhatAPolicyJudged(
        approved=False,
        reason=(
            "After reviewing the DiscoveryReport I refuse: it lists fourteen source files it "
            "did not show, and the architecture summary reasons from their names; show the "
            "files or drop the claims."
        ),
    )

    assert a_judgement.approved is False


def test_an_approval_saying_what_it_checked_is_untouched() -> None:
    """The other side of the same boundary: an approval is not a deferral either.

    **Past tense and a finding, rather than a narration of work in progress.** A rule that
    refused this would refuse approvals for saying what they did, which is the one thing an
    approval is for.
    """
    a_judgement = WhatAPolicyJudged(
        approved=True,
        reason=(
            "Reviewed the DiscoveryReport against the clone: every cited file exists, the "
            "summary matches the inspection, and the first suggested change is the issue "
            "this run answers."
        ),
    )

    assert a_judgement.approved is True
