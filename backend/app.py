from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.positions_api import router as positions_router
from routes.portfolio_api import router as portfolio_router
from routes.cyclone_api import router as cyclone_router

app = FastAPI(title="Sonic1 API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(positions_router)
app.include_router(portfolio_router)
app.include_router(cyclone_router)

@app.get("/api/status")
async def status():
    return {"status": "FastAPI backend online 🚀"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="0.0.0.0", port=5000, reload=True)
