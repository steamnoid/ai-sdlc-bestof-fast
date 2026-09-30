"""How long a run may keep asking a model for something it already has.

§14 says a failed answer goes to *retry / repair*, and the budget is part of that rule rather
than a detail of it. **A deployment states the budget and the default is what a run proved
necessary**, so the rule is a rule with a value rather than a number written in stone.

**The default is two corrections, and a run is why, and the fault it answers is a gateway
rather than a model.** Asked for a forced tool, this gateway once returned a message with no
tool call in it, and the parser turned that into `None`; the correction loop caught it, asked
again, and got nothing again. Two attempts was all one correction allowed, and the run ended at
the product analyst. The model was not refusing — it had produced a complete, correct artifact
on three probes out of six.

**A deployment may lift the count, and the reason it is allowed to is a price.** The argument
that used to hold this budget down was that a correction is a paid call. It does not hold for a
model whose price is zero, and a rule that survives only because a call is expensive is not a
rule about correctness — it is a rule about money, wearing correctness's clothes. The honest
response to an unreliable dependency is to ask again rather than to end a run.

**Lifting the count does not lift the ceiling, because the count was the only bound there was.**
The per-call timeout bounds one call and not the loop around it, so with no count a node could
ask until somebody noticed. The minutes are that bound, and a run that has spent them stops and
raises the last refusal, exactly as it did before — a person still gets a thing to act on, which
is what a correction budget was ever for.

It is its own module because **the budget is one rule and seven agents enforce it.** Discovery
corrects a cited file that is not in the clone, the product analyst corrects an answer that said
nothing, and the other five correct a shape they did not ask for. Those are different failures,
and the question behind all seven is one question: may this run go on asking? A budget written
per agent is several numbers that drift into disagreeing about when to give up, and the run
that gives up last is the one that hangs.

A run that exhausts its budget raises the *last* refusal rather than a summary of them. The
caller needs the last thing that was wrong, because that is the thing worth showing a person,
and a list of three near-miss citations helps nobody decide what to do next.

**A setting that is not a number is refused rather than ignored.** A deployment that misspells
its budget and is silently given the default has asked for nothing and got something, and the
only way anyone finds out is a run behaving in a way nobody chose.
"""

from __future__ import annotations

import os
import time

from pydantic import ValidationError

# Stated by a deployment rather than written here, and both absent by default. The names are
# this package's convention — `AISDLC_FORK_OWNER` is the other one — and the two are read only
# by the two functions below.
THE_SETTING_NAMING_THE_BUDGET = "AISDLC_CORRECTION_BUDGET"
THE_SETTING_NAMING_THE_MINUTES = "AISDLC_CORRECTION_MINUTES"

# What a deployment gets for saying nothing, and the reason each number is that number is in the
# tests that hold them: two corrections is what the product analyst needed and one gateway did
# not give, and thirty minutes is about ten times the longest any single node has spent being
# corrected — long enough not to cut short a run that was going to work.
HOW_MANY_CORRECTIONS_WHEN_NO_BUDGET_IS_STATED = 2
HOW_MANY_MINUTES_WHEN_NO_CEILING_IS_STATED = 30

# Zero corrections means the count does not apply, rather than meaning "never correct anything".
# A deployment turning the budget off writes `0`, and a system that read it as a prohibition
# would refuse every imperfect answer — the opposite of what it was asked for.
NO_COUNT_APPLIES = 0


class ACorrectionBudgetThatIsNotANumberError(Exception):
    """The rule is in this module: a budget is a number, and a word is not one.

    Raised rather than falling back to the default, because a fallback is invisible. A
    deployment whose `AISDLC_CORRECTION_BUDGET` is `unlimited` would otherwise be given two
    corrections and no sign of it, and would find out from a run that died.
    """

    def __init__(self, setting: str, what_was_said: str) -> None:
        """Say which setting, and repeat what it said — the two things needed to fix it."""
        super().__init__(
            f"{setting} is how many, and it was given {what_was_said!r}. State a whole number, "
            f"or 0 if the count does not apply and {THE_SETTING_NAMING_THE_MINUTES} is what "
            "bounds this run instead."
        )


