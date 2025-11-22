"""
WalletCore module
=================

High-level orchestrator for wallet operations.

This class loads wallets through ``WalletService`` and provides helper
methods for interacting with the Solana blockchain via ``solana-py``.
It does not replace existing services or repositories but delegates
persistence to them while offering convenience methods like
``fetch_balance`` and ``send_transaction``.
"""

from __future__ import annotations

from typing import List, Optional

from dataclasses import dataclass


import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))



from backend.core.logging import log

try:  # optional dependency
    from solana.rpc.api import Client
    from solana.transaction import Transaction
    from solana.keypair import Keypair
    from solders.pubkey import Pubkey
    from solana.rpc.commitment import Confirmed
    from solana.rpc.types import TxOpts

except Exception as e:  # pragma: no cover - gracefully handle missing deps
    log.warning(f"Failed to import solana/solders: {e}", source="WalletCore")
    Client = None  # type: ignore
    Transaction = object  # type: ignore
    Keypair = object  # type: ignore
    Pubkey = object  # type: ignore
    Confirmed = None  # type: ignore
    TxOpts = object  # type: ignore


#from wallets.blockchain_balance_service import BlockchainBalanceService
#from wallets.jupiter_service import JupiterService
#from wallets.jupiter_trigger_service import JupiterTriggerService
from backend.data.data_locker import DataLocker
from backend.data.dl_wallets import DLWalletManager
from backend.core.positions_core.position_core import PositionCore
from backend.core.wallet_core.signer_store import SignerStore, WalletSigner
from backend.core.wallet_core.wallet_service import WalletService
from backend.models.wallet import Wallet


@dataclass
class WalletSummary:
    """
    Lightweight view of a wallet suitable for console / Launch Pad menus.
    """

    wallet_id: str
    label: str
    public_key: str
    active: bool = True

LAMPORTS_PER_SOL = 1_000_000_000


class WalletCore:
    """Central access point for wallet + blockchain operations."""

    def __init__(
        self,
        rpc_endpoint: str = "https://api.mainnet-beta.solana.com",
        dl: Optional[DataLocker] = None,
        *,
        signer_store: Optional[SignerStore] = None,
    ):
        self._dl = dl or DataLocker.get_instance()
        self._signers = signer_store or SignerStore.from_env()
        self._wallet_store = DLWalletManager(self._dl.db) if getattr(self._dl, "db", None) else None

        self.service = WalletService()
       # self.rpc_endpoint = rpc_endpoint
      #  self.client = Client(rpc_endpoint) if Client else None
        # Instantiate BlockchainBalanceService regardless of solana availability
        # so ``load_wallets`` can gracefully attempt balance lookups.
