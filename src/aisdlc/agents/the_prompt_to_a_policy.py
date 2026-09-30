"""What a policy is asked when it stands in for a person at the gate.

**The question is the one a person is asked, and it is deliberately not a yes/no question.**
`ApprovalDecision.approved` is a boolean and it is tempting to ask the model for one, but a
boolean with no grounds is a coin flip written down, and this gate is the last place a coin flip
belongs. So the model is asked to rule and to give the grounds, in one answer, and the grounds
are what the record keeps.

**The whole artifact goes in, verbatim.** Not a summary, not the fields a parser thought were
important. A person opening this file sees everything in it, and a policy that saw less would be
approving something nobody showed it — which is the failure this whole mechanism is arranged to
prevent, arrived at from the other direction.

**The version is named, because a decision is about one version or about nothing.** The gate
records the version it presented; a policy that answered about a different one would be approving
something the approval does not cover.
"""

from __future__ import annotations

from pathlib import Path

from aisdlc.approval.approval_gate import THE_POLICY_NAMESPACE
from aisdlc.approval.approval_question import ApprovalQuestion

# The agent that asks, named so the prompt's author is visible in the model trace.
THE_AGENT_THAT_REVIEWS = "aisdlc-policy-review"


def the_prompt_to_a_policy(
    question: ApprovalQuestion, what_the_run_produced: str, where_it_was_read_from: Path
) -> str:
    """The whole artifact, the exact version, and a question that asks for grounds.

    **`what_the_run_produced` is the file's own text rather than a model dump**, so the policy
    reads what a person opening the same path would read. A policy handed a re-serialised model
    could approve a document the gate never offered.
    """
    return f"""\
You are standing in for a person who reviews a {question.artifact_id} before this run continues.

The exact thing you are ruling on:
  work item:  {question.work_item_id}
  artifact:   {question.artifact_id}
  version:    {question.artifact_version}
  read from:  {where_it_was_read_from}

The artifact, exactly as the run wrote it:

{what_the_run_produced}

Rule on it. Answer with:
  approved — true if this run may continue, false if it may not;
  reason   — the grounds, in one or two sentences, naming what you actually looked at.

A refusal is a decision and is recorded as one. If you refuse, say what is wrong in terms the
person who commissioned this work could act on — not "this is insufficient" but the specific
thing that is missing, wrong, or unsupported by what is above.

Your answer is recorded as `{THE_POLICY_NAMESPACE}<the policy's name>`. A record naming a person
for a judgement a model made would be false, so it will not name one."""
