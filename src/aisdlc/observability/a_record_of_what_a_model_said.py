"""What a model was asked, what it said, and how long it took — while it is happening.

**A run that cannot say what it is waiting for is a run nobody can help.** Silence between two
lines of progress is silence in which a slow call, a hung gateway and a refused request are
indistinguishable, and a person watching has no instrument to tell them apart. This is that
instrument, and it is here rather than in a test because the person waiting is whoever is
operating the deployment.

**It is a callback, not a change to the six agents.** LangChain raises `on_llm_start`,
`on_llm_new_token` and `on_llm_end` whether the caller used `.invoke()` or `.stream()`, so
installing this at the factory gives production streaming without a single agent learning that
observability exists. That is the whole reason it is a callback and not a wrapper.

**Off unless somebody asks.** The default suite must stay silent and CI must not fill a disk
with tokens, so `a_model_for` takes this as an argument and a deployment that wants it installs
one. A run nobody is watching announces nothing.

**An empty token is not announced.** Some providers send empty chunks, and a line containing
nothing reads as a symptom rather than as nothing.
"""

from __future__ import annotations

import time
from typing import TextIO, override
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import GenerationChunk, LLMResult
from langchain_core.outputs.chat_generation import ChatGenerationChunk
from pydantic import ValidationError

from aisdlc.observability import saying_what_a_run_is_doing
from aisdlc.observability.saying_what_a_run_is_doing import (
    announcing_what_a_run_is_doing,
)


def _the_terminal_a_person_is_watching() -> TextIO:
    """Where a token goes, and why it is not simply `print`.

    **A token is the only thing this system prints that cannot be reconstructed.** Every other
    line is a decision it made, and a decision is derivable from the artifacts on disk; a token is
    not, and a run that answers in three words after ninety seconds is identical afterwards to one
    that answers in three words after nine minutes. What was on screen while it happened is the
    only record that the difference existed.

    **So it is written where the person is, and nowhere else.** `print(token, end="")` reaches
    `sys.stdout`, which pytest has already taken: a real run paused for ninety seconds and then
    emitted a stage line, with no explanation for either. The same duplication the command runner
    had -- written once here, and a second copy into a stream nobody was reading.

    **Looked up on the module rather than imported by name**, so a test replaces one place. A
    `from` import binds the function at import time and silently ignores the replacement, which is
    how a test ends up asserting about a stream nothing writes to.

    **Off, it is `sys.stdout` and the four hundred tests keep reading it through `capsys`.** The
    default suite must stay silent *and* stay assertable, and that is the same promise.
    """
    return saying_what_a_run_is_doing.where_the_output_goes()


