# Core Workflows (Quick)

- Create Order → `POST /orders` (idempotent)
- Adjust Position → `POST /positions/{id}/adjust`
- Emit Alert → `POST /alerts`

**Invariant highlights**
- Orders require Account.
- Adjustments must maintain min collateral.
- All writes accept `Idempotency-Key`.
