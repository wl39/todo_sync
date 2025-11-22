from __future__ import annotations

from collections import defaultdict
from typing import Callable, DefaultDict, List

from fastapi import WebSocket

Subscriber = Callable[[dict], None]


class InMemoryEventBus:
    def __init__(self) -> None:
        self.listeners: DefaultDict[str, List[Subscriber]] = defaultdict(list)

    def subscribe(self, channel: str, callback: Subscriber) -> None:
        self.listeners[channel].append(callback)

    def unsubscribe(self, channel: str, callback: Subscriber) -> None:
        if channel in self.listeners and callback in self.listeners[channel]:
            self.listeners[channel].remove(callback)

    def publish(self, channel: str, payload: dict) -> None:
        for callback in list(self.listeners.get(channel, [])):
            callback(payload)


class WebSocketManager:
    def __init__(self, bus: InMemoryEventBus | None = None) -> None:
        self.bus = bus or InMemoryEventBus()
        self.connections: DefaultDict[str, List[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, channel: str) -> None:
        await websocket.accept()
        self.connections[channel].append(websocket)

    def disconnect(self, websocket: WebSocket, channel: str) -> None:
        if websocket in self.connections.get(channel, []):
            self.connections[channel].remove(websocket)

    async def broadcast(self, channel: str, message: dict) -> None:
        for connection in list(self.connections.get(channel, [])):
            await connection.send_json(message)

    async def publish(self, channel: str, message: dict) -> None:
        await self.broadcast(channel, message)
        self.bus.publish(channel, message)


ws_manager = WebSocketManager()
