"""The field an artifact cannot leave empty, and what an empty one means.

**Silence in a finding is read as an answer, and this is the list of where that is true.**
`SecurityReport` already refuses an empty result itself — `EmptySecurityReportError`, on the
ground that a report saying nothing about a repository's security reads as a report saying it is
fine, "the one silence in this pipeline that could be acted on with real consequences". That rule
was written for one artifact and the reasoning is not specific to it: a stage that returns an
empty list has not found nothing, it has declined to answer, and every reader downstream has no
way to tell those apart.

**So this is the same rule for the stages that have no such check**, and it lives in the default
tier so it can be proved without a model. The pair tests import it and apply it to whatever a
real model returned; nothing here asserts about a model, only that the mapping is real — that
each artifact names fields which exist on it — because a rule naming a field that has been
renamed is a rule that silently stopped applying.

**One artifact may be empty, and has to say why.** A security report with no findings is a
legitimate answer, and the field saying so is `nothing_found_because`. A report that is empty
*and* silent about what it looked at is the fault, so its entry is an "at least one of".
"""

from __future__ import annotations

from pydantic import BaseModel

from aisdlc.agents.architecture_report import ArchitectureReport
from aisdlc.agents.discovery_report import DiscoveryReport
from aisdlc.agents.implementation_plan import ImplementationPlan
from aisdlc.agents.qa_plan import QaPlan
from aisdlc.agents.requirements import Requirements


class WhatAnArtifactMustHaveSaid(BaseModel):
    """One artifact, and the fields of it where one of them cannot be empty.

    **`at_least_one_of` rather than `every`, because two artifacts have a legitimate empty
    answer.** A security report may find nothing and a discovery report may have no suggested
    changes, and the difference between that and a stage that declined to answer is exactly what
    a reader cannot see. `nothing_found_because` is the field that carries the difference for a
    security report, which is why it is in the same list rather than somewhere else.
    """

    artifact: type
    at_least_one_of: tuple[str, ...]
    why_an_empty_one_is_a_fault: str


# **Five artifacts, and each one names the field that carries its answer.** The list is in
# pipeline order rather than alphabetically, because it is read next to the pipeline far more
# often than it is searched.
WHAT_EVERY_FINDING_MUST_HAVE_SAID = (
    WhatAnArtifactMustHaveSaid(
        artifact=DiscoveryReport,
        at_least_one_of=("architecture_summary", "key_components"),
        why_an_empty_one_is_a_fault=(
            "a discovery report with no architecture summary and no components is a report that "
            "read the repository and wrote nothing down, and the four gates after it are asked to "
            "approve exactly that emptiness"
        ),
    ),
    WhatAnArtifactMustHaveSaid(
        artifact=Requirements,
        at_least_one_of=("requirements", "acceptance_criteria"),
        why_an_empty_one_is_a_fault=(
            "requirements with nothing in them are approved by a human at the first gate and "
            "then planned, implemented and put in front of somebody as a pull request, and no "
            "stage in between can tell that nothing was ever asked for"
        ),
    ),
    WhatAnArtifactMustHaveSaid(
        artifact=QaPlan,
        at_least_one_of=("scenarios", "test_strategy"),
        why_an_empty_one_is_a_fault=(
            "a QA plan with no scenarios and no strategy is the one the implementer was told to "
            "satisfy, so the emptiness is copied into whatever the implementer invents to fill it"
        ),
    ),
    WhatAnArtifactMustHaveSaid(
        artifact=ArchitectureReport,
        at_least_one_of=("modules",),
        why_an_empty_one_is_a_fault=(
            "this is the one a real run proved the hard way. The architecture analyst returned "
            "modules: [], so there was nothing to check the QA plan against and nothing to check "
            "the security findings against — the pair read as agreeing because nothing could be "
            "compared. An architecture report that names no modules agrees with everything and "
            "therefore says nothing"
        ),
    ),
    WhatAnArtifactMustHaveSaid(
        artifact=ImplementationPlan,
        at_least_one_of=("files_to_change", "files_to_add", "tests_to_add"),
        why_an_empty_one_is_a_fault=(
            "a plan naming no file is a plan the implementer cannot act on, and the guard that "
            "ends a change passes it because there is nothing missing"
        ),
    ),
)
