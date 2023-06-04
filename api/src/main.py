import asyncio
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sse_starlette import ServerSentEvent
from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute
from sse_starlette.sse import EventSourceResponse
from starlette.websockets import WebSocket, WebSocketDisconnect
from starlette.responses import PlainTextResponse
from starlette import status

class RequestMessage(BaseModel):
    message: str

class WebSocketManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def message(self, client_id: str, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, game: str):
        for connection in self.active_connections:
            await connection.send_text(game)

class Stream:
    def __init__(self) -> None:
        self._queue = asyncio.Queue[ServerSentEvent]()

    def __aiter__(self) -> "Stream":
        return self

    async def __anext__(self) -> ServerSentEvent:
        return await self._queue.get()

    async def asend(self, value: ServerSentEvent) -> None:
        await self._queue.put(value)

app = FastAPI()

wsManager = WebSocketManager()
_stream = Stream()
app.dependency_overrides[Stream] = lambda: _stream

@app.get("/")
def root():
    return {"message": "Hello World"}

@app.get("/sse")
async def sse(stream: Stream = Depends()) -> EventSourceResponse:
    return EventSourceResponse(stream)

@app.post("/poke-sse", status_code=status.HTTP_201_CREATED)
async def poke_sse(request_msg: RequestMessage, stream: Stream = Depends()):
    try:
        await stream.asend(
            ServerSentEvent(data=request_msg.message)
        )
    except HTTPException as e:
        return { "message": "error"}
    return { "message": "sse poke success"}


@app.websocket("/ws")
async def websocket(websocket):
    await wsManager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()

    except WebSocketDisconnect:
        wsManager.disconnect(websocket)
        await wsManager.broadcast("connection closed")

@app.post("/poke-ws")
async def pokeWsRoute(request):
    try:
        await wsManager.broadcast("poke")
    except:
        return { "message": "error"}

    return { "message": "websocket poke success"}





