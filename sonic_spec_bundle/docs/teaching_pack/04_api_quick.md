# API Quick Reference

**Auth:** `Authorization: Bearer <token>`  
**Base URL (dev):** `http://localhost:8000`

## Orders
- `GET /orders?status=open|closed`
- `POST /orders` (body: `schemas/order_create.json`)

## Positions
- `GET /positions/{id}`
- `POST /positions/{id}/adjust` (body: `schemas/position_adjust.json`)

## Alerts
- `POST /alerts` (body: `schemas/alert_create.json`)
