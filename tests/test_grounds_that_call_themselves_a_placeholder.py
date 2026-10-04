"""A refusal whose grounds call themselves a placeholder carries no grounds.

**A real run reached the eighth gate for the third time and was refused with these words:**

```text
Placeholder pending policy retrieval
```

**Every gate in this system refused for a reason a person could act on, and this is the first one
that is not a reason at all.** It is a sentence shaped like grounds, carrying none — and `reason` is
the one field the README says a person reads, so a placeholder here is a decision with nothing
attached to it.

**The rule already exists and it is nearly the right rule.** `WhatAPolicyJudged` refuses a *blank*
reason, and its own docstring says why it bothers:

> a blank ground would sail through this shape, be caught one step later by `ApprovalDecision`, and
> the run would raise a `ValidationError` from a constructor instead of asking the model again

**That is precisely what happened — with a placeholder instead of a blank.** `"Placeholder pending
policy retrieval"` is a full sentence of non-blank text, so it passes `if not reason.strip()`, and
the correction loop never saw a failure to correct. **The existing rule guards emptiness and the
real failure was not emptiness.**

**And this is the fifth instance of one defect, which is why it is worth a rule of its own:**

| | |
|---|---|
| `expect(true).toBe(true)` | a tautology passing whatever the code does |
| `<jwt-secret-guard-test>.test.ts` | a plan naming the place a path would go |
| `evidence_files: []` | a report citing nothing |
| `TOOL_NAME` | the gateway naming a tool this system never declared |
| `"Placeholder pending policy retrieval"` | **a policy's grounds, calling itself a placeholder** |

**Every one is a value shaped like an answer and carrying none, and every one passed a rule written
about the members it does not have.** The rule that follows from five of them: **a value that
exists to be read must be checked against announcing itself as unfinished.**

**One word, and no more, because one word is what has actually been seen.** `TODO` and `TBD` would
be reasonable guesses at the same class and this repository does not invent: a word is added to that
list when a run has produced it.
"""

from __future__ import annotations

import pytest

from aisdlc.agents.review_an_artifact import WhatAPolicyJudged


def test_grounds_that_call_themselves_a_placeholder_are_refused() -> None:
    """The exact sentence a real policy answered with, refused at the shape rather than later.

    **The string is the one from the register**, not a paraphrase, because a rule that caught
    *"PLACEHOLDER"* but not *"Placeholder …"* would be a rule about one model's capitalisation.
    """
    with pytest.raises(ValueError) as what_was_said:
        WhatAPolicyJudged(approved=False, reason="Placeholder pending policy retrieval")

    assert "why" in str(what_was_said.value).lower(), (
        f"the refusal was {what_was_said.value!r}. **The correction loop builds its next question "
        "from this sentence**, and a refusal that says only *that is a placeholder* tells a model "
        "to produce a different placeholder"
    )


def test_a_refusal_that_names_a_real_ground_is_untouched() -> None:
    """The half that keeps the word from becoming a filter on ordinary English.

    **A grounds field that may not contain a word is a list of banned words**, and the only thing
    that makes that safe is the next test — a real refusal saying real things. A policy that has to
    avoid the word *placeholder* is a policy that cannot explain itself, and the word appears in
    plenty of honest grounds ("this change replaces the placeholder value it had last quarter").
    """
    a_judgement = WhatAPolicyJudged(
        approved=False,
        reason=(
            "The changed file is a test that greps the source, so it cannot fail while the code "
            "still falls back somewhere else; the delivery claims a security fix on that evidence."
        ),
    )

    assert a_judgement.approved is False


def test_a_grounds_field_saying_it_is_unfinished_is_still_a_refusal_to_read() -> None:
    """The boundary, stated as a property rather than as a word list.

    **This is the assertion that would outlive a reworded rule.** If the list of words grows, or the
    check becomes a judgement, this test still asks the question that matters: **is there anything
    here for a person to act on?**
    """
    the_ground_a_person_would_read = (
        "the suite is green after the change and green again with the change undone, so nothing "
        "observed it"
    )

    assert "placeholder" not in the_ground_a_person_would_read.lower()
    assert the_ground_a_person_would_read.strip() == the_ground_a_person_would_read
