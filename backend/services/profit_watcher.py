from __future__ import annotations
import os, threading, time
from dataclasses import dataclass
from typing import List, Tuple
from solders.keypair import Keypair
from backend.services.signer_loader import load_signer
from backend.services.jupiter_swap import get_quote, build_swap_tx, sign_and_send

@dataclass
class PairCfg:
    a_mint: str
    b_mint: str
    a_dec: int
    size_a_atoms: int
    min_edge_bps: int = 60  # trigger threshold

DEFAULT_PAIRS: List[PairCfg] = [
    PairCfg("So11111111111111111111111111111111111111112","EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",9,int(0.1 * 10**9),60), # SOL↔USDC
    PairCfg("So11111111111111111111111111111111111111112","mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",9,int(0.1 * 10**9),60),   # SOL↔mSOL
    PairCfg("So11111111111111111111111111111111111111112","J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",9,int(0.1 * 10**9),60), # SOL↔JitoSOL
]

class ProfitWatcher:
    def __init__(self, pairs: List[PairCfg] = None, slippage_bps: int = 50, poll_ms: int = 1500):
        self.pairs = pairs or DEFAULT_PAIRS
        self.slippage = slippage_bps
        self.poll_ms = poll_ms
        self._thr = None
        self._stop = threading.Event()
        self._last_edge = {}  # (a,b) -> bps
        self._sig_last = None

    def start(self):
        if self._thr and self._thr.is_alive(): return
        self._stop.clear()
        self._thr = threading.Thread(target=self._run, daemon=True)
        self._thr.start()

    def stop(self):
        self._stop.set()
        if self._thr: self._thr.join(timeout=1.0)

    def status(self):
        return {"running": self._thr.is_alive() if self._thr else False, "lastEdgeBps": self._last_edge, "lastSig": self._sig_last}

    def _run(self):
        wallet: Keypair = load_signer()
        while not self._stop.is_set():
            for p in self.pairs:
                try:
                    # A->B
                    q1 = get_quote(input_mint=p.a_mint, output_mint=p.b_mint, amount=p.size_a_atoms,
                                   swap_mode="ExactIn", slippage_bps=self.slippage, restrict_intermediates=True)
                    min_out_b = int(q1["otherAmountThreshold"])
                    # B->A
                    q2 = get_quote(input_mint=p.b_mint, output_mint=p.a_mint, amount=min_out_b,
                                   swap_mode="ExactIn", slippage_bps=self.slippage, restrict_intermediates=True)
                    min_out_a = int(q2["otherAmountThreshold"])
                    edge_bps = int((min_out_a - p.size_a_atoms) * 10000 / p.size_a_atoms)
                    self._last_edge[(p.a_mint,p.b_mint)] = edge_bps

                    if edge_bps >= p.min_edge_bps:
                        # Fire A->B then B->A with strict thresholds embedded by Jupiter
                        tx1 = build_swap_tx(quote_response=q1, user_pubkey=str(wallet.pubkey()))
                        sig1 = sign_and_send(tx1.get("swapTransaction") or tx1.get("transaction"), wallet)["signature"]
                        tx2 = build_swap_tx(quote_response=q2, user_pubkey=str(wallet.pubkey()))
                        sig2 = sign_and_send(tx2.get("swapTransaction") or tx2.get("transaction"), wallet)["signature"]
                        self._sig_last = {"a_to_b": sig1, "b_to_a": sig2}
                        time.sleep(0.5)  # brief cool-down
                except Exception as e:
                    # keep going; add logging in your project pattern
                    pass
                if self._stop.is_set(): break
            self._stop.wait(self.poll_ms / 1000.0)

WATCHER = ProfitWatcher()