def how_many_corrections_a_model_may_be_given() -> int:
    """The corrections this deployment allows, or none when it says the count does not apply.

    **Read once per call rather than once at import**, so a deployment that states a budget
    after the process started gets the budget it stated, and so a test can state one.
    """
    return _a_number_the_deployment_stated(
        THE_SETTING_NAMING_THE_BUDGET, HOW_MANY_CORRECTIONS_WHEN_NO_BUDGET_IS_STATED
    )


def how_long_a_run_may_keep_asking() -> int:
    """The seconds a single node may spend being corrected before it stops and raises.

    Seconds rather than minutes because every caller compares against `time.monotonic()`, and
    a caller that had to multiply would be seven places to get the arithmetic right.
    """
    return 60 * _a_number_the_deployment_stated(
        THE_SETTING_NAMING_THE_MINUTES, HOW_MANY_MINUTES_WHEN_NO_CEILING_IS_STATED
    )


def may_this_run_keep_asking(asked_so_far: int, began_at: float) -> bool:
    """Whether to put the question again, which is the whole rule in one question.

    **Both limits apply together**, so neither is a fallback for the other: a run with
    corrections left stops when the minutes are gone, and a run with minutes left stops when
    the corrections are spent. `asked_so_far` counts questions already put, so a budget of two
    allows the first question, one correction, and no fourth.
    """
    if time.monotonic() - began_at >= how_long_a_run_may_keep_asking():
        return False

    allowed = how_many_corrections_a_model_may_be_given()
    return allowed == NO_COUNT_APPLIES or asked_so_far <= allowed


def _a_number_the_deployment_stated(setting: str, when_silent: int) -> int:
    """The setting's value as a whole number, or the default when it says nothing.

    **A value that is a word is refused and not rounded, and not ignored.** `int()` would take
    `"7 "` and refuse `"seven"`, and a reader of a failed run deserves to be told which of the
    two settings to look at and what it actually said.
    """
    what_was_said = os.environ.get(setting, "").strip()

    if not what_was_said:
        return when_silent

    try:
        return int(what_was_said)
    except ValueError:
        raise ACorrectionBudgetThatIsNotANumberError(setting, what_was_said) from None


def how_a_model_is_told_what_was_wrong(refused: BaseException) -> str:
    """The question a model is asked after a wrong answer, in the words it can act on.

    **Both halves are load-bearing.** Which artifact was refused and why, because seven agents
    ask for seven artifacts and "wrong" is not addressable; and what to send instead, because a
    model told that its answer was not JSON and not told what *is* JSON will send the same thing
    again — which is what a run watched happen twice.

    The refusal is quoted whole rather than summarised. A model can act on a parser's own words
    once it also has an instruction, and the person reading an exhausted budget later is owed
    the refusal rather than a description of it.

    **The instruction names the tool and not JSON, because the answer does not arrive as a
    message.** Every structured question here is asked through a forced tool call, and what
    comes back is that call's arguments. Telling a model on this transport to "answer with a
    single JSON object" is telling it to abandon the tool, and a run did precisely that:
    thirty-one corrections, each answered in about ten seconds where a real answer takes forty
    to one hundred and forty-five, and each refused for arriving as `None`.

    The tool's name is read out of the refusal rather than passed in, because the refusal opens
    with it — `1 validation error for QaPlanAnswer` — and a caller that had to supply the name
    would have to know which artifact its own node was asking for, which is one more thing to
    keep true.
    """
    what_to_send = (
        f"Call the `{refused.title}` tool with the whole answer in its arguments, and write "
        "nothing else: no sentence before it and no explanation after it."
        if isinstance(refused, ValidationError)
        else "Answer again in the form that was asked for."
    )

    return (
        f"Your last answer was refused, and this is why:\n\n{str(refused).strip()}\n\n"
        f"{what_to_send}"
    )
