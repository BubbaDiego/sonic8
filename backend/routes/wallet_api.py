from fastapi import APIRouter, Depends, HTTPException
from backend.models.wallet import Wallet
from backend.data.data_locker import DataLocker
from backend.core.wallet_core import WalletCore
from backend.deps import get_locker

router = APIRouter(prefix="/wallets", tags=["wallets"])

@router.get("/", response_model=list[dict])
def list_wallets(dl: DataLocker = Depends(get_locker)):
    """Return wallets without forcing a balance refresh."""
    return dl.read_wallets()

@router.post("/", status_code=201)
def create_wallet(wallet: Wallet, dl: DataLocker = Depends(get_locker)):
    try:
        dl.create_wallet(wallet.dict())
    except Exception as exc:
        raise HTTPException(500, "Insert failed") from exc
    return {"status": "created"}

@router.put("/{name}")
def update_wallet(name: str, wallet: Wallet, dl: DataLocker = Depends(get_locker)):
    try:
        dl.update_wallet(name, wallet.dict())
    except Exception as exc:
        raise HTTPException(500, "Update failed") from exc
    return {"status": "updated"}

@router.delete("/{name}")
def delete_wallet(name: str, dl: DataLocker = Depends(get_locker)):
    try:
        dl.wallets.delete_wallet(name)
    except Exception as exc:
        raise HTTPException(500, "Delete failed") from exc
    return {"status": "deleted"}

@router.post("/star_wars", status_code=201)
def insert_star_wars_wallets_route(dl: DataLocker = Depends(get_locker)):
    """Insert sample Star Wars wallets via helper script."""
    try:
        count = WalletCore().insert_star_wars_wallets()
    except Exception as exc:
        raise HTTPException(500, "Insert failed") from exc
    return {"status": "inserted", "count": count}
