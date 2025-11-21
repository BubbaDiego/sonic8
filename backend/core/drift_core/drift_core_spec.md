# Drift Core – Sonic Integration Spec (scaffold)

> NOTE: This file is a high-level design doc for the new Drift Core module.
> It intentionally describes behavior at a conceptual level. The initial
> implementation is scaffolding only.

## 1. Purpose

Drift Core is responsible for integrating the Drift Protocol (perpetual
futures on Solana) into Sonic. It focuses on:

- Connecting to Drift using the official `driftpy` Python SDK.
- Exposing a clean, testable service API (`DriftCoreService`) for
  consoles, HTTP routes and monitors.
- Mapping Drift positions/markets into Sonic's existing persistence model
  using `DataLocker`.

## 2. Components

- `DriftConfig` – loads RPC URL / wallet secret settings from environment.
- `DriftClientWrapper` – thin wrapper around `driftpy.DriftClient`.
- `DriftStore` – writes/reads Drift-derived data via `DataLocker`.
- `DriftSyncService` – orchestrates one-shot sync flows from Drift into the DB.
- `DriftCore` – main orchestrator shared by other modules.
- `DriftCoreService` – narrow external interface for routes/monitors/CLI.
- `drift_console` – small CLI for operator workflows and debugging.

## 3. Non-goals (for now)

- No direct use of raw Solana transactions; all calls go through `driftpy`.
- No custom risk engine or portfolio logic; Drift Core only feeds Sonic.
- No UI components; the React app can talk to Drift Core via API later.

## 4. Follow-up work

- Implement `DriftClientWrapper.connect` and the market/position fetch calls.
- Wire `DriftStore` to the concrete `DataLocker` APIs for positions and
  any Drift-specific tables.
- Add a small FastAPI router that uses `DriftCoreService` (separate file).
- Expand `drift_console` commands once the core flows are stable.
