"""API route definitions for the Sonic1 backend."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/placeholder")
async def placeholder_endpoint():
    """Placeholder API endpoint."""
    return {"message": "placeholder"}
