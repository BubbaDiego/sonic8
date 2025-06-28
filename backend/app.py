from fastapi import FastAPI
from routes.positions_api import router as positions_router

app = FastAPI(title="Sonic1 API")
app.include_router(positions_router)

@app.get("/api/status")
async def status():
    return {"status": "FastAPI backend online 🚀"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True)