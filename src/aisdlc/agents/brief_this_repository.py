"""A repository briefs itself: what work could it be given, and which files show it.

**This is the other half of the product, and it is the half a sentence cannot reach.** Every
other agent in this system answers a question a person asked — *add a health endpoint*, *check
this for security risk* — and each one is told what to look at. This one is handed a repository
and asked what it should be given, which is a different kind of question: the answer is not
derived from anything the deployment said, and a model that is not shown the repository's own
files will invent work.

**Which is why every opportunity has to name files, and why those files are proved before a
person is asked to rule on the briefing.** `AnOpportunity` refuses an empty citation list, and
`proving_what_they_cite` checks every one of them against the files the clone actually holds. The
second rule is the one this repository learned the hard way — a security report reasoning from
filenames reached a gate and was refused, and the reason it could reason from filenames is the
same reason this has to check: nothing had told the model which files it had been shown.

**The inspection is the one the security analyst gets, and the reason is the same.** A briefing
that proposes "add rate limiting to the event endpoint" is a proposal about code, and a model
proposing it from a directory listing and a `package.json` is proposing it from filenames. The
inspection ends by naming what it withheld, and this prompt says so too — twice, in two
registers, because the one a reader of the resulting issue can check is the rule worth having.

**An empty list is a result.** A repository in good shape has nothing worth doing, and a
briefing that says so is the most useful thing it can conclude. It is not a fault, it is not
routed to a repair supervisor, and it is not an excuse to invent three opportunities so the
board is not empty.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import ValidationError

from aisdlc.creative.the_opportunities_this_repository_offers import (
    AnOpportunityCitingAFileTheCloneDoesNotHoldError,
    TheOpportunitiesThisRepositoryOffers,
)
from aisdlc.domain.commissioned_request import CommissionedRequest
from aisdlc.domain.repository import Repository
from aisdlc.llm.asking_a_model_for import (
    AModelAnsweredInAShapeThisSystemCannotReadError,
    ask_a_model_for,
)
from aisdlc.llm.correction_budget import (
    how_a_model_is_told_what_was_wrong,
    may_this_run_keep_asking,
)
from aisdlc.tools.github_clone_repository import ClonedRepository, RepositoryToClone
from aisdlc.tools.github_list_open_issues import AnOpenIssue
from aisdlc.tools.inspect_the_repository import an_inspection_of_the_code

# What a model is asked for, and what the answer is validated into. Two names rather than one
# because the first is a shape the model fills and the second is the artifact a person rules on —
# and the difference is the citation list, which the node proves and the model does not.
_BRIEFING = "TheOpportunitiesThisRepositoryOffers"

WHAT_EACH_OPPORTUNITY_MAY_NAME = (
    "what_could_be_done",
    "why_it_is_worth_doing",
    "the_files_that_show_this",
    "how_it_would_be_known_to_have_worked",
    "the_discipline_that_owns_it",
    "the_risk_of_it",
)

WHAT_IS_ASKED_FOR_HERE = (
    "a briefing",
    "what work this repository could be given",
)


def _what_is_already_tracked_says(what_is_already_tracked: Sequence[AnOpenIssue]) -> str:
    """The list of open issues the briefing is shown, and what it is told to do about them.

    **The list is here because proposing work a team has already agreed to do is the most
    likely wrong answer this node can give**, and a model told to "propose work" proposes work
    it knows about — it is a retrieval task and it recalls a different project. Listing what is
    open turns it into a lookup.

    **And the list is not what stops it.** Filing refuses a duplicate before anything is opened,
    in `filing_what_the_briefing_found`, because a prompt is not a check. This section exists to
    make duplication unlikely; the refusal exists to make it not happen.

    **A repository with no open issues says so in one line**, rather than saying nothing. "Nobody
    has filed anything" and "you were not shown anything" read identically to a model, and only
    one of them is true.
    """
    if not what_is_already_tracked:
        return (
            "\nNobody has filed an issue on this repository yet, so anything you find is "
            "probably worth filing. There is nothing already tracked to duplicate.\n"
        )
    the_open_ones = "\n".join(
        f"- #{an_issue.number} {an_issue.title}" for an_issue in what_is_already_tracked
    )
    return (
        "\nThis repository already has these issues open:\n\n"
        f"{the_open_ones}\n\n"
        "**Do not propose any of this work again.** A team that has already agreed to do "
        "something and is then sent a second issue about it has been sent work, not help. If "
        "everything you can see in the code is already covered by one of these, say so and "
        "return an empty list — that is a result.\n"
    )


def the_prompt_to_brief_a_repository(
    inspection: str,
    what_the_clone_holds: list[str],
    repository: Repository,
    how_many_opportunities: int,
    what_was_wrong_about_the_last_answer: str | None = None,
    what_is_already_tracked: Sequence[AnOpenIssue] = (),
) -> str:
    """The question put to the model about one repository it is being asked to brief itself.

    **The count is a ceiling and the prompt says so.** A deployment asking for five gets at most
    five, and a model told "at most five" proposes five even when the repository offers two. The
    sentence that matters is the other one: propose less if the repository offers less, because a
    briefing padded to a number is a list a person has to read to find the one worth doing.

    **The paths it may cite are listed, and that is the fix a real briefing needed.** The first
    briefing of a real repository proposed `src/App.jsx` in all four opportunities — a file the
    repository does not have, describing a React application the repository is not. The
    inspection contained the real files, and citing from it is a recall task, and this model
    recalled a different project. Listing the sixty paths the clone actually holds turns citing
    into a lookup, and the node's proof then has nothing left to catch.

    **The citation rule is in the prompt three times and the prompt is not what enforces it.**
    As a rule, as the reason, and as the list. The node refuses the whole briefing over one
    invented path — that is the enforcement, and it is why the paths are listed rather than
    trusted: a model told to cite real files will invent a plausible one, and the refusal is what
    turns that into a second question instead of a ticket.
    """
    what_is_already_tracked_says = _what_is_already_tracked_says(what_is_already_tracked)
    correction = (
        ""
        if what_was_wrong_about_the_last_answer is None
        else (
            "\nYour last answer was wrong, and this is what was wrong with it:\n"
            f"{what_was_wrong_about_the_last_answer}\n"
        )
    )

    the_paths_a_citation_may_name = "\n".join(f"- `{a_path}`" for a_path in what_the_clone_holds)

    return (
        f"You are briefing {repository.owner}/{repository.name} about what work it could be "
        "given.\n"
        "\n"
        "Answer from the inspection below and from nothing else. You have not been told anything "
        "about this repository that is not in it.\n"
        "\n"
        f"Propose at most {how_many_opportunities} opportunities, and fewer if the repository "
        "offers fewer. A briefing padded to a number is a list somebody has to read to find the "
        "one worth doing, and **an empty list is a result**: a repository in good shape has "
        "nothing worth doing and saying so is the most useful thing you can conclude. Do not "
        "invent work to fill the space.\n"
        "\n"
        f"Each opportunity names these: {', '.join(WHAT_EACH_OPPORTUNITY_MAY_NAME)}.\n"
        f"{what_is_already_tracked_says}"
        f"{correction}"
        "\n"
        "Every path in `the_files_that_show_this` must be **copied from the list below**, written "
        "exactly as it appears there. Do not compose a path, do not shorten one, and do not write "
        "a directory: naming a file this repository does not have costs the whole briefing and is "
        "checked, not taken on trust.\n"
        "\n"
        f"# The paths a citation may name — every one of these is a real file\n\n"
        f"{the_paths_a_citation_may_name}\n"
        "\n"
        "`how_it_would_be_known_to_have_worked` is the field a verification agent is later handed "
        "and is the reason an opportunity is worth filing. Write what a test or a check would "
        "assert — not 'it works better'.\n"
        "\n"
        "`the_discipline_that_owns_it` is one of: PO, DEV, QA, SEC, ARCH.\n"
        "\n"
        f"`the_risk_of_it` is required and is not a weakness. 'Touches the authentication "
        "middleware' lets somebody decide; a blank does not.\n"
        "\n"
        f"Your answer is one object with a field called `opportunities`, holding a list of "
        f"objects with the fields above, plus `what_this_repository_is` as one sentence, and "
        f"`what_the_briefing_could_not_settle` as a list of sentences. A briefing that found "
        f"nothing sends `opportunities: []`."
    )


def brief_this_repository(
    clone: ClonedRepository,
    repository: Repository,
    what_the_run_is_about: CommissionedRequest | None,
    model: BaseChatModel,
    how_many_opportunities: int = 5,
    what_is_already_tracked: Sequence[AnOpenIssue] = (),
) -> TheOpportunitiesThisRepositoryOffers:
    """What this repository could be given, with every citation proved against the clone.

    **Proved before it is returned, and proved by the caller holding the clone.** The report is
    built from what a model said and then every path in it is checked, because a briefing whose
    citations resolve to nothing reaches a person as a list of claims they cannot check — and
    `CitedFileNotFoundError` exists for a discovery report for exactly this reason. Two artifacts
    with the same hole would be the same hole twice.

    **One correction, on the budget every other reasoning node spends, and the budget is not
    optional here.** The first answer this node got from a real model on a real repository was a
    single opportunity with all five of its sentences blank — not an empty list, which is the
    finding this artifact exists to be able to state. A model handed a shape and asked to fill
    it fills it, and this one filled it with nothing rather than with the sentence the prompt
    spent four lines asking for. That is a wrong answer and not a refusal: the report type is
    right, the repository is legible, and the one thing missing is a second question.

    **The correction is added to the question and does not replace it**, for the reason every
    other node in this system does it that way: a second question with no first question is a
    question about something else, and the model's second answer would be about that.
    """
    inspection = an_inspection_of_the_code(clone, what_the_run_is_about)
    what_was_wrong: str | None = None

    began_at = time.monotonic()
    asked_so_far = 0
    while may_this_run_keep_asking(asked_so_far, began_at):
        asked_so_far += 1
        asking = ask_a_model_for(model, TheOpportunitiesThisRepositoryOffers)
        try:
            return TheOpportunitiesThisRepositoryOffers.proving_what_they_cite(
                _a_validated_report(
                    asking.invoke(
                        the_prompt_to_brief_a_repository(
                            inspection,
                            what_the_clone_holds(clone),
                            repository,
                            how_many_opportunities,
                            what_was_wrong,
                            what_is_already_tracked,
                        )
                    )
                ),
                what_the_clone_holds(clone),
            )
        except (
            AnOpportunityCitingAFileTheCloneDoesNotHoldError,
            ValidationError,
            AModelAnsweredInAShapeThisSystemCannotReadError,
        ) as refused:
            what_was_wrong = how_a_model_is_told_what_was_wrong(refused)
            last = refused

    raise last


def _a_validated_report(what_came_back) -> TheOpportunitiesThisRepositoryOffers:
    """The report, validated rather than cast.

    **The same rule every reasoning node in this system follows.** A model that ignores a schema
    is a real case rather than a theoretical one, and a briefing full of invented opportunities is
    a thing somebody would rule on.
    """
    if isinstance(what_came_back, TheOpportunitiesThisRepositoryOffers):
        return what_came_back
    if isinstance(what_came_back, dict):
        return TheOpportunitiesThisRepositoryOffers.model_validate(what_came_back)
    return TheOpportunitiesThisRepositoryOffers.model_validate(
        getattr(what_came_back, "__dict__", what_came_back)
    )


def what_the_clone_holds(clone: ClonedRepository) -> list[str]:
    """Every path the clone has, from its root, which is what a citation is written against.

    **A repository's own paths and no more.** The walk skips `.git` and the directories a
    dependency lives in, because a model citing `node_modules/x/index.js` is citing a file that
    exists and is not the repository's, and a briefing built on one is a briefing about a
    dependency.
    """
    from aisdlc.tools.inspect_the_repository import (
        DIRECTORIES_THAT_HOLD_SOMEONE_ELSES_CODE,
    )

    what_is_there: list[str] = []
    for a_path in clone.path.rglob("*"):
        if not a_path.is_file():
            continue
        its_parts = a_path.relative_to(clone.path).parts
        if any(a_part in DIRECTORIES_THAT_HOLD_SOMEONE_ELSES_CODE for a_part in its_parts):
            continue
        if ".git" in its_parts:
            continue
        what_is_there.append(str(a_path.relative_to(clone.path)))

    return sorted(what_is_there)


def the_briefing_using_the_configured_model() -> Brief:
    """The briefing agent, built from the deployment's own model like every other one here.

    **A factory and not a closure in the composition root**, because this is an agent and the six
    other agents all have one, and a reader comparing them should find the same shape in all
    seven.
    """
    from aisdlc.llm.llm_configuration import a_configuration_from_the_environment
    from aisdlc.llm.model_factory import a_model_for

    def briefing(
        clone: ClonedRepository,
        repository: Repository,
        what_the_run_is_about: CommissionedRequest | None,
        how_many_opportunities: int = 5,
        what_is_already_tracked: Sequence[AnOpenIssue] = (),
    ) -> TheOpportunitiesThisRepositoryOffers:
        return brief_this_repository(
            clone,
            repository,
            what_the_run_is_about,
            a_model_for(a_configuration_from_the_environment()),
            how_many_opportunities,
            what_is_already_tracked=what_is_already_tracked,
        )

    return briefing


# What a briefing is handed and hands back. **A callable and not a `Protocol` class**, because
# there is one production implementation and a class would be a file of ceremony around a type
# annotation — and the two closures the composition root and a test build have the same shape,
# which is what a reader comparing them needs to see.
Brief = Callable[
    [ClonedRepository, Repository, CommissionedRequest | None, int, Sequence[AnOpenIssue]],
    TheOpportunitiesThisRepositoryOffers,
]


def cloning_a_repository_to_read_only() -> Callable[[Repository, Path], RepositoryToClone]:
    """Clone a repository the way to read it, which is not the way to write to it.

    **A briefing forks nothing and this is the reason.** Every other clone in this system goes
    through `a_clone_this_system_may_write_to`, which forks first, because the run that follows is
    going to push a branch and open a pull request. A briefing reads a repository and proposes
    work; nothing about it writes anything, so a fork would be an account's copy of somebody's
    repository created for a read and left behind by it.

    **HTTPS and not SSH, for the same reason `the_clone_url_of` says.** Reading a public
    repository needs no credential, so a briefing works on a machine with no key — and a URL with
    a token in it is a URL git echoes back when it fails.

    **The origin is recorded as where the code came from rather than where it is.** The `Addresses`
    value has two fields because a clone can be read from one place and written to another, and a
    briefing has only the first. Leaving the second as the same place says "this is the
    original", which for a briefing it is.
    """
    from aisdlc.tools.github_client import Addresses, the_clone_url_of
    from aisdlc.tools.github_clone_repository import a_repository_to_clone

    def planning(source: Repository, into: Path) -> RepositoryToClone:
        a_read_only_address = the_clone_url_of(source)
        return a_repository_to_clone(
            source,
            Addresses(fetch_from=a_read_only_address, origin_of_the_code=a_read_only_address),
            into,
        )

    return planning
