from collections import defaultdict
from typing import Any

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder


class LiveQuizRealtimeBroadcaster:
    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(
        self,
        quiz_id: str,
        websocket: WebSocket,
        *,
        accepted: bool = False,
    ) -> None:
        if not accepted:
            await websocket.accept()
        self._connections[quiz_id].add(websocket)

    def disconnect(self, quiz_id: str, websocket: WebSocket) -> None:
        connections = self._connections.get(quiz_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(quiz_id, None)

    async def publish(self, quiz_id: str, event: dict[str, Any]) -> None:
        connections = list(self._connections.get(quiz_id, set()))
        stale: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_json(jsonable_encoder(event))
            except Exception:
                stale.append(websocket)

        for websocket in stale:
            self.disconnect(quiz_id, websocket)


live_quiz_realtime_broadcaster = LiveQuizRealtimeBroadcaster()