class ARecordOfWhatAModelSaid(BaseCallbackHandler):
    """One run's model calls, told as they happen and remembered afterwards.

    **Every callback carries `@override` and every signature is the supertype's**, which is
    six arguments and not a design choice. These are the hooks the runtime raises; a shorter
    signature would be a different method with the same name.

    **Elapsed time is measured between the two callbacks the runtime already raises**, rather
    than around an `.invoke()` that six agents would each have to wrap — six chances to forget,
    and a run that reports no duration for the one call that mattered.

    Per-run state is keyed by `run_id` rather than held in one slot. One instance serves every
    call in a run and a run makes seven of them, so a single slot has the seventh call
    overwriting the first call's start and reporting a negative duration.
    """

    def __init__(self, the_model: str) -> None:
        """A record for one named model, ready to be handed to it.

        **The name is an argument because the runtime does not carry it.** The serialised model
        this callback receives has the *class* name in it and no model name, so a record that
        read it printed `ChatOpenAI` — and a line naming the wrong model is worse than no line,
        because the question the line exists to answer is "which model was that".

        The fragments of the answer are kept even though they are not printed, because they are
        the whole of the diagnosis when a call fails: a model asked for JSON that answers in
        prose is the difference between "the gateway is broken" and "this model does not do
        structured output", and nothing else in the system can tell those apart.
        """
        self.the_model = the_model
        self.started_at: dict[UUID, float] = {}
        self.announced: list[str] = []
        self.said: list[str] = []
        self.fragments: dict[UUID, list[str]] = {}
        self.asked_and_not_yet_judged: str = ""
        self.awaiting_a_verdict: str = ""

    @override
    def on_llm_start(
        self,
        serialized: dict[str, object],
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, object] | None = None,
        **kwargs: object,
    ) -> None:
        """Say what is being sent, and how much of it, before anything is waiting on.

        The size rather than the text: a 400-character prompt and a 40 000-character one are
        different lengths of wait, and the number tells them apart without putting a
        repository's contents into somebody's terminal.
        """
        if self.asked_and_not_yet_judged:
            self.announced.append(
                announcing_what_a_run_is_doing(
                    "this question was not accepted, because another one followed it:\n"
                    f"{self.asked_and_not_yet_judged}",
                    0.0,
                )
            )
        self.asked_and_not_yet_judged = "".join(prompts)
        self.started_at[run_id] = time.monotonic()
        self.fragments[run_id] = []
        self.announced.append(
            announcing_what_a_run_is_doing(
                f"asking {self.the_model} a question of "
                f"{sum(len(prompt) for prompt in prompts)} characters",
                0.0,
            )
        )

    @override
    def on_llm_new_token(
        self,
        token: str | list[str | dict[str, object]],
        *,
        chunk: GenerationChunk | ChatGenerationChunk | None = None,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: object,
    ) -> None:
        """Print the token as it arrives, because a buffered token is not a token.

        **A list is not a token and is not printed.** Structured output arrives as tool-call
        deltas, which are `list[dict]` fragments of a JSON envelope; printing them interleaves
        braces into the line a person is reading, and the last one wins, so the answer on screen
        is not the answer that arrives.
        """
        if chunk is not None:
            self.fragments[run_id] = self.fragments.get(run_id, []) + _the_fragments_in(chunk)

        if not isinstance(token, str) or not token:
            return
        self.said.append(token)
        _the_terminal_a_person_is_watching().write(token)
        _the_terminal_a_person_is_watching().flush()

    @override
    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: object,
    ) -> None:
        """Say how long it took, and close the line the tokens were written on.

        Without the closing line the tokens run into whatever prints next, and a reader cannot
        tell where one answer ended and the next thing began.
        """
        elapsed = self._how_long_since(run_id)
        _the_terminal_a_person_is_watching().write("\n")
        _the_terminal_a_person_is_watching().flush()
        self.announced.append(
            announcing_what_a_run_is_doing(f"answered in {elapsed:.1f}s", elapsed)
        )

    @override
    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: object,
    ) -> None:
        """Say what went wrong, because silence after a question is the worst of the silences."""
        elapsed = self._how_long_since(run_id)
        _the_terminal_a_person_is_watching().write("\n")
        _the_terminal_a_person_is_watching().flush()
        what_it_said = "".join(self.fragments.pop(run_id, []))
        if what_it_said:
            self.announced.append(
                announcing_what_a_run_is_doing(
                    f"it answered this, which is not what was asked for: {what_it_said[:600]}",
                    elapsed,
                )
            )
        self.announced.append(
            announcing_what_a_run_is_doing(
                f"failed after {elapsed:.1f}s: {_what_went_wrong(error)}", elapsed
            )
        )

    def _how_long_since(self, run_id: UUID) -> float:
        began = self.started_at.pop(run_id, None)
        return 0.0 if began is None else time.monotonic() - began


def _what_went_wrong(error: BaseException) -> str:
    """The reason, with the field named when the reason *is* a field.

    A validation error opens with "1 validation error for ImplementationPlan" and puts the
    offending field four lines further down, so truncating the message keeps the part that says
    nothing and drops the part that says everything — and on a live run the line read
    "1 validation error for ImplementationPlan" and named no field at all.

    **Both halves are named: the artifact and the field.** A run asks seven agents for seven
    different artifacts, so "the shape was wrong" without saying which one is a question rather
    than a diagnosis, and the model is the same on every call and so cannot stand in for it.
    """
    if isinstance(error, ValidationError):
        the_fields = sorted(
            {
                ".".join(str(part) for part in found["loc"])
                for found in error.errors()
                if found["loc"]
            }
        )
        if not the_fields:
            return f"{error.title} on a shape that is not the artifact at all"

        return f"{error.title} on {', '.join(the_fields)}"

    return str(error)[:300]


def _the_fragments_in(chunk: GenerationChunk | ChatGenerationChunk) -> list[str]:
    """The pieces of a structured answer, as they arrive.

    **Read from the message rather than from the token**, because a structured answer arrives as
    tool-call deltas and the token is a list of them rather than text. Concatenating the `args`
    fragments gives back the answer the model sent, which is the one thing worth showing when the
    call failed.

    **Each delta is read as a dictionary, not as an object**, which is what the runtime hands
    over: `ToolCallChunk` is spelled as a class and an instance of it has `dict` as its whole
    method resolution order, so `fragment.args` cannot work and mypy is right that it does not
    exist. Reading an attribute here would have failed on the first live call and the type checker
    said so.
    """
    if not isinstance(chunk, ChatGenerationChunk):
        return []

    if not isinstance(chunk.message, AIMessageChunk):
        return []

    found: list[str] = []
    for fragment in chunk.message.tool_call_chunks:
        the_args = fragment.get("args")
        if isinstance(the_args, str) and the_args:
            found.append(the_args)
    return found
