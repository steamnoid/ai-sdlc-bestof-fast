"""What a run leaves in its project directory: the artifact, and a summary to read.

Two promises from "The project directory" in `AGENTS.md` are kept here, and the second
one is a security-shaped promise about this module rather than about its caller.

**Nothing of ours goes into the clone.** The clone is somebody else's repository and has
to stay a faithful checkout of it, so the artifact is a *sibling* of the clone rather than
a file in its working tree. The test asks git about the tree instead of trusting the
layout, because a run that wrote its report into the working tree would leave a repository
that is not the repository — and the diff that decides what a pull request contains would
be a diff of our own files.

**The summary is written from the run, not by a model.** This module may not import a
model factory, and a test reads its imports to hold that. A summary that flatters the run
it describes is worse than no summary, because it is the first thing a person reads, and
the one artifact whose whole job is to be believed.

A summary is not a log. It carries the work item, the issue it answers, the artifacts with
the links a person would click, and **every** gate with who decided it — because a decision
that cannot be found later is not a record, it is a claim. Every gate, and each named by the
decision that was about it: a run is walked through several, and a verdict attributed to the
wrong artifact is a worse record than a missing one.
"""

from __future__ import annotations

import json
from pathlib import Path

from aisdlc.agents.architecture_report import ArchitectureReport
from aisdlc.agents.discovery_report import DiscoveryReport
from aisdlc.agents.implementation_plan import ImplementationPlan
from aisdlc.agents.pull_request_request import PullRequestRequest
from aisdlc.agents.qa_plan import QaPlan
from aisdlc.agents.requirements import Requirements
from aisdlc.agents.security_report import SecurityReport
from aisdlc.agents.verification_report import VerificationReport
from aisdlc.approval.approval_decision import ApprovalDecision
from aisdlc.domain.approval import Approval
from aisdlc.domain.work_item import WorkItem
from aisdlc.store.what_a_run_records import the_artifact_was_recorded
from aisdlc.tools.github_create_pull_request import AnOpenedPullRequest
from aisdlc.tools.the_project_directory import the_project_directory_of

A_FILE_EXTENSION_A_PERSON_CAN_READ = ".json"

# **Named after the run's own state, and not after the stage it stopped in.** A person goes to the
# project directory to find out what happened, and "why it stopped" is the question they arrive
# with; a name carrying a stage number would be a name they have to guess at.
WHERE_A_RUN_WROTE_WHY_IT_STOPPED = "what-this-run-stopped-to-ask.md"


# Every artifact a run files beside its clone, in the pipeline's order. **One name and not
# seven in a signature**, because a signature listing the pipeline's artifacts is a second
# place to forget one — and a forgotten artifact is a file no gate names and no person can
# look up, which is §34's "an artifact that is not persisted does not exist" arriving quietly.
# It grows with the glossary's artifacts table, and the readability guard for that table does
# not read this line, so a reviewer is what keeps the two in step — **and a reviewer is what let
# the eighth go missing.** A run committed, pushed, opened a pull request and left no
# `PullRequestRequest.json`, and the run *succeeded*, because every signal a run gives says
# success. The comment above already said what a forgotten artifact is; this line is where the
# forgetting happened.
type AnArtifactARunFiles = (
    DiscoveryReport
    | Requirements
    | QaPlan
    | ArchitectureReport
    | SecurityReport
    | ImplementationPlan
    | VerificationReport
    | PullRequestRequest
)
NO_DECISION_RECORDED_YET = "No decision recorded yet"


def write_the_report(
    report: DiscoveryReport, work_item: WorkItem, projects_root: Path
) -> Path:
    """The report on disk, beside the clone and not inside it.

    Named after the artifact rather than after a stage, because the artifact is the
    contract: `DiscoveryReport` is what the glossary says this agent produces and what an
    approval names, and a file called `stage-two.json` would be a name nobody can look up.
    """
    return _an_artifact_written_beside_the_clone(report, work_item, projects_root)


def write_the_plan(
    plan: ImplementationPlan, work_item: WorkItem, projects_root: Path
) -> Path:
    """The plan on disk, beside the clone and not inside it.

    A function of its own rather than a second call to `write_the_report`, so a reader is not
    left deciding whether a plan is a kind of report. It is not: the glossary lists the two
    artifacts separately, with different producers and different contents.
    """
    return _an_artifact_written_beside_the_clone(plan, work_item, projects_root)


def write_the_verification(
    verification: VerificationReport, work_item: WorkItem, projects_root: Path
) -> Path:
    """The verification on disk, beside the clone and not inside it.

    A function of its own for the same reason as the plan's: the glossary lists three artifacts
    with three producers, and a caller that had to know which two were "the report" would be
    holding a rule about types rather than about where things go.
    """
    return _an_artifact_written_beside_the_clone(verification, work_item, projects_root)


