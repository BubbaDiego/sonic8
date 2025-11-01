# GMX-Solana Core — Phase S-1

Goal: provide a Solana-first integration scaffold (no EVM shims) with a
dependency-free console that validates config & basic imports.

Phase S-1:
- Package layout
- solana.yaml config template (ENV resolution)
- console with ping/config/smoke

Phase S-2 (next):
- Anchor IDL loading via anchorpy or solana-py
- Implement `position_source_solana.list_open_positions(wallet)`
- Map on-chain accounts → NormalizedPosition
- DL writer integration, tests, reconcile job

Runbook:
- Branch: codex/gmx_solana_core_phase_s1
- Commit: add scaffold, remove old EVM gmx_core
- CI: run tests under tests/gmx_solana_core
