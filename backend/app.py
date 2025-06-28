# backend/app.py
from fastapi import FastAPI

app = FastAPI(title="Sonic1 API")

@app.get("/api/status")
async def status():
    return {"status": "FastAPI backend online 🚀"}

# To run directly:
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True)
