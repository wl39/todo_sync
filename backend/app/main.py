from fastapi import FastAPI

from .api import auth, public, sharing, todos, ws
from .models import base, todo, todo_audit, user  # noqa: F401

app = FastAPI(title="todo_sync API")

app.include_router(auth.router)
app.include_router(todos.router)
app.include_router(sharing.router)
app.include_router(public.router)
app.include_router(ws.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
