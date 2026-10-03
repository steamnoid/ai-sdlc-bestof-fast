"""What the discovery agent learned about a repository, in the fields §10 lists.

The field names are not chosen here. `docs/domain-glossary.md` already fixed the
contents of this artifact, and the agent's name is the contract, so a field that drifts
from that table is a broken promise rather than a rename.
"""

from __future__ import annotations

from pydantic import BaseModel, model_validator

from aisdlc.agents.a_value_that_says_something import a_value_that_says_something
from aisdlc.domain.repository import Repository

THE_DISCOVERY_AGENT = "aisdlc-discover"
WHERE_A_REVIEWER_READS_A_FILE = "https://github.com/{owner}/{name}/blob/{branch}/{path}"


class EmptyDiscoveryReportError(Exception):
    """The rule is in `DiscoveryReport`, and this is the only thing that may say it broke.

    Raised rather than returned as a Pydantic `ValidationError`, because the caller has
    something to do about this one that it cannot do about a malformed field: a report
    with one bad language is a report to ask the agent to fix, and a report that says
    nothing is a fault to be told about in our own words.
    """


class EvidenceOutsideRepositoryError(Exception):
    """The rule is in `evidence_for`, and this is the only thing that may say it broke."""


class EvidenceFile(BaseModel):
    """One file of the repository, and the address a reviewer opens to see it.

    The link is derived rather than asked for, so a model cannot name a host it likes.
    What the agent contributes is the path; the address follows from the repository the
    run is about, which is why building it needs no model at all.
    """

    path: str
    link: str


class DiscoveryReport(BaseModel):
    """What a repository is, in the terms a reader would plan against it.

    `evidence_files` is the paths these claims rest on, and it is not an inventory of
    the repository. An inventory is a fact that can be counted, so it is computed rather
    than asked for, and a model asked to produce one will produce a plausible list
    either way. What only the agent knows is which files it concluded something from,
    and naming them is what makes a human's approval worth something and what lets a
    test check a report against a repository that really exists.
    """

    languages: list[str] = []
    frameworks: list[str] = []
    build_system: str | None = None
    ci_system: str | None = None
    architecture_summary: str = ""
    key_components: list[str] = []
    evidence_files: list[EvidenceFile] = []
    suggested_changes: list[str] = []

    def everything_it_says(self) -> tuple[object, ...]:
        """Every field's value, in the order the glossary lists them."""
        return (
            self.languages,
            self.frameworks,
            self.build_system,
            self.ci_system,
            self.architecture_summary,
            self.key_components,
            self.evidence_files,
            self.suggested_changes,
        )

    @model_validator(mode="after")
    def it_must_cite_a_file_it_read(self) -> DiscoveryReport:
        """At least one file of this repository, or this is a report about something else.

        **A real run was refused at its first gate for exactly this**: `evidence_files` came back
        empty, `architecture_summary` blank, and the reason was that *"the suggested change is not
        grounded in any inspected file"*. **Every check here had passed it** —
        `_the_cited_files_that_are_in` proves each citation is a file of the clone and was shown to
        the model, which it does of zero citations without complaint, and the rule below is
        satisfied by nothing more than a list of languages.

        **This is the third of one bug and the shape is identical each time.**
        `expect(true).toBe(true)` passes whatever the code does; `<jwt-secret-guard-test>.test.ts`
        passed every check about paths; an empty citation list passes every check about citations.
        **All three are an empty value satisfying a rule written about its members** — a rule of the
        form *every X must be Y*, which an empty list satisfies without doing anything.

        **The field that cannot be empty is the one carrying what was read.** The rest may
        legitimately be absent — a repository with no CI has nothing to say about CI, and a rule
        demanding every field would only ever be satisfied by a report that guesses. **A report that
        says what a repository is built with and never says what it read was produced from something
        that is not the repository.**
        """
        if not self.evidence_files:
            raise EmptyDiscoveryReportError(
                f"{THE_DISCOVERY_AGENT} cited no file: `evidence_files` is empty, so nothing in "
                "this report is grounded in anything anybody opened. Every check above is about "
                "the citations themselves — each is a file of this repository and was shown to "
                "you — and none of them can notice there were none.\n\n"
                "Name at least one path you were shown and read, as a path inside the "
                "repository. The reader of this report clicks those links, and a report whose "
                "claims rest on nothing links to nothing."
            )
        return self

    @model_validator(mode="after")
    def it_must_say_something_about_the_repository(self) -> DiscoveryReport:
        """At least one field must carry a value, or this is a fault and not a report.

        "At least one" and not "all of them", because a repository with no CI has
        nothing to say about CI and must be able to say so. Absence is representable,
        and a rule demanding every field would only ever be satisfied by a report that
        guesses.

        **This is not the rule that caught the empty report, and it is kept because it catches a
        different one.** A report that cites a file and says nothing else about the repository has
        grounded itself in something and analysed nothing.
        """
        if not any(a_value_that_says_something(value) for value in self.everything_it_says()):
            raise EmptyDiscoveryReportError(
                f"{THE_DISCOVERY_AGENT} reported nothing at all about the repository: "
                "every field was empty. That is a fault rather than an artifact, "
                "because a person cannot tell an empty report from a real one by "
                "looking at it."
            )

        return self


def evidence_for(paths: list[str], repository: Repository) -> list[EvidenceFile]:
    """The evidence for a set of paths, each with the address a reviewer opens.

    Every path is checked before any link is built, so a set containing one bad path
    produces no evidence at all rather than a report that is partly clickable.
    """
    return [_the_evidence_for(path, repository) for path in paths]


def _the_evidence_for(path: str, repository: Repository) -> EvidenceFile:
    if not _is_a_path_inside_the_repository(path):
        raise EvidenceOutsideRepositoryError(
            f"{path!r} is not a path inside {repository.owner}/{repository.name}, so it "
            "cannot be evidence. A report's links must stay on the repository the human "
            "was asked to approve, because that is where they will be clicked."
        )

    return EvidenceFile(
        path=path,
        link=WHERE_A_REVIEWER_READS_A_FILE.format(
            owner=repository.owner,
            name=repository.name,
            branch=repository.default_branch,
            path=path,
        ),
    )


def _is_a_path_inside_the_repository(path: str) -> bool:
    """Whether this string is a path in a repository, rather than a way out of one.

    Four shapes get out, and each is refused on its own terms: nothing at all, a URL
    with a scheme, a rooted path, and a `..` that climbs above the repository. A rooted
    path covers the protocol-relative `//host/...` too, since it is rooted.

    The `..` test looks at whole segments rather than looking for two dots, so an
    ordinary file called `app..tsx` is a file and not an escape.
    """
    if not path.strip():
        return False

    if "://" in path:
        return False

    if path.startswith("/"):
        return False

    return ".." not in path.split("/")