#        self.balance_service = BlockchainBalanceService()
        self.jupiter = None
        self.jupiter_trigger = None
      #  log.debug(
    #        f"WalletCore initialized with RPC {rpc_endpoint}" + (" (stubbed)" if Client is None else ""),
   #         source="WalletCore",
    #    )

    # ------------------------------------------------------------------
    # Data access helpers
    # ------------------------------------------------------------------
    def get_active_wallets(self) -> List[WalletSummary]:
        """
        Return a list of wallets that are considered 'active' in Sonic.

        Implementation should:

        - Use the existing wallet DL / repository to load all wallets.
        - Filter to whatever the current 'active' flag is (e.g., is_active, enabled, etc.).
        - Join with SignerStore where possible so we can provide public_key even
          if the wallets table does not include it directly.

        This method must be safe to call even if there is only a single
        legacy wallet configured.
        """

        signers = {s.wallet_id: s for s in self._signers.list_signers()}
        try:
            wallets_out = self.service.list_wallets()
        except Exception:
            wallets_out = []

        summaries: List[WalletSummary] = []
        for wallet in wallets_out:
            is_active = bool(getattr(wallet, "is_active", True))
            if not is_active:
                continue

            signer = signers.get(wallet.name)
            public_key = getattr(wallet, "public_address", "") or (
                signer.public_key if signer else ""
            )
            label = getattr(wallet, "name", "")
            summaries.append(
                WalletSummary(
                    wallet_id=wallet.name,
                    label=label or wallet.name,
                    public_key=public_key,
                    active=is_active,
                )
            )

        return summaries

    def load_wallets(self) -> List[Wallet]:
        """Return all wallets from the repository as ``Wallet`` objects."""
        wallets_out = self.service.list_wallets()
        wallets = [Wallet(**w.dict()) for w in wallets_out]
        for w in wallets:
            bal = self.fetch_positions_balance(w.name)
            if bal is not None:
                w.balance = bal
        return wallets

    def get_wallet_signer(self, wallet_id: str) -> Optional[WalletSigner]:
        """
        Return the WalletSigner for the given wallet_id, or None if none is
        configured.

        This is the preferred way for other cores / consoles to obtain
        signing material for a specific wallet.
        """
        return self._signers.get_signer(wallet_id)

    def require_wallet_signer(self, wallet_id: str) -> WalletSigner:
        """
        Strict variant that raises KeyError if no signer exists.
        """
        return self._signers.require_signer(wallet_id)

    def get_passphrase_for_wallet(self, wallet_id: str) -> Optional[str]:
        """
        Convenience wrapper to fetch just the passphrase for a wallet, if any.
        """
        signer = self._signers.get_signer(wallet_id)
        return signer.passphrase if signer else None

    def set_rpc_endpoint(self, endpoint: str) -> None:
        """Switch to a different Solana RPC endpoint."""
        self.rpc_endpoint = endpoint
        if Client:
            self.client = Client(endpoint)
        log.debug(f"RPC endpoint switched to {endpoint}", source="WalletCore")

    # ------------------------------------------------------------------
    # Blockchain interaction helpers
    # ------------------------------------------------------------------
    def fetch_balance(self, wallet: Wallet) -> Optional[float]:
        """Fetch the SOL balance for ``wallet`` using the active client."""
        if not Client or not self.client:
            log.debug("fetch_balance skipped; solana client unavailable", source="WalletCore")
            return None
        try:
            resp = self.client.get_balance(
                Pubkey.from_string(wallet.public_address.strip()), commitment=Confirmed
            )
            lamports = resp.value
            if lamports is not None:
                return lamports / LAMPORTS_PER_SOL
        except Exception as e:
            log.error(f"Failed to fetch balance for {wallet.name}: {e}", source="WalletCore")
        return None

    def fetch_positions_balance(self, wallet_id: str) -> Optional[float]:
        """Return the total value of active positions for ``wallet_id``."""
        try:
            dl = DataLocker.get_instance()
            positions = PositionCore(dl).get_active_positions()
            total = 0.0
            for pos in positions:
                data = pos.dict() if hasattr(pos, "dict") else pos
                if str(data.get("wallet_name")) == str(wallet_id):
                    try:
                        total += float(data.get("value") or 0.0)
                    except Exception:
                        continue
            return round(total, 2)
        except Exception as e:
            log.error(f"Failed to fetch positions balance for {wallet_id}: {e}", source="WalletCore")
            return None

    def refresh_wallet_balance(self, wallet_id: str) -> bool:
        """Recalculate and persist balance for a single wallet."""
        try:
            dl = DataLocker.get_instance()
        except Exception as exc:  # pragma: no cover - best effort
            log.error(f"Failed to obtain DataLocker: {exc}", source="WalletCore")
            return False

        bal = self.fetch_positions_balance(wallet_id)
        if bal is None:
            return False
        wallet = dl.get_wallet_by_name(wallet_id)
        if not wallet:
            return False
        try:
            wallet["balance"] = bal
            dl.update_wallet(wallet_id, wallet)
            return True
        except Exception as exc:  # pragma: no cover - database errors
            log.error(f"Failed to refresh balance for {wallet_id}: {exc}", source="WalletCore")
            return False

    def refresh_wallet_balances(self) -> int:
        """Recalculate wallet balances from active positions and persist to the DB.

        Returns the number of wallets updated.
        """
        try:
            dl = DataLocker.get_instance()
        except Exception as exc:  # pragma: no cover - best effort
            log.error(f"Failed to obtain DataLocker: {exc}", source="WalletCore")
            return 0

        wallets = dl.read_wallets() if hasattr(dl, "read_wallets") else []
        updated = 0
        for w in wallets:
            if not w.get("is_active", True):
                continue
            bal = self.fetch_positions_balance(w.get("name"))
            if bal is None:
                continue
            try:
                w["balance"] = bal
                dl.update_wallet(w["name"], w)
                updated += 1
            except Exception as exc:  # pragma: no cover - database errors
                log.error(f"Failed to refresh balance for {w.get('name')}: {exc}", source="WalletCore")

        log.info(f"Refreshed balances for {updated} wallets", source="WalletCore")
        return updated

    def _keypair_from_wallet(self, wallet: Wallet) -> Keypair:
        if not Client or not wallet.private_address:
            raise ValueError("Wallet has no private key")
        try:
            import base58
            secret = base58.b58decode(wallet.private_address)
            return Keypair.from_secret_key(secret)
        except Exception:
            import base64
            secret = base64.b64decode(wallet.private_address)
            return Keypair.from_secret_key(secret)

    def send_transaction(self, wallet: Wallet, tx: Transaction) -> Optional[str]:
        """Sign and submit ``tx`` using ``wallet``'s keypair."""
        if not Client or not self.client:
            log.debug("send_transaction skipped; solana client unavailable", source="WalletCore")
            return None
        try:
            kp = self._keypair_from_wallet(wallet)
            recent = self.client.get_recent_blockhash()["result"]["value"]["blockhash"]
            tx.recent_blockhash = recent
            tx.sign(kp)
            resp = self.client.send_transaction(tx, kp, opts=TxOpts(preflight_commitment=Confirmed))
            sig = resp.get("result")
            if sig:
                log.success(f"Transaction sent: {sig}", source="WalletCore")
            return sig
        except Exception as e:
            log.error(f"Failed to send transaction from {wallet.name}: {e}", source="WalletCore")
            return None

    # ------------------------------------------------------------------
    # Jupiter collateral helpers
    # ------------------------------------------------------------------
    def deposit_collateral(self, wallet: Wallet, market: str, amount: float) -> Optional[dict]:
        """Deposit collateral into a Jupiter perpetual position."""
        if not Client or not self.jupiter:
            log.debug("deposit_collateral skipped; solana client unavailable", source="WalletCore")
            return None
        try:
            result = self.jupiter.increase_position(wallet.public_address, market, amount)
            log.info(
                f"Deposited {amount} to {market} for {wallet.name}",
                source="WalletCore",
            )
            return result
        except Exception as e:  # pragma: no cover - network failures
            log.error(f"Deposit failed for {wallet.name}: {e}", source="WalletCore")
            return None

    def withdraw_collateral(self, wallet: Wallet, market: str, amount: float) -> Optional[dict]:
        """Withdraw collateral from a Jupiter perpetual position."""
        if not Client or not self.jupiter:
            log.debug("withdraw_collateral skipped; solana client unavailable", source="WalletCore")
            return None
        try:
            result = self.jupiter.decrease_position(wallet.public_address, market, amount)
            log.info(
                f"Withdrew {amount} from {market} for {wallet.name}",
                source="WalletCore",
            )
            return result
        except Exception as e:  # pragma: no cover - network failures
            log.error(f"Withdraw failed for {wallet.name}: {e}", source="WalletCore")
            return None

    def place_trigger_order(
        self,
        wallet: Wallet,
        market: str,
        trigger_price: float,
        size: float,
        is_long: bool,
    ) -> Optional[str]:
        """Create a trigger order and send the resulting transaction."""
        if not Client or not self.jupiter_trigger:
            log.debug("place_trigger_order skipped; solana client unavailable", source="WalletCore")
            return None
        try:
            resp = self.jupiter_trigger.create_trigger_order(
                wallet.public_address,
                market,
                trigger_price,
                size,
                is_long,
            )
            tx_data = resp.get("transaction")
            if not tx_data:
                log.error("Trigger order response missing transaction", source="WalletCore")
                return None
            tx_obj = None
            if isinstance(tx_data, Transaction):
                tx_obj = tx_data
            else:
                try:
                    import base64
                    tx_obj = Transaction.deserialize(base64.b64decode(tx_data))
                except Exception as exc:
                    log.error(f"Failed to decode trigger transaction: {exc}", source="WalletCore")
                    return None
            return self.send_transaction(wallet, tx_obj)
        except Exception as e:  # pragma: no cover - network failures
            log.error(f"Trigger order failed for {wallet.name}: {e}", source="WalletCore")
            return None

    def insert_star_wars_wallets(self) -> int:
        """Load Star Wars themed wallets via the helper script."""
        try:
            from scripts.insert_star_wars_wallets import insert_star_wars_wallets

            return insert_star_wars_wallets()
        except Exception as e:  # pragma: no cover - best effort
            log.error(f"Failed to inject Star Wars wallets: {e}", source="WalletCore")
            return 0

    def delete_all_wallets(self) -> None:
        """Remove all wallets from persistent storage."""
        try:
            self.service.delete_all_wallets()
            log.success("All wallets deleted via WalletCore", source="WalletCore")
        except Exception as e:
            log.error(f"Failed to delete all wallets: {e}", source="WalletCore")


__all__ = [
    "WalletCore",
    "WalletSummary",
    "WalletSigner",
    "SignerStore",
]

