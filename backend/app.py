"""Main entry point for the Sonic1 backend application."""

from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
