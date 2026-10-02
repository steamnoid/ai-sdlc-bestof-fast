# The domain, written down

**This document exists because nine modules say it exists.** `DiscoveryReport`, `Requirements`,
`QaPlan`, `ArchitectureReport`, `SecurityReport`, `ImplementationPlan` and their answer shapes all
open with some version of *"the field names are not chosen here — `docs/domain-glossary.md` fixed
the contents of this artifact"*. Until now that sentence pointed at nothing: there was no `docs/`
directory in this repository at all, so every one of those was a claim about where a decision had
been made with no document behind it.

**It has already cost more than tidiness.** The security analyst cites this file while reasoning,
because the repository's own docstrings point here and an agent reading a repository reads its
docstrings. A citation an agent can follow into nothing makes its answer weaker, not stronger.

**Written from the code, in that order.** The code is the domain written down, and a glossary
invented after the code would be a second place to keep in step — the failure mode this document
exists to prevent. Every field list below is the field list in the module named beside it.

**Checked, not trusted.** `tests/test_the_glossary_blesses_every_term_the_domain_defines.py` reads
the classes out of `src/aisdlc/domain/` and the artifact names out of the `THE_ARTIFACT_*`
constants, and fails if this document does not name them. A term added to the code without an entry
here fails that test on the day it is added.

---

## The work item

A work item is the unit of work. It exists because somebody asked for something to be worked on,
and it is the only thing in the system that moves.

### `WorkItem`

`src/aisdlc/domain/work_item.py`

| field | what it is |
|---|---|
| `work_item_id` | the name nobody has used before, and the only thing that tells one run from another |
| `repository` | the `Repository` being worked on |
| `stage` | where in its life it is — never written by an agent, only by `transition()` |
| `role` | which discipline answers for the result |
| `commissioned_by` | who asked. A person, or a name in the `aisdlc-` namespace if a machine did |
| `agent` | the agent holding it, or `None` |
| `requested` | the `CommissionedRequest` in the words somebody used |
| `work_done` | the `TheWorkEachAgentHasDone` the register carries |

**`commissioned_by` is recorded, never chosen.** No field an agent can write changes which stage a
work item is at, so an agent cannot route work around a gate by setting something.

### `Stage`

`src/aisdlc/domain/stage.py` — `IDLE`, `AWAITING_AGENT_PICKUP`, `IN_PROGRESS_BY_AGENT`,
`AWAITING_HUMAN_APPROVAL`, `READY`, `DONE`.

### `Role`

`src/aisdlc/domain/role.py` — `PO`, `DEV`, `QA`, `SEC`, `ARCH`.

**Who asked and who answers are two questions, so they are two fields.** There is no `AI` role: a
handoff is not a discipline, and a set whose own definition excludes one of its members is not a set
of disciplines.

### `LEGAL_TRANSITIONS`

`src/aisdlc/domain/state_machine.py` — the exhaustive table. `IDLE` → `AWAITING_AGENT_PICKUP`;
`AWAITING_AGENT_PICKUP` → `IN_PROGRESS_BY_AGENT`; `IN_PROGRESS_BY_AGENT` →
`AWAITING_HUMAN_APPROVAL` or `AWAITING_AGENT_PICKUP`; `AWAITING_HUMAN_APPROVAL` →
`AWAITING_AGENT_PICKUP` or `DONE`; `READY` → `AWAITING_AGENT_PICKUP`; `DONE` → nothing.

**Nothing targets `READY`.** Entry is a person's act, which is exactly why no edge leads there.

### `StateMachineError`

`src/aisdlc/domain/state_machine.py` — raised when a work item would break a rule of the state
machine. Named after the rule, not after the mechanism.

### `CommissionedRequest`

`src/aisdlc/domain/commissioned_request.py` — `title`, `body`, and `filed_as` where it was said.

**The words are the point and the filing is not a substitute for them.** `filed_as` is `None` for
the ordinary case of somebody saying it out loud, and a stage reads the title and the body.

### `TheIssueThisAnswers`

`src/aisdlc/domain/the_issue_this_answers.py` — `number` and `address`. The address is the one
GitHub returned rather than one composed from `owner/name`, because a link that resolves is a
different kind of fact from one that does not.

### `TheWorkEachAgentHasDone` and `TheWorkOneAgentHasDone`

`src/aisdlc/domain/the_work_each_agent_has_done.py` — `worked`, a tuple of `agent` and
`how_many_times`. So work already tracked is not proposed again.

### `Repository`

`src/aisdlc/domain/repository.py` — `owner`, `name`, `default_branch`.

### `Approval`

