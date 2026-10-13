"""A filing a briefing commissioned can be picked up and worked to a pull request.

**The glue of the autonomous loop, and the refusals around it.** A briefing files an issue
and leaves a work item at `READY` carrying GitHub's own number and address. This proves that
such a work item loads back by id, that anything else is refused by name — a sentence-typed
run, an unknown id, an already delivered filing — and that the waiting list holds only filed
work at `READY`. It also proves the delivery body carries `Closes #N`, because a merge that
does not close the issue it answers leaves the loop's last step to a person.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aisdlc.application.a_filing_being_worked import (
    AFiledWorkItemThatIsAlreadyDoneError,
    NotAFiledWorkItemError,
    a_filed_work_item_to_start,
    the_ready_filings,
)
from aisdlc.application.the_runs_this_process_is_holding import TheRunsThisProcessIsHolding
from aisdlc.domain.commissioned_request import CommissionedRequest
from aisdlc.domain.repository import Repository
from aisdlc.domain.role import Role
from aisdlc.domain.stage import Stage
from aisdlc.domain.state_machine import transition
from aisdlc.domain.the_issue_this_answers import TheIssueThisAnswers
from aisdlc.domain.work_item import a_work_item_commissioned_for_an_agent
from aisdlc.graph.deliver_node import _the_lines_of_a_pull_request_body
from aisdlc.store.the_register_of_work_items import NoSuchWorkItemError
from aisdlc.store.what_a_run_records import the_work_item_was_commissioned
from aisdlc.store.where_the_register_lives import holding_the_register, the_register_lives_at
from aisdlc.web.the_api import the_api_over

A_REPOSITORY = Repository(owner="steamnoid", name="wellbeing-tracker-public")


def _a_filed_request(number: int = 41) -> CommissionedRequest:
    return CommissionedRequest(
        title="Replace the ticket-named end-to-end specs",
        body="A check enumerates tests/e2e and fails on any spec whose file name does not match",
        filed_as=TheIssueThisAnswers(
            number=number,
            address=f"https://github.com/steamnoid/wellbeing-tracker-public/issues/{number}",
        ),
    )


def _commission(work_item_id: str, requested) -> object:
    return the_work_item_was_commissioned(
        a_work_item_commissioned_for_an_agent(
            work_item_id=work_item_id,
            repository=A_REPOSITORY,
            accountable_role=Role.DEV,
            commissioned_by="aisdlc-brief",
            requested=requested,
        )
    )


@pytest.fixture
def an_isolated_register(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setenv("AISDLC_PROJECTS_DIR", str(tmp_path / "projects"))
    the_register_lives_at(tmp_path / "the-register.sqlite3")
    return tmp_path


def test_a_filed_work_item_loads_back_by_id(an_isolated_register) -> None:
    _commission("issue-41-replace-the-ticket-named-specs", _a_filed_request(41))

    the_work_item = a_filed_work_item_to_start("issue-41-replace-the-ticket-named-specs")

    assert the_work_item.requested is not None
    assert the_work_item.requested.filed_as is not None
    assert the_work_item.requested.filed_as.number == 41


def test_a_sentence_typed_run_is_not_a_filing(an_isolated_register) -> None:
    from aisdlc.domain.commissioned_request import a_request_about

    _commission("a-sentence-typed-run", a_request_about("add a health endpoint", ""))

    with pytest.raises(NotAFiledWorkItemError):
        a_filed_work_item_to_start("a-sentence-typed-run")


def test_an_unknown_work_item_id_is_unknown(an_isolated_register) -> None:
    with pytest.raises(NoSuchWorkItemError):
        a_filed_work_item_to_start("issue-999-nothing-filed-this")


def test_an_already_delivered_filing_is_not_started_again(an_isolated_register) -> None:
    the_work_item = _commission("issue-41-already-delivered", _a_filed_request(41))

    queued = transition(the_work_item, Stage.AWAITING_AGENT_PICKUP, None, Role.DEV)
    begun = transition(queued, Stage.IN_PROGRESS_BY_AGENT, "aisdlc-dev-impl", Role.DEV)
    handed = transition(begun, Stage.AWAITING_HUMAN_APPROVAL, None, Role.DEV)
    done = transition(handed, Stage.DONE, None, Role.DEV)
    with holding_the_register() as register:
        from aisdlc.store.the_register_of_work_items import the_work_item_is_recorded_at

        the_work_item_is_recorded_at(register, the_work_item, queued)
        the_work_item_is_recorded_at(register, queued, begun)
        the_work_item_is_recorded_at(register, begun, handed)
        the_work_item_is_recorded_at(register, handed, done)

    with pytest.raises(AFiledWorkItemThatIsAlreadyDoneError):
        a_filed_work_item_to_start("issue-41-already-delivered")


def test_the_waiting_list_holds_only_filed_work_at_ready(an_isolated_register) -> None:
    from aisdlc.domain.commissioned_request import a_request_about

    _commission("issue-41-waiting", _a_filed_request(41))
    _commission("a-sentence-waiting", a_request_about("add a health endpoint", ""))
    delivered = _commission("issue-42-delivered", _a_filed_request(42))
    queued = transition(delivered, Stage.AWAITING_AGENT_PICKUP, None, Role.DEV)
    with holding_the_register() as register:
        from aisdlc.store.the_register_of_work_items import the_work_item_is_recorded_at

        the_work_item_is_recorded_at(register, delivered, queued)

    assert [item.work_item_id for item in the_ready_filings()] == ["issue-41-waiting"]


def test_a_filed_delivery_body_closes_the_issue_it_answers() -> None:
    the_work_item = a_work_item_commissioned_for_an_agent(
        work_item_id="issue-41-replace-the-ticket-named-specs",
        repository=A_REPOSITORY,
        accountable_role=Role.DEV,
        commissioned_by="aisdlc-brief",
        requested=_a_filed_request(41),
    )

    the_lines = _the_lines_of_a_pull_request_body(the_work_item)

    assert any("Closes #41" in line for line in the_lines), (
        f"a filed delivery must close its issue on merge, and the body says: {the_lines}"
    )


def test_an_unfiled_run_body_names_no_issue() -> None:
    from aisdlc.domain.commissioned_request import a_request_about

    the_work_item = a_work_item_commissioned_for_an_agent(
        work_item_id="a-sentence-typed-run",
        repository=A_REPOSITORY,
        accountable_role=Role.DEV,
        commissioned_by="a person in a terminal",
        requested=a_request_about("add a health endpoint", ""),
    )

    assert _the_lines_of_a_pull_request_body(the_work_item) == []


def _a_holder_that_refuses_to_build() -> TheRunsThisProcessIsHolding:
    def refusing(source, model=None):
        raise AssertionError("no graph is built on a refusal path")

    return TheRunsThisProcessIsHolding(build_the_graph=refusing)


def test_starting_an_unknown_filing_is_a_404(an_isolated_register) -> None:
    from aisdlc.store.where_the_register_lives import the_register

    with TestClient(the_api_over(the_register(), _a_holder_that_refuses_to_build())) as board:
        answer = board.post("/api/runs/issue-999-nothing-filed-this/start")

    assert answer.status_code == 404, answer.text


def test_starting_a_sentence_run_as_a_filing_is_a_400(an_isolated_register) -> None:
    from aisdlc.domain.commissioned_request import a_request_about
    from aisdlc.store.where_the_register_lives import the_register

    _commission("a-sentence-typed-run", a_request_about("add a health endpoint", ""))

    with TestClient(the_api_over(the_register(), _a_holder_that_refuses_to_build())) as board:
        answer = board.post("/api/runs/a-sentence-typed-run/start")

    assert answer.status_code == 400, answer.text


def test_the_ready_endpoint_lists_a_waiting_filing(an_isolated_register) -> None:
    from aisdlc.store.where_the_register_lives import the_register

    _commission("issue-41-waiting", _a_filed_request(41))

    with TestClient(the_api_over(the_register(), _a_holder_that_refuses_to_build())) as board:
        answer = board.get("/api/filings/ready")

    assert answer.status_code == 200, answer.text
    the_filings = answer.json()["filings"]
    assert [filing["work_item_id"] for filing in the_filings] == ["issue-41-waiting"]
    assert the_filings[0]["issue_number"] == 41
