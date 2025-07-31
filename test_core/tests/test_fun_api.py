
import pytest, asyncio
from httpx import AsyncClient
from fastapi import FastAPI

from backend.core.fun_core import fun_router

@pytest.fixture(scope="module")
def test_app():
    app = FastAPI()
    app.include_router(fun_router)
    return app

@pytest.mark.asyncio
async def test_joke_endpoint(test_app):
    async with AsyncClient(app=test_app, base_url="http://test") as ac:
        resp = await ac.get("/api/fun/random?type=joke")
        assert resp.status_code == 200
        body = resp.json()
        assert body["type"] == "joke"
        assert "text" in body and body["text"]