def write_the_requirements(
    requirements: Requirements, work_item: WorkItem, projects_root: Path
) -> Path:
    """The proposal on disk, beside the clone and not inside it.

    A function of its own for the reason the plan's and the verification's are: the glossary
    lists each artifact separately, with its own producer and its own contents, so a caller
    that had to know which two of them were "the report" would be holding a rule about types
    rather than about where things go.

    **A person approves this file.** The gate presents an artifact by name and version, and a
    run that asked somebody to rule on a proposal it never wrote down would be asking a person
    to approve a paragraph they can only see if they read a trace.
    """
    return _an_artifact_written_beside_the_clone(requirements, work_item, projects_root)


def write_the_qa_plan(qa_plan: QaPlan, work_item: WorkItem, projects_root: Path) -> Path:
    """The QA plan on disk, for the same reason the proposal's is written.

    The first of the four that is *not* about the repository, and the first a person is
    approving something that does not exist yet — a shape of testing rather than a description
    of code. Which is exactly why it has to be on disk before anybody rules on it.
    """
    return _an_artifact_written_beside_the_clone(qa_plan, work_item, projects_root)


def write_the_architecture_report(
    architecture_report: ArchitectureReport, work_item: WorkItem, projects_root: Path
) -> Path:
    """The architecture report on disk, for the same reason the proposal's is written."""
    return _an_artifact_written_beside_the_clone(
        architecture_report, work_item, projects_root
    )


def write_the_security_report(
    security_report: SecurityReport, work_item: WorkItem, projects_root: Path
) -> Path:
    """The security report on disk, for the same reason the proposal's is written.

    **The one whose absence is most dangerous**, and not only because it is the last gate: a
    run that found no risk wrote no file, and a reader looking for `SecurityReport.json` later
    cannot tell that from a run that never looked. Writing it even when it says little is what
    makes the difference visible.
    """
    return _an_artifact_written_beside_the_clone(security_report, work_item, projects_root)


def write_the_pull_request_request(
    requested: PullRequestRequest, work_item: WorkItem, projects_root: Path
) -> Path:
    """The pull request this run asked for, on disk, for the same reason the other seven are.

    **It was the only artifact with no writer, and a real run proved what that costs.** A run
    committed, pushed, and opened a pull request on the upstream repository — and left no
    `PullRequestRequest.json` beside the clone. The run *succeeded*: nothing failed, nothing was
    refused, and the delivery was real. What was missing is the record, which is the one thing
    this directory exists to be.

    A gap of that shape is invisible from the outside, because every signal a run gives says
    success. A reader opening the directory sees seven gates approved and no trace of the
    eighth, and the eighth is the artifact a person **approved** — the decision exists in
    `Approvals.json` and names something nobody can open.
    """
    return _an_artifact_written_beside_the_clone(requested, work_item, projects_root)


