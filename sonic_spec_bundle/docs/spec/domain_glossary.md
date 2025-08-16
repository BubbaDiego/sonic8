# Domain Glossary (Sonic)

> One factual definition per term. Link to the canonical type or schema.

- **Account** — A user’s authenticated identity; see `core/models/account.py` and `schemas/account.json`.
- **Position** — [Your definition].
- **Order** — [Your definition]; see `schemas/order.json`, `POST /orders`.
- **Signal** — [Your definition]; invariants in `workflows.md#signals`.
- **Strategy** — [Your definition]; lifecycle in `workflows.md#strategies`.
- **Alert** — [Your definition]; schema `schemas/alert_create.json`.

_Seed Q&A_
- **Q:** Can an Order exist without a Position?  
  **A:** [Yes/No]. If creating without a Position, use `orders.create` with `link=false`.
