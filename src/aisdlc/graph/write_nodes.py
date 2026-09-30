"""Writing what a run has, at the two moments it becomes worth writing.

The chain says *when*: the report as soon as it exists, because the gate is a suspension
and a run waiting a week for an answer should not be a run whose findings exist only inside
a checkpoint; the summary after the gate answers, because a summary written before the
decision could only say the decision had not been made.

What is written, and to where, is the recorder's business rather than the graph's, and the
graph is given it as a collaborator. A test of the *shape* of a run should not be able to
fail because a directory could not be created, and a graph that reaches the filesystem on
its own makes every one of those tests a test of the filesystem too.

Neither call returns anything into the state. Where a report went is derived from the work
item, so a path in the state would be a second source of a fact that can be computed, and a
second source is a thing that eventually disagrees with the first.
"""

from __future__ import annotations

from collections.abc import Callable

from aisdlc.graph.agent_state import AgentState
from aisdlc.tools.what_a_run_leaves_behind import (
    write_the_approvals,
    write_the_architecture_report,
    write_the_plan,
    write_the_pull_request_request,
    write_the_qa_plan,
    write_the_report,
    write_the_requirements,
    write_the_security_report,
    write_the_summary,
    write_the_verification,
)

Record = Callable[[AgentState], None]


def record_what_this_run_has(state: AgentState) -> None:
    """Write whatever this run has produced so far, into its project directory.

    Called at every point in the chain, so it writes what exists and skips what does not: a
    run at the first gate has a report and no answer, a run at the second has a plan as well,
    and a run that finished has every artifact and every answer. A summary written before the
    first answer could only say there had been none.

    **The approvals are written as their own file, not only named in the summary.** A decision
    that cannot be found later is not a record, it is a claim, and an `Approval` is the one
    thing here that names the exact artifact *and version* it covers and is therefore the
    thing that goes invalid when the artifact moves on. The summary is prose about that; the
    file is the record, and a later stage is entitled to check it rather than re-read a
    paragraph.
    """
    # **No local check for a missing root, and the module it used to have one.** The refusal
    # belongs to `the_project_directory_of`, which every caller of a project directory meets,
    # and a second copy in one caller is a message that names a setting in one place and not in
    # another. The channel is non-optional now, so the branch was dead rather than necessary.
    projects_root = state["projects_root"]

    work_item = state["work_item"]
    report = state["discovery_report"]

    plan = state["implementation_plan"]

    if report is not None:
        write_the_report(report, work_item, projects_root)

    requirements = state["requirements"]

    if requirements is not None:
        write_the_requirements(requirements, work_item, projects_root)

    qa_plan = state["qa_plan"]

    if qa_plan is not None:
        write_the_qa_plan(qa_plan, work_item, projects_root)

    architecture = state["architecture_report"]

    if architecture is not None:
        write_the_architecture_report(architecture, work_item, projects_root)

    security = state["security_report"]

    if security is not None:
        write_the_security_report(security, work_item, projects_root)

    if plan is not None:
        write_the_plan(plan, work_item, projects_root)

    verification = state["verification_report"]

    if verification is not None:
        write_the_verification(verification, work_item, projects_root)

    requested = state["pull_request_request"]

    if requested is not None:
        write_the_pull_request_request(requested, work_item, projects_root)

    if report is None:
        return

    approvals = state["approvals"]

    if approvals:
        write_the_approvals(approvals, work_item, projects_root)

    if state["decisions"]:
        write_the_summary(
            work_item,
            report,
            state["decisions"],
            projects_root,
            state["opened_pull_request"],
        )
