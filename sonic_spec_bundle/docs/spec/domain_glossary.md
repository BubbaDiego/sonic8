# Domain Glossary (Sonic)

> One factual definition per term. Link to the canonical type or schema.

- **Account** — A user’s authenticated identity; see `backend/models/trader.py`.
- **Position** — Snapshot of an open derivative contract including asset, size, and leverage; see `backend/models/position.py`.
- **Order** — Instruction to buy or sell an instrument; see `schemas/order.json`, `POST /orders`.
- **Signal** — Programmatic indicator derived from market data or strategy evaluation; invariants in `workflows.md#signals`.
- **Strategy** — Algorithmic ruleset that emits Signals and manages Positions; lifecycle in `workflows.md#strategies`.
- **Alert** — Notification rule that evaluates conditions and dispatches messages; schema `schemas/alert_create.json`.

_Seed Q&A_
- **Q:** Can an Order exist without a Position?
  **A:** Yes. If creating without a Position, use `orders.create` with `link=false`.
