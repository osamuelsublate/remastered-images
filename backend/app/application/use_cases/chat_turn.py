"""Use case: one conversational turn, possibly proposing/updating the plan.

Split in two so a domain error (missing carousel, generation already
running) can still map to a normal HTTP status code *before* the response
starts streaming:

- ``begin_chat_turn`` runs synchronously: validates, records the user's
  message, and is called *before* the route creates the
  ``StreamingResponse``. Errors here still raise normally.
- ``stream_chat_reply`` is a generator that does the actual (streamed) call
  to the AI, persists the result, and yields SSE-ready ``(event, payload)``
  pairs. Once bytes start flowing there's no changing the HTTP status
  anymore, so provider failures surface as an ``("error", message)`` event
  instead of a raised exception.
"""

from __future__ import annotations

from typing import Iterator

from ...domain.carousel import CarouselState, ChatMessage
from ...domain.errors import CarouselNotFound, GenerationInProgress
from ...ports.carousel_repository import CarouselRepository
from ...ports.job_runner import JobRunner
from ...ports.text_ai_provider import TextAIProvider

ChatStreamEvent = tuple[str, str | CarouselState]


def begin_chat_turn(
    cid: str,
    message: str,
    *,
    repo: CarouselRepository,
    job_runner: JobRunner,
) -> CarouselState:
    state = repo.load(cid)
    if state is None:
        raise CarouselNotFound(cid)
    if job_runner.is_active(cid):
        raise GenerationInProgress("Aguarde a geração terminar.")

    state.messages.append(ChatMessage(role="user", content=message))
    repo.save(state)
    return state


def stream_chat_reply(
    state: CarouselState,
    *,
    repo: CarouselRepository,
    text_ai: TextAIProvider,
) -> Iterator[ChatStreamEvent]:
    """Yields ``("delta", text)`` chunks, then either ``("done", CarouselState)``
    once the reply is persisted, or ``("error", message)`` if the AI call
    fails at any point.
    """
    history = [{"role": m.role, "content": m.content} for m in state.messages]
    try:
        streamer = text_ai.chat_turn_stream(
            history, current_plan=state.plan, references=state.references
        )
        for chunk in streamer:
            yield ("delta", chunk)
        text, plan = streamer.result()
    except Exception as exc:  # noqa: BLE001
        yield ("error", f"Falha no chat: {exc}")
        return

    state.messages.append(ChatMessage(role="assistant", content=text))
    if plan is not None:
        state.plan = plan
        if state.status in ("draft", "planned"):
            state.status = "planned"
    repo.save(state)
    yield ("done", state)