`src/aisdlc/domain/approval.py` — `work_item_id`, `artifact_id`, `artifact_version`, `approved_by`,
`approved_at`, `reason`.

**The record names who decided, verbatim**, and becomes invalid if the artifact it covers changes.
`reason` is required rather than optional because an optional reason is two standards of evidence
in the same table.

---

## The artifacts

**Eight, and each is named by a constant.** The gate rules on these and on nothing else, so a run
cannot produce something nobody was asked about. A refusal ends the run, and a refusal is a
decision rather than a gap.

### `DiscoveryReport`

`src/aisdlc/agents/discovery_report.py` — `languages`, `frameworks`, `build_system`, `ci_system`,
`architecture_summary`, `key_components`, `evidence_files`, `suggested_changes`.

`build_system` and `ci_system` are optional: a tool that failed on a repository without CI would
leave the model with nothing, and a model with nothing guesses. Every path in `evidence_files` is
checked against the clone before the report exists.

### `Requirements`

`src/aisdlc/agents/requirements.py` — `requirements`, `acceptance_criteria`, `ambiguities`.

An ambiguity is something the analyst could not settle. It is rendered into the planner's question
rather than stopping the run: a run that refuses plannable work delivers nothing while every gate
passes.

### `QaPlan`

`src/aisdlc/agents/qa_plan.py` — `test_strategy`, `scenarios`, `edge_cases`, `regression_risks`.

### `ArchitectureReport`

`src/aisdlc/agents/architecture_report.py` — `findings`, `modules`, `dependencies`, `boundaries`,
`risks`.

**At least one field must say something, or this is a fault and not a report.** A repository can be
small enough to have no architectural risk, and the honest report says so rather than inventing a
coupling to describe.

### `SecurityReport`

`src/aisdlc/agents/security_report.py` — `findings`, and `nothing_found_because` when there are
none. A bare list of findings by shape is the one artifact that carries no note, which is why the
supervisor is named for it rather than left to be discovered.

### `ImplementationPlan`

`src/aisdlc/agents/implementation_plan.py` — `files_to_change`, `files_to_add`, `tests_to_add`,
`dependencies`, `migrations`.

`tests_to_add` is separate from `files_to_change` because that is the only thing that knows which
of a change's files are tests; a caller that had to guess would be guessing about a repository's
conventions from a file that has never read them.

### `VerificationReport`

`src/aisdlc/agents/verification_report.py` — `suite_before_the_change` and
`suite_after_the_change`, each a `SuiteOutcome`.

**A red suite is a fact the gate rules on, not a fault the implementer is stopped for.** Nothing is
rolled back, because the first question a person asks of a failing change is which files it
touched, and that question has no answer on a checkout somebody else put back.

### `PullRequestRequest`

`src/aisdlc/agents/pull_request_request.py` — `repository`, `work_item_id`, `branch`, `base`,
`title`, `body`.

### The value types inside them

| term | file | what it is |
|---|---|---|
| `EvidenceFile` | `src/aisdlc/agents/discovery_report.py` | a `path` and the `link` a person would click |
| `SecurityFinding` | `src/aisdlc/agents/security_finding.py` | `statement`, `severity`, `signal`, `false_positive_notes`, `recommendation` |
| `AnAmbiguity` | `src/aisdlc/agents/requirements_answer.py` | `what_is_undetermined` |
| `SuiteOutcome` | `src/aisdlc/tools/run_tests.py` | `exit_code`, `passed`, `dependencies_installed`, `output`, `what_it_collected` |

**`dependencies_installed` is a field and not a convenience.** A suite whose dependencies did not
install has not run, and a report that says it was red when it never started is a lie with a
passing shape.

---

## The agents

Nine, each with an explicit identifier, each producing one artifact.

| identifier | produces |
|---|---|
| `aisdlc-discover` | `DiscoveryReport` |
| `aisdlc-po-analyze` | `Requirements` |
| `aisdlc-qa-analyze` | `QaPlan` |
| `aisdlc-arch-analyze` | `ArchitectureReport` |
| `aisdlc-sec-analyze` | `SecurityReport` |
| `aisdlc-dev-plan` | `ImplementationPlan` |
| `aisdlc-dev-impl` | the change, and `VerificationReport` |
| `aisdlc-repair-supervise` | `WhatToRepeat`, on a refusal a node handed on |
| `aisdlc-pr` | `PullRequestRequest` |

**An agent identifier is `str | None`, never the literal `"none"`**, and `None` means the stage has
no agent rather than that it has an agent called nothing.

**`aisdlc-repair-supervise` judges, and the code routes.** What stage to start again at is the
model's answer; the mapping from that answer to a graph edge is a literal in the code, because a
value read from a model would be a model routing the graph.