def _an_artifact_written_beside_the_clone(
    artifact: AnArtifactARunFiles,
    work_item: WorkItem,
    projects_root: Path,
) -> Path:
    """One artifact, named after its own class, in the run's project directory.

    The name comes from the artifact rather than from an argument, so a caller cannot file a
    plan under the report's name and a gate that names `ImplementationReport` would be a gate
    nobody could find. Two artifacts with one writer, and the writer has no opinion about
    either of them beyond where they go.

    **The same value is announced to the register**, so the run's story says what exists without
    anything having to go and look in the directory. A board showing a run that has written four
    artifacts and saying nothing about them is a board that has made a reader go and count files.
    """
    project = the_project_directory_of(work_item, projects_root)
    where = project / f"{artifact.__class__.__name__}{A_FILE_EXTENSION_A_PERSON_CAN_READ}"

    project.mkdir(parents=True, exist_ok=True)
    where.write_text(
        json.dumps(artifact.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    the_artifact_was_recorded(work_item, artifact.__class__.__name__)

    return where


def the_summary_of(
    work_item: WorkItem,
    report: DiscoveryReport,
    decisions: list[ApprovalDecision],
    opened_pull_request: AnOpenedPullRequest | None = None,
) -> str:
    """The run in one page: what it worked on, what it found, and who decided what.

    Written from the run's own state, in that order, because that is the order a person
    asks about it: which issue, what is it, what did you conclude, who said yes to each.

    **Every gate, and each one named by the decision that was about it.** `AGENTS.md` promises
    the summary carries *every* approval with who decided, and a run is walked through three
    gates. Reading the last answer alone produced a record that said
    ``DiscoveryReport` version 1 was approved by `autopilot:approve-verificationreport`` —
    the verdict of one gate attributed to another gate's artifact, which is worse than an
    absence, because an absence announces itself and that did not.

    A decision carries the artifact, the version, the verdict, who and when, so a table built
    from decisions cannot mispair them. An `Approval` carries no verdict at all — it exists
    only for an affirmative answer — so a record built from approvals could not show a refusal.
    The decisions are what this file reads; the approvals are written beside it.
    """
    repository = work_item.repository
    request = work_item.requested

    lines = [
        f"# {work_item.work_item_id}",
        "",
        f"Repository: {repository.owner}/{repository.name}",
    ]

    if request is None:
        lines.append("Requested: none — this work was commissioned without a request.")
    else:
        lines.append(f"Requested: {request.title}")
        if request.body:
            lines += ["", request.body]

    lines += [
        "",
        f"## {report.__class__.__name__}",
        "",
        f"Languages: {', '.join(report.languages) if report.languages else 'none named'}",
        f"Build system: {report.build_system or 'none found'}",
        f"CI: {report.ci_system or 'none found'}",
        "",
        report.architecture_summary,
        "",
        "### Evidence",
        "",
    ]

    for evidence in report.evidence_files:
        lines.append(f"- [{evidence.path}]({evidence.link})")

    lines += _the_gates_section(decisions)

    if opened_pull_request is None:
        lines += [
            "",
            "## Pull request",
            "",
            "None opened — this run has not delivered anything.",
        ]
    else:
        lines += [
            "",
            "## Pull request",
            "",
            f"#{opened_pull_request.number}: {opened_pull_request.address}",
        ]

    return "\n".join(lines) + "\n"


def _the_gates_section(decisions: list[ApprovalDecision]) -> list[str]:
    """Every gate this run was walked through, in the order it was walked, as a table.

    A table rather than a paragraph, because a run with eight gates is a list and a list a
    person checks against their own memory reads worse as prose. Each row's artifact name
    comes from the decision in that row, so a verdict cannot be attributed to a gate it was
    not about.

    Silence stays readable. A run that has not reached a gate has no decision to show, and
    saying so is the difference between a record that admits what it does not know and one
    that lets a reader assume the rest was fine.
    """
    if not decisions:
        return ["", "## Gates", "", NO_DECISION_RECORDED_YET]

    lines = [
        "",
        "## Gates",
        "",
        "| Artifact | Version | Decision | Decided by | When | Why |",
        "|---|---|---|---|---|---|",
    ]

    for decision in decisions:
        verdict = "approved" if decision.approved else "refused"
        lines.append(
            f"| `{decision.artifact_id}` | {decision.artifact_version} | {verdict} | "
            f"`{decision.decided_by}` | {decision.decided_at.isoformat()} | "
            f"{decision.reason} |"
        )

    return lines


THE_RECORD_OF_EVERY_APPROVAL = "Approvals"


def write_the_approvals(
    approvals: list[Approval], work_item: WorkItem, projects_root: Path
) -> Path:
    """Every approval this run earned, on disk, beside the clone and not inside it.

    Not the summary's business, and that is why it is its own file. A decision that cannot be
    found later is not a record, it is a claim, and an `Approval` is the one thing here that
    names the exact artifact **and version** it covers — the thing that goes invalid when the
    artifact moves on. The summary is prose about that; this is the record, and a later stage
    is entitled to check it rather than re-read a paragraph.
    """
    project = the_project_directory_of(work_item, projects_root)
    where = project / f"{THE_RECORD_OF_EVERY_APPROVAL}{A_FILE_EXTENSION_A_PERSON_CAN_READ}"

    project.mkdir(parents=True, exist_ok=True)
    where.write_text(
        json.dumps([approval.model_dump(mode="json") for approval in approvals], indent=2),
        encoding="utf-8",
    )

    return where


def write_why_this_run_stopped(
    work_item: WorkItem, projects_root: Path, why_it_stopped: str
) -> Path:
    """Why this run stopped, on disk, where a person goes to find it.

    **A run that refuses to deliver has no pull request, no branch and no summary**, so a person
    who walked away from it has a clone on disk and no way of learning that it stopped rather
    than finished. **This is what a decision that cannot be found later looks like when it is not
    found at all**, and the refusal text is the only place it exists.

    **The words are the refusal's, and not a rendering of it.** Whoever refused said what the
    suite said and what the exit code was, and a second wording beside it would be a second claim
    about the same stop.

    **Written before the refusal goes any further**, because after it the run has no more code to
    reach, and an exception is not a record.
    """
    project = the_project_directory_of(work_item, projects_root)
    where = project / WHERE_A_RUN_WROTE_WHY_IT_STOPPED

    project.mkdir(parents=True, exist_ok=True)
    where.write_text(
        f"# This run stopped and did not deliver\n\n"
        f"Work item: {work_item.work_item_id}\n"
        f"Repository: {work_item.repository.owner}/{work_item.repository.name}\n\n"
        f"{why_it_stopped}\n",
        encoding="utf-8",
    )

    return where


def write_the_summary(
    work_item: WorkItem,
    report: DiscoveryReport,
    decisions: list[ApprovalDecision],
    projects_root: Path,
    opened_pull_request: AnOpenedPullRequest | None = None,
) -> Path:
    """The summary on disk, in the project directory beside the clone."""
    project = the_project_directory_of(work_item, projects_root)
    where = project / "summary.md"

    project.mkdir(parents=True, exist_ok=True)
    where.write_text(
        the_summary_of(work_item, report, decisions, opened_pull_request),
        encoding="utf-8",
    )

    return where
