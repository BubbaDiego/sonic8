from fastapi import APIRouter, Depends, HTTPException
from backend.models.wallet import Wallet
from data.data_locker import DataLocker

router = APIRouter(prefix="/wallets", tags=["wallets"])


def _dl() -> DataLocker:
    return DataLocker.get_instance()


@router.get("/", response_model=list[dict])
def list_wallets(dl: DataLocker = Depends(_dl)):
    return dl.read_wallets()


@router.post("/", status_code=201)
def create_wallet(wallet: Wallet, dl: DataLocker = Depends(_dl)):
    try:
        dl.create_wallet(wallet.dict())
    except Exception as exc:  # pragma: no cover - safety
        raise HTTPException(500, "Insert failed") from exc
    return {"status": "created"}


@router.put("/{name}")
def update_wallet(name: str, wallet: Wallet, dl: DataLocker = Depends(_dl)):
    try:
        dl.update_wallet(name, wallet.dict())
    except Exception as exc:  # pragma: no cover - safety
        raise HTTPException(500, "Update failed") from exc
    return {"status": "updated"}


@router.delete("/{name}")
def delete_wallet(name: str, dl: DataLocker = Depends(_dl)):
    try:
        dl.wallets.delete_wallet(name)
    except Exception as exc:  # pragma: no cover - safety
        raise HTTPException(500, "Delete failed") from exc
    return {"status": "deleted"}
