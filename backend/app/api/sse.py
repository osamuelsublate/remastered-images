"""Server-Sent Events encoding shared by the chat and transcription routes.

Both stream a sequence of ``(event_name, payload)`` tuples where the payload
is either plain text (deltas/errors) or a Pydantic model (the final
``CarouselState``); this module only knows how to turn that into
``text/event-stream`` bytes.
"""

from __future__ import annotations

import json
from typing import Any, Iterable, Iterator

from pydantic import BaseModel


def sse_encode(events: Iterable[tuple[str, Any]]) -> Iterator[bytes]:
    for event, payload in events:
        data = (
            payload.model_dump_json()
            if isinstance(payload, BaseModel)
            else json.dumps(payload)
        )
        yield f"event: {event}\ndata: {data}\n\n".encode()
