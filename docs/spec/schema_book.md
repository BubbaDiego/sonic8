# Sonic Schema Book — Teaching Bundle

> Generated: 2025-09-20 17:09:11 UTC  
> Source: `docs/spec/spec.manifest.yaml`  
> Note: This file consolidates many repo schemas into one for *teaching*. In the repository, each schema lives as its own JSON file.

## API ⇄ Schema index

| Method | Path | Schema ID |
|---|---|---|
| `GET` | `/alert_thresholds/` | `SCHEMA-ALERT_THRESHOLDS` |
| `POST` | `/alert_thresholds/` | `SCHEMA-ALERT_THRESHOLDS` |
| `GET` | `/alert_thresholds/bulk` | `SCHEMA-ALERT_THRESHOLDS_BULK` |
| `PUT` | `/alert_thresholds/bulk` | `SCHEMA-ALERT_THRESHOLDS_BULK` |
| `GET` | `/alert_thresholds/{threshold_id}` | `SCHEMA-ALERT_THRESHOLDS_{THRESHOLD_ID}` |
| `PUT` | `/alert_thresholds/{threshold_id}` | `SCHEMA-ALERT_THRESHOLDS_{THRESHOLD_ID}` |
| `DELETE` | `/alert_thresholds/{threshold_id}` | `SCHEMA-ALERT_THRESHOLDS_{THRESHOLD_ID}` |
| `POST` | `/alerts/create_all` | `SCHEMA-ALERTS_CREATE_ALL` |
| `POST` | `/alerts/delete_all` | `SCHEMA-ALERTS_DELETE_ALL` |
| `GET` | `/alerts/monitor` | `SCHEMA-ALERTS_MONITOR` |
| `POST` | `/alerts/refresh` | `SCHEMA-ALERTS_REFRESH` |
| `POST` | `/api/auto-core/close-browser` | `SCHEMA-API_AUTO-CORE_CLOSE-BROWSER` |
| `POST` | `/api/auto-core/connect-jupiter` | `SCHEMA-API_AUTO-CORE_CONNECT-JUPITER` |
| `GET` | `/api/auto-core/jupiter-status` | `SCHEMA-API_AUTO-CORE_JUPITER-STATUS` |
| `POST` | `/api/auto-core/open-browser` | `SCHEMA-API_AUTO-CORE_OPEN-BROWSER` |
| `POST` | `/api/auto-core/register-wallet-address` | `SCHEMA-API_AUTO-CORE_REGISTER-WALLET-ADDRESS` |
| `POST` | `/api/auto-core/run-request` | `SCHEMA-API_AUTO-CORE_RUN-REQUEST` |
| `POST` | `/api/auto-core/select-asset` | `SCHEMA-API_AUTO-CORE_SELECT-ASSET` |
| `POST` | `/api/auto-core/solflare-unlock` | `SCHEMA-API_AUTO-CORE_SOLFLARE-UNLOCK` |
| `GET` | `/api/auto-core/wallet-address` | `SCHEMA-API_AUTO-CORE_WALLET-ADDRESS` |
| `GET` | `/api/fun/random` | `SCHEMA-API_FUN_RANDOM` |
| `POST` | `/api/jupiter/close` | `SCHEMA-API_JUPITER_CLOSE` |
| `POST` | `/api/jupiter/connect` | `SCHEMA-API_JUPITER_CONNECT` |
| `GET` | `/api/jupiter/debug-paths` | `SCHEMA-API_JUPITER_DEBUG-PATHS` |
| `GET` | `/api/jupiter/debug/config` | `SCHEMA-API_JUPITER_DEBUG_CONFIG` |
| `GET` | `/api/jupiter/debug/signer` | `SCHEMA-API_JUPITER_DEBUG_SIGNER` |
| `GET` | `/api/jupiter/health` | `SCHEMA-API_JUPITER_HEALTH` |
| `POST` | `/api/jupiter/open` | `SCHEMA-API_JUPITER_OPEN` |
| `GET` | `/api/jupiter/price` | `SCHEMA-API_JUPITER_PRICE` |
| `POST` | `/api/jupiter/select-asset` | `SCHEMA-API_JUPITER_SELECT-ASSET` |
| `GET` | `/api/jupiter/signer/info` | `SCHEMA-API_JUPITER_SIGNER_INFO` |
| `GET` | `/api/jupiter/status` | `SCHEMA-API_JUPITER_STATUS` |
| `POST` | `/api/jupiter/swap/execute` | `SCHEMA-API_JUPITER_SWAP_EXECUTE` |
| `POST` | `/api/jupiter/swap/quote` | `SCHEMA-API_JUPITER_SWAP_QUOTE` |
| `POST` | `/api/jupiter/trigger/cancel` | `SCHEMA-API_JUPITER_TRIGGER_CANCEL` |
| `POST` | `/api/jupiter/trigger/create` | `SCHEMA-API_JUPITER_TRIGGER_CREATE` |
| `GET` | `/api/jupiter/trigger/orders` | `SCHEMA-API_JUPITER_TRIGGER_ORDERS` |
| `GET` | `/api/jupiter/txlog` | `SCHEMA-API_JUPITER_TXLOG` |
| `GET` | `/api/jupiter/txlog/by-sig` | `SCHEMA-API_JUPITER_TXLOG_BY-SIG` |
| `GET` | `/api/jupiter/txlog/latest` | `SCHEMA-API_JUPITER_TXLOG_LATEST` |
| `GET` | `/api/jupiter/wallet/balance` | `SCHEMA-API_JUPITER_WALLET_BALANCE` |
| `GET` | `/api/jupiter/wallet/estimate-sol-spend` | `SCHEMA-API_JUPITER_WALLET_ESTIMATE-SOL-SPEND` |
| `GET` | `/api/jupiter/wallet/portfolio` | `SCHEMA-API_JUPITER_WALLET_PORTFOLIO` |
| `POST` | `/api/jupiter/wallet/preflight-send` | `SCHEMA-API_JUPITER_WALLET_PREFLIGHT-SEND` |
| `POST` | `/api/jupiter/wallet/send` | `SCHEMA-API_JUPITER_WALLET_SEND` |
| `GET` | `/api/jupiter/whoami` | `SCHEMA-API_JUPITER_WHOAMI` |
| `GET` | `/api/liquidation/nearest-distance` | `SCHEMA-API_LIQUIDATION_NEAREST-DISTANCE` |
| `GET` | `/api/market/latest` | `SCHEMA-API_MARKET_LATEST` |
| `GET` | `/api/monitor-settings/liquidation` | `SCHEMA-API_MONITOR-SETTINGS_LIQUIDATION` |
| `POST` | `/api/monitor-settings/liquidation` | `SCHEMA-API_MONITOR-SETTINGS_LIQUIDATION` |
| `GET` | `/api/monitor-settings/market` | `SCHEMA-API_MONITOR-SETTINGS_MARKET` |
| `POST` | `/api/monitor-settings/market` | `SCHEMA-API_MONITOR-SETTINGS_MARKET` |
| `POST` | `/api/monitor-settings/market/reset-anchors` | `SCHEMA-API_MONITOR-SETTINGS_MARKET_RESET-ANCHORS` |
| `GET` | `/api/monitor-settings/profit` | `SCHEMA-API_MONITOR-SETTINGS_PROFIT` |
| `POST` | `/api/monitor-settings/profit` | `SCHEMA-API_MONITOR-SETTINGS_PROFIT` |
| `GET` | `/api/monitor-settings/sonic` | `SCHEMA-API_MONITOR-SETTINGS_SONIC` |
| `POST` | `/api/monitor-settings/sonic` | `SCHEMA-API_MONITOR-SETTINGS_SONIC` |
| `POST` | `/api/monitor-status/reset-liquid-snooze` | `SCHEMA-API_MONITOR-STATUS_RESET-LIQUID-SNOOZE` |
| `GET` | `/api/monitor-status/{monitor_type}` | `SCHEMA-API_MONITOR-STATUS_{MONITOR_TYPE}` |
| `POST` | `/api/monitor-status/{monitor_type}` | `SCHEMA-API_MONITOR-STATUS_{MONITOR_TYPE}` |
| `GET` | `/api/notifications/` | `SCHEMA-API_NOTIFICATIONS` |
| `POST` | `/api/notifications/mark_all_read` | `SCHEMA-API_NOTIFICATIONS_MARK_ALL_READ` |
| `GET` | `/api/notifications/unread-count` | `SCHEMA-API_NOTIFICATIONS_UNREAD-COUNT` |
| `POST` | `/api/notifications/{notif_id}/read` | `SCHEMA-API_NOTIFICATIONS_{NOTIF_ID}_READ` |
| `POST` | `/api/perps/close` | `SCHEMA-API_PERPS_CLOSE` |
| `GET` | `/api/perps/debug/idl` | `SCHEMA-API_PERPS_DEBUG_IDL` |
| `GET` | `/api/perps/debug/idl-inspect` | `SCHEMA-API_PERPS_DEBUG_IDL-INSPECT` |
| `GET` | `/api/perps/debug/idl-names` | `SCHEMA-API_PERPS_DEBUG_IDL-NAMES` |
| `GET` | `/api/perps/debug/owner-offset` | `SCHEMA-API_PERPS_DEBUG_OWNER-OFFSET` |
| `GET` | `/api/perps/markets` | `SCHEMA-API_PERPS_MARKETS` |
| `GET` | `/api/perps/markets/resolve` | `SCHEMA-API_PERPS_MARKETS_RESOLVE` |
| `POST` | `/api/perps/order` | `SCHEMA-API_PERPS_ORDER` |
| `POST` | `/api/perps/order/close` | `SCHEMA-API_PERPS_ORDER_CLOSE` |
| `POST` | `/api/perps/order/open` | `SCHEMA-API_PERPS_ORDER_OPEN` |
| `GET` | `/api/perps/position/by-market` | `SCHEMA-API_PERPS_POSITION_BY-MARKET` |
| `GET` | `/api/perps/positions` | `SCHEMA-API_PERPS_POSITIONS` |
| `GET` | `/api/perps/positions/db` | `SCHEMA-API_PERPS_POSITIONS_DB` |
| `GET` | `/api/perps/positions/detailed` | `SCHEMA-API_PERPS_POSITIONS_DETAILED` |
| `GET` | `/api/perps/positions/detailed` | `SCHEMA-API_PERPS_POSITIONS_DETAILED` |
| `GET` | `/api/perps/positions/detailed` | `SCHEMA-API_PERPS_POSITIONS_DETAILED` |
| `GET` | `/api/perps/positions/health` | `SCHEMA-API_PERPS_POSITIONS_HEALTH` |
| `GET` | `/api/perps/positions/raw` | `SCHEMA-API_PERPS_POSITIONS_RAW` |
| `GET` | `/api/portfolio/latest_snapshot` | `SCHEMA-API_PORTFOLIO_LATEST_SNAPSHOT` |
| `POST` | `/api/portfolio/update_snapshot` | `SCHEMA-API_PORTFOLIO_UPDATE_SNAPSHOT` |
| `POST` | `/api/solana/balance` | `SCHEMA-API_SOLANA_BALANCE` |
| `GET` | `/api/status` | `SCHEMA-API_STATUS` |
| `GET` | `/api/traders/` | `SCHEMA-API_TRADERS` |
| `POST` | `/api/traders/` | `SCHEMA-API_TRADERS` |
| `GET` | `/api/traders/export` | `SCHEMA-API_TRADERS_EXPORT` |
| `POST` | `/api/traders/quick_import` | `SCHEMA-API_TRADERS_QUICK_IMPORT` |
| `GET` | `/api/traders/{name}` | `SCHEMA-API_TRADERS_{NAME}` |
| `PUT` | `/api/traders/{name}` | `SCHEMA-API_TRADERS_{NAME}` |
| `DELETE` | `/api/traders/{name}` | `SCHEMA-API_TRADERS_{NAME}` |
| `GET` | `/api/wallet/debug` | `SCHEMA-API_WALLET_DEBUG` |
| `POST` | `/api/wallet/send` | `SCHEMA-API_WALLET_SEND` |
| `POST` | `/api/wallets/verify` | `SCHEMA-API_WALLETS_VERIFY` |
| `POST` | `/api/wallets/verify-bulk` | `SCHEMA-API_WALLETS_VERIFY-BULK` |
| `DELETE` | `/cyclone/data` | `SCHEMA-CYCLONE_DATA` |
| `POST` | `/cyclone/positions` | `SCHEMA-CYCLONE_POSITIONS` |
| `POST` | `/cyclone/prices` | `SCHEMA-CYCLONE_PRICES` |
| `POST` | `/cyclone/run` | `SCHEMA-CYCLONE_RUN` |
| `GET` | `/db_admin/tables` | `SCHEMA-DB_ADMIN_TABLES` |
| `GET` | `/db_admin/tables/{table}` | `SCHEMA-DB_ADMIN_TABLES_{TABLE}` |
| `GET` | `/monitor_status/` | `SCHEMA-MONITOR_STATUS` |
| `GET` | `/monitors/` | `SCHEMA-MONITORS` |
| `POST` | `/monitors/sonic_cycle` | `SCHEMA-MONITORS_SONIC_CYCLE` |
| `GET` | `/monitors/sonic_events` | `SCHEMA-MONITORS_SONIC_EVENTS` |
| `POST` | `/monitors/{name}` | `SCHEMA-MONITORS_{NAME}` |
| `GET` | `/api/monitor-status/` | `SCHEMA-MONITORSTATUS` |
| `GET` | `/portfolio/latest` | `SCHEMA-PORTFOLIO` |
| `GET` | `/portfolio/` | `SCHEMA-PORTFOLIO` |
| `POST` | `/portfolio/` | `SCHEMA-PORTFOLIO` |
| `PUT` | `/portfolio/{entry_id}` | `SCHEMA-PORTFOLIO_{ENTRY_ID}` |
| `DELETE` | `/portfolio/{entry_id}` | `SCHEMA-PORTFOLIO_{ENTRY_ID}` |
| `GET` | `/positions/` | `SCHEMA-POSITIONS` |
| `POST` | `/positions/` | `SCHEMA-POSITIONS` |
| `POST` | `/positions/enrich` | `SCHEMA-POSITIONS_ENRICH` |
| `POST` | `/positions/snapshot` | `SCHEMA-POSITIONS_SNAPSHOT` |
| `POST` | `/positions/update` | `SCHEMA-POSITIONS_UPDATE` |
| `DELETE` | `/positions/{pos_id}` | `SCHEMA-POSITIONS_{POS_ID}` |
| `GET` | `/prices/` | `SCHEMA-PRICES` |
| `GET` | `/session/history` | `SCHEMA-SESSION_HISTORY` |
| `GET` | `/session/` | `SCHEMA-SESSION_STATE` |
| `POST` | `/session/` | `SCHEMA-SESSION_STATE` |
| `PUT` | `/session/` | `SCHEMA-SESSION_STATE` |
| `POST` | `/session/reset` | `SCHEMA-SESSION_STATE` |
| `POST` | `/session/close` | `SCHEMA-SESSION_STATE` |
| `PUT` | `/session/{sid}` | `SCHEMA-SESSION_{SID}` |
| `GET` | `/wallets/` | `SCHEMA-WALLETS` |
| `POST` | `/wallets/` | `SCHEMA-WALLETS` |
| `POST` | `/wallets/star_wars` | `SCHEMA-WALLETS_STAR_WARS` |
| `PUT` | `/wallets/{name}` | `SCHEMA-WALLETS_{NAME}` |
| `DELETE` | `/wallets/{name}` | `SCHEMA-WALLETS_{NAME}` |
| `GET` | `/xcom/last_ping` | `SCHEMA-XCOM_LAST_PING` |
| `GET` | `/xcom/providers` | `SCHEMA-XCOM_PROVIDERS` |
| `PUT` | `/xcom/providers` | `SCHEMA-XCOM_PROVIDERS` |
| `GET` | `/xcom/status` | `SCHEMA-XCOM_STATUS` |
| `POST` | `/xcom/test` | `SCHEMA-XCOM_TEST` |

## Table of Contents
- [SCHEMA-ALERT](#schema-alert)
- [SCHEMA-ALERT_THRESHOLDS](#schema-alert-thresholds)
- [SCHEMA-ALERT_THRESHOLDS_BULK](#schema-alert-thresholds-bulk)
- [SCHEMA-ALERT_THRESHOLDS_{THRESHOLD_ID}](#schema-alert-thresholds-{threshold-id})
- [SCHEMA-ALERTS_CREATE_ALL](#schema-alerts-create-all)
- [SCHEMA-ALERTS_DELETE_ALL](#schema-alerts-delete-all)
- [SCHEMA-ALERTS_MONITOR](#schema-alerts-monitor)
- [SCHEMA-ALERTS_REFRESH](#schema-alerts-refresh)
- [SCHEMA-API_AUTO-CORE_CLOSE-BROWSER](#schema-api-auto-core-close-browser)
- [SCHEMA-API_AUTO-CORE_CONNECT-JUPITER](#schema-api-auto-core-connect-jupiter)
- [SCHEMA-API_AUTO-CORE_JUPITER-STATUS](#schema-api-auto-core-jupiter-status)
- [SCHEMA-API_AUTO-CORE_OPEN-BROWSER](#schema-api-auto-core-open-browser)
- [SCHEMA-API_AUTO-CORE_REGISTER-WALLET-ADDRESS](#schema-api-auto-core-register-wallet-address)
- [SCHEMA-API_AUTO-CORE_RUN-REQUEST](#schema-api-auto-core-run-request)
- [SCHEMA-API_AUTO-CORE_SELECT-ASSET](#schema-api-auto-core-select-asset)
- [SCHEMA-API_AUTO-CORE_SOLFLARE-UNLOCK](#schema-api-auto-core-solflare-unlock)
- [SCHEMA-API_AUTO-CORE_WALLET-ADDRESS](#schema-api-auto-core-wallet-address)
- [SCHEMA-API_FUN_RANDOM](#schema-api-fun-random)
- [SCHEMA-API_JUPITER_CLOSE](#schema-api-jupiter-close)
- [SCHEMA-API_JUPITER_CONNECT](#schema-api-jupiter-connect)
- [SCHEMA-API_JUPITER_DEBUG-PATHS](#schema-api-jupiter-debug-paths)
- [SCHEMA-API_JUPITER_DEBUG_CONFIG](#schema-api-jupiter-debug-config)
- [SCHEMA-API_JUPITER_DEBUG_SIGNER](#schema-api-jupiter-debug-signer)
- [SCHEMA-API_JUPITER_HEALTH](#schema-api-jupiter-health)
- [SCHEMA-API_JUPITER_OPEN](#schema-api-jupiter-open)
- [SCHEMA-API_JUPITER_PRICE](#schema-api-jupiter-price)
- [SCHEMA-API_JUPITER_SELECT-ASSET](#schema-api-jupiter-select-asset)
- [SCHEMA-API_JUPITER_SIGNER_INFO](#schema-api-jupiter-signer-info)
- [SCHEMA-API_JUPITER_STATUS](#schema-api-jupiter-status)
- [SCHEMA-API_JUPITER_SWAP_EXECUTE](#schema-api-jupiter-swap-execute)
- [SCHEMA-API_JUPITER_SWAP_QUOTE](#schema-api-jupiter-swap-quote)
- [SCHEMA-API_JUPITER_TRIGGER_CANCEL](#schema-api-jupiter-trigger-cancel)
- [SCHEMA-API_JUPITER_TRIGGER_CREATE](#schema-api-jupiter-trigger-create)
- [SCHEMA-API_JUPITER_TRIGGER_ORDERS](#schema-api-jupiter-trigger-orders)
- [SCHEMA-API_JUPITER_TXLOG](#schema-api-jupiter-txlog)
- [SCHEMA-API_JUPITER_TXLOG_BY-SIG](#schema-api-jupiter-txlog-by-sig)
- [SCHEMA-API_JUPITER_TXLOG_LATEST](#schema-api-jupiter-txlog-latest)
- [SCHEMA-API_JUPITER_WALLET_BALANCE](#schema-api-jupiter-wallet-balance)
- [SCHEMA-API_JUPITER_WALLET_ESTIMATE-SOL-SPEND](#schema-api-jupiter-wallet-estimate-sol-spend)
- [SCHEMA-API_JUPITER_WALLET_PORTFOLIO](#schema-api-jupiter-wallet-portfolio)
- [SCHEMA-API_JUPITER_WALLET_PREFLIGHT-SEND](#schema-api-jupiter-wallet-preflight-send)
- [SCHEMA-API_JUPITER_WALLET_SEND](#schema-api-jupiter-wallet-send)
- [SCHEMA-API_JUPITER_WHOAMI](#schema-api-jupiter-whoami)
- [SCHEMA-API_LIQUIDATION_NEAREST-DISTANCE](#schema-api-liquidation-nearest-distance)
- [SCHEMA-API_MARKET_LATEST](#schema-api-market-latest)
- [SCHEMA-API_MONITOR-SETTINGS_LIQUIDATION](#schema-api-monitor-settings-liquidation)
- [SCHEMA-API_MONITOR-SETTINGS_MARKET](#schema-api-monitor-settings-market)
- [SCHEMA-API_MONITOR-SETTINGS_MARKET_RESET-ANCHORS](#schema-api-monitor-settings-market-reset-anchors)
- [SCHEMA-API_MONITOR-SETTINGS_PROFIT](#schema-api-monitor-settings-profit)
- [SCHEMA-API_MONITOR-SETTINGS_SONIC](#schema-api-monitor-settings-sonic)
- [SCHEMA-API_MONITOR-STATUS_RESET-LIQUID-SNOOZE](#schema-api-monitor-status-reset-liquid-snooze)
- [SCHEMA-API_MONITOR-STATUS_{MONITOR_TYPE}](#schema-api-monitor-status-{monitor-type})
- [SCHEMA-API_NOTIFICATIONS](#schema-api-notifications)
- [SCHEMA-API_NOTIFICATIONS_MARK_ALL_READ](#schema-api-notifications-mark-all-read)
- [SCHEMA-API_NOTIFICATIONS_UNREAD-COUNT](#schema-api-notifications-unread-count)
- [SCHEMA-API_NOTIFICATIONS_{NOTIF_ID}_READ](#schema-api-notifications-{notif-id}-read)
- [SCHEMA-API_PERPS_CLOSE](#schema-api-perps-close)
- [SCHEMA-API_PERPS_DEBUG_IDL](#schema-api-perps-debug-idl)
- [SCHEMA-API_PERPS_DEBUG_IDL-INSPECT](#schema-api-perps-debug-idl-inspect)
- [SCHEMA-API_PERPS_DEBUG_IDL-NAMES](#schema-api-perps-debug-idl-names)
- [SCHEMA-API_PERPS_DEBUG_OWNER-OFFSET](#schema-api-perps-debug-owner-offset)
- [SCHEMA-API_PERPS_MARKETS](#schema-api-perps-markets)
- [SCHEMA-API_PERPS_MARKETS_RESOLVE](#schema-api-perps-markets-resolve)
- [SCHEMA-API_PERPS_ORDER](#schema-api-perps-order)
- [SCHEMA-API_PERPS_ORDER_CLOSE](#schema-api-perps-order-close)
- [SCHEMA-API_PERPS_ORDER_OPEN](#schema-api-perps-order-open)
- [SCHEMA-API_PERPS_POSITION_BY-MARKET](#schema-api-perps-position-by-market)
- [SCHEMA-API_PERPS_POSITIONS](#schema-api-perps-positions)
- [SCHEMA-API_PERPS_POSITIONS_DB](#schema-api-perps-positions-db)
- [SCHEMA-API_PERPS_POSITIONS_DETAILED](#schema-api-perps-positions-detailed)
- [SCHEMA-API_PERPS_POSITIONS_HEALTH](#schema-api-perps-positions-health)
- [SCHEMA-API_PERPS_POSITIONS_RAW](#schema-api-perps-positions-raw)
- [SCHEMA-API_PORTFOLIO_LATEST_SNAPSHOT](#schema-api-portfolio-latest-snapshot)
- [SCHEMA-API_PORTFOLIO_UPDATE_SNAPSHOT](#schema-api-portfolio-update-snapshot)
- [SCHEMA-API_SOLANA_BALANCE](#schema-api-solana-balance)
- [SCHEMA-API_STATUS](#schema-api-status)
- [SCHEMA-API_TRADERS](#schema-api-traders)
- [SCHEMA-API_TRADERS_EXPORT](#schema-api-traders-export)
- [SCHEMA-API_TRADERS_QUICK_IMPORT](#schema-api-traders-quick-import)
- [SCHEMA-API_TRADERS_{NAME}](#schema-api-traders-{name})
- [SCHEMA-API_WALLET_DEBUG](#schema-api-wallet-debug)
- [SCHEMA-API_WALLET_SEND](#schema-api-wallet-send)
- [SCHEMA-API_WALLETS_VERIFY](#schema-api-wallets-verify)
- [SCHEMA-API_WALLETS_VERIFY-BULK](#schema-api-wallets-verify-bulk)
- [SCHEMA-CYCLONE_DATA](#schema-cyclone-data)
- [SCHEMA-CYCLONE_POSITIONS](#schema-cyclone-positions)
- [SCHEMA-CYCLONE_PRICES](#schema-cyclone-prices)
- [SCHEMA-CYCLONE_RUN](#schema-cyclone-run)
- [SCHEMA-DB_ADMIN_TABLES](#schema-db-admin-tables)
- [SCHEMA-DB_ADMIN_TABLES_{TABLE}](#schema-db-admin-tables-{table})
- [SCHEMA-MONITOR_STATUS](#schema-monitor-status)
- [SCHEMA-MONITORS](#schema-monitors)
- [SCHEMA-MONITORS_SONIC_CYCLE](#schema-monitors-sonic-cycle)
- [SCHEMA-MONITORS_SONIC_EVENTS](#schema-monitors-sonic-events)
- [SCHEMA-MONITORS_{NAME}](#schema-monitors-{name})
- [SCHEMA-MONITORSTATUS](#schema-monitorstatus)
- [SCHEMA-PORTFOLIO](#schema-portfolio)
- [SCHEMA-PORTFOLIO_{ENTRY_ID}](#schema-portfolio-{entry-id})
- [SCHEMA-POSITION](#schema-position)
- [SCHEMA-POSITIONS](#schema-positions)
- [SCHEMA-POSITIONS_ENRICH](#schema-positions-enrich)
- [SCHEMA-POSITIONS_SNAPSHOT](#schema-positions-snapshot)
- [SCHEMA-POSITIONS_UPDATE](#schema-positions-update)
- [SCHEMA-POSITIONS_{POS_ID}](#schema-positions-{pos-id})
- [SCHEMA-PRICES](#schema-prices)
- [SCHEMA-SESSION](#schema-session)
- [SCHEMA-SESSION_HISTORY](#schema-session-history)
- [SCHEMA-SESSION_STATE](#schema-session-state)
- [SCHEMA-SESSION_{SID}](#schema-session-{sid})
- [SCHEMA-WALLETS](#schema-wallets)
- [SCHEMA-WALLETS_STAR_WARS](#schema-wallets-star-wars)
- [SCHEMA-WALLETS_{NAME}](#schema-wallets-{name})
- [SCHEMA-XCOM_LAST_PING](#schema-xcom-last-ping)
- [SCHEMA-XCOM_PROVIDERS](#schema-xcom-providers)
- [SCHEMA-XCOM_STATUS](#schema-xcom-status)
- [SCHEMA-XCOM_TEST](#schema-xcom-test)

---

### SCHEMA-ALERT
**Used by:** _not mapped_

**Example**
```json
{
  "id": "evt_123",
  "type": "warning",
  "message": "SOL balance low for fees",
  "context": {
    "lamports": 13018072,
    "min": 10000000
  },
  "createdAt": "2025-09-11T19:49:10Z"
}
```

**Schema**
```json
{
  "$id": "schema/Alert.json",
  "type": "object",
  "required": [
    "id",
    "type",
    "message",
    "createdAt"
  ],
  "properties": {
    "id": {
      "type": "string"
    },
    "type": {
      "type": "string",
      "enum": [
        "warning",
        "error",
        "info"
      ]
    },
    "message": {
      "type": "string"
    },
    "context": {
      "type": "object",
      "additionalProperties": true
    },
    "createdAt": {
      "type": "string",
      "format": "date-time"
    }
  },
  "examples": [
    {
      "id": "evt_123",
      "type": "warning",
      "message": "SOL balance low for fees",
      "context": {
        "lamports": 13018072,
        "min": 10000000
      },
      "createdAt": "2025-09-11T19:49:10Z"
    }
  ]
}
```

---

### SCHEMA-ALERT_THRESHOLDS
**Used by:** `GET /alert_thresholds/`, `POST /alert_thresholds/`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/alert_thresholds.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-ALERT_THRESHOLDS_BULK
**Used by:** `GET /alert_thresholds/bulk`, `PUT /alert_thresholds/bulk`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/alert_thresholds_bulk.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-ALERT_THRESHOLDS_{THRESHOLD_ID}
**Used by:** `GET /alert_thresholds/{threshold_id}`, `PUT /alert_thresholds/{threshold_id}`, `DELETE /alert_thresholds/{threshold_id}`

**Example**
```json
{
  "status": "deleted"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    }
  },
  "required": [
    "status"
  ],
  "additionalProperties": true,
  "$id": "schema/alert_thresholds_{threshold_id}.json",
  "examples": [
    {
      "status": "deleted"
    }
  ]
}
```

---

### SCHEMA-ALERTS_CREATE_ALL
**Used by:** `POST /alerts/create_all`

**Example**
```json
{
  "success": true
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "success": {
      "type": "boolean"
    }
  },
  "additionalProperties": true,
  "$id": "schema/alerts_create_all.json",
  "examples": [
    {
      "success": true
    }
  ]
}
```

---

### SCHEMA-ALERTS_DELETE_ALL
**Used by:** `POST /alerts/delete_all`

**Example**
```json
{
  "success": true
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "success": {
      "type": "boolean"
    }
  },
  "additionalProperties": true,
  "$id": "schema/alerts_delete_all.json",
  "examples": [
    {
      "success": true
    }
  ]
}
```

---

### SCHEMA-ALERTS_MONITOR
**Used by:** `GET /alerts/monitor`

**Example**
```json
{
  "alerts": []
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "alerts": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/alerts_monitor.json",
  "examples": [
    {
      "alerts": []
    }
  ]
}
```

---

### SCHEMA-ALERTS_REFRESH
**Used by:** `POST /alerts/refresh`

**Example**
```json
{
  "success": true
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "success": {
      "type": "boolean"
    }
  },
  "additionalProperties": true,
  "$id": "schema/alerts_refresh.json",
  "examples": [
    {
      "success": true
    }
  ]
}
```

---

### SCHEMA-API_AUTO-CORE_CLOSE-BROWSER
**Used by:** `POST /api/auto-core/close-browser`

**Example**
```json
{
  "ok": true,
  "closed_pids": []
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "ok": {
      "type": "boolean"
    },
    "closed_pids": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_auto-core_close-browser.json",
  "examples": [
    {
      "ok": true,
      "closed_pids": []
    }
  ]
}
```

---

### SCHEMA-API_AUTO-CORE_CONNECT-JUPITER
**Used by:** `POST /api/auto-core/connect-jupiter`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_auto-core_connect-jupiter.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_AUTO-CORE_JUPITER-STATUS
**Used by:** `GET /api/auto-core/jupiter-status`

**Example**
```json
{
  "sessions": {}
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "sessions": {
      "type": "object",
      "properties": {},
      "additionalProperties": true
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_auto-core_jupiter-status.json",
  "examples": [
    {
      "sessions": {}
    }
  ]
}
```

---

### SCHEMA-API_AUTO-CORE_OPEN-BROWSER
**Used by:** `POST /api/auto-core/open-browser`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_auto-core_open-browser.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_AUTO-CORE_REGISTER-WALLET-ADDRESS
**Used by:** `POST /api/auto-core/register-wallet-address`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_auto-core_register-wallet-address.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_AUTO-CORE_RUN-REQUEST
**Used by:** `POST /api/auto-core/run-request`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_auto-core_run-request.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_AUTO-CORE_SELECT-ASSET
**Used by:** `POST /api/auto-core/select-asset`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_auto-core_select-asset.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_AUTO-CORE_SOLFLARE-UNLOCK
**Used by:** `POST /api/auto-core/solflare-unlock`

**Example**
```json
{
  "detail": "solflare_unlock_only step not available"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "string"
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_auto-core_solflare-unlock.json",
  "examples": [
    {
      "detail": "solflare_unlock_only step not available"
    }
  ]
}
```

---

### SCHEMA-API_AUTO-CORE_WALLET-ADDRESS
**Used by:** `GET /api/auto-core/wallet-address`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "query",
        "wallet_id"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_auto-core_wallet-address.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "query",
            "wallet_id"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_FUN_RANDOM
**Used by:** `GET /api/fun/random`

**Example**
```json
{
  "detail": "403 Forbidden"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "string"
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_fun_random.json",
  "examples": [
    {
      "detail": "403 Forbidden"
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_CLOSE
**Used by:** `POST /api/jupiter/close`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_close.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_CONNECT
**Used by:** `POST /api/jupiter/connect`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_connect.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_DEBUG-PATHS
**Used by:** `GET /api/jupiter/debug-paths`

**Example**
```json
{
  "repo_root": "/workspace/sonic5",
  "launcher": "/workspace/sonic5/auto_core/launcher/open_jupiter.py",
  "launcher_exists": false,
  "sessions_file": "/workspace/sonic5/auto_core/state/jupiter_sessions.json"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "repo_root": {
      "type": "string"
    },
    "launcher": {
      "type": "string"
    },
    "launcher_exists": {
      "type": "boolean"
    },
    "sessions_file": {
      "type": "string"
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_debug-paths.json",
  "examples": [
    {
      "repo_root": "/workspace/sonic5",
      "launcher": "/workspace/sonic5/auto_core/launcher/open_jupiter.py",
      "launcher_exists": false,
      "sessions_file": "/workspace/sonic5/auto_core/state/jupiter_sessions.json"
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_DEBUG_CONFIG
**Used by:** `GET /api/jupiter/debug/config`

**Example**
```json
{
  "SONIC_SIGNER_PATH": "signer.txt",
  "SONIC_MNEMONIC_DERIVE_CMD": "",
  "HELIUS_API_KEY_set": false,
  "RPC_URL": "",
  "resolvedRpcUrl": "https://api.mainnet-beta.solana.com",
  "JUP_BASE_URL": "https://lite-api.jup.ag",
  "JUP_API_KEY_set": false,
  "JITO_TIP_LAMPORTS": "0"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "SONIC_SIGNER_PATH": {
      "type": "string"
    },
    "SONIC_MNEMONIC_DERIVE_CMD": {
      "type": "string"
    },
    "HELIUS_API_KEY_set": {
      "type": "boolean"
    },
    "RPC_URL": {
      "type": "string"
    },
    "resolvedRpcUrl": {
      "type": "string"
    },
    "JUP_BASE_URL": {
      "type": "string"
    },
    "JUP_API_KEY_set": {
      "type": "boolean"
    },
    "JITO_TIP_LAMPORTS": {
      "type": "string"
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_debug_config.json",
  "examples": [
    {
      "SONIC_SIGNER_PATH": "signer.txt",
      "SONIC_MNEMONIC_DERIVE_CMD": "",
      "HELIUS_API_KEY_set": false,
      "RPC_URL": "",
      "resolvedRpcUrl": "https://api.mainnet-beta.solana.com",
      "JUP_BASE_URL": "https://lite-api.jup.ag",
      "JUP_API_KEY_set": false,
      "JITO_TIP_LAMPORTS": "0"
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_DEBUG_SIGNER
**Used by:** `GET /api/jupiter/debug/signer`

**Example**
```json
{
  "spec": "signer.txt",
  "cwd": "/workspace/sonic5",
  "module_dir": "/workspace/sonic5/backend/services",
  "candidates": [
    "/workspace/sonic5/signer.txt",
    "/workspace/sonic5/backend/services/signer.txt",
    "/workspace/sonic5/backend/signer.txt"
  ],
  "found": "",
  "exists": false,
  "error": "no candidate signer.txt found",
  "load_signer": {
    "ok": false,
    "error": "FileNotFoundError: Signer file not found: signer.txt. Tried: ['/workspace/sonic5/signer.txt', '/workspace/sonic5/backend/services/signer.txt', '/workspace/sonic5/backend/signer.txt']"
  }
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "spec": {
      "type": "string"
    },
    "cwd": {
      "type": "string"
    },
    "module_dir": {
      "type": "string"
    },
    "candidates": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "found": {
      "type": "string"
    },
    "exists": {
      "type": "boolean"
    },
    "error": {
      "type": "string"
    },
    "load_signer": {
      "type": "object",
      "properties": {
        "ok": {
          "type": "boolean"
        },
        "error": {
          "type": "string"
        }
      },
      "additionalProperties": true
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_debug_signer.json",
  "examples": [
    {
      "spec": "signer.txt",
      "cwd": "/workspace/sonic5",
      "module_dir": "/workspace/sonic5/backend/services",
      "candidates": [
        "/workspace/sonic5/signer.txt",
        "/workspace/sonic5/backend/services/signer.txt",
        "/workspace/sonic5/backend/signer.txt"
      ],
      "found": "",
      "exists": false,
      "error": "no candidate signer.txt found",
      "load_signer": {
        "ok": false,
        "error": "FileNotFoundError: Signer file not found: signer.txt. Tried: ['/workspace/sonic5/signer.txt', '/workspace/sonic5/backend/services/signer.txt', '/workspace/sonic5/backend/signer.txt']"
      }
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_HEALTH
**Used by:** `GET /api/jupiter/health`

**Example**
```json
{
  "ok": true,
  "triggerApi": true,
  "rpcUrl": "https://api.mainnet-beta.solana.com"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "ok": {
      "type": "boolean"
    },
    "triggerApi": {
      "type": "boolean"
    },
    "rpcUrl": {
      "type": "string"
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_health.json",
  "examples": [
    {
      "ok": true,
      "triggerApi": true,
      "rpcUrl": "https://api.mainnet-beta.solana.com"
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_OPEN
**Used by:** `POST /api/jupiter/open`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_open.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_PRICE
**Used by:** `GET /api/jupiter/price`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "query",
        "id"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_price.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "query",
            "id"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_SELECT-ASSET
**Used by:** `POST /api/jupiter/select-asset`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_select-asset.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_SIGNER_INFO
**Used by:** `GET /api/jupiter/signer/info`

**Example**
```json
{
  "method": "unknown",
  "path": "",
  "note": ""
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "method": {
      "type": "string"
    },
    "path": {
      "type": "string"
    },
    "note": {
      "type": "string"
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_signer_info.json",
  "examples": [
    {
      "method": "unknown",
      "path": "",
      "note": ""
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_STATUS
**Used by:** `GET /api/jupiter/status`

**Example**
```json
{}
```

**Schema**
```json
{
  "type": "object",
  "properties": {},
  "additionalProperties": true,
  "$id": "schema/api_jupiter_status.json",
  "examples": [
    {}
  ]
}
```

---

### SCHEMA-API_JUPITER_SWAP_EXECUTE
**Used by:** `POST /api/jupiter/swap/execute`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_swap_execute.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_SWAP_QUOTE
**Used by:** `POST /api/jupiter/swap/quote`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_swap_quote.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_TRIGGER_CANCEL
**Used by:** `POST /api/jupiter/trigger/cancel`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_trigger_cancel.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_TRIGGER_CREATE
**Used by:** `POST /api/jupiter/trigger/create`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_trigger_create.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_TRIGGER_ORDERS
**Used by:** `GET /api/jupiter/trigger/orders`

**Example**
```json
"Internal Server Error"
```

**Schema**
```json
{
  "$id": "schema/api_jupiter_trigger_orders.json",
  "type": "string",
  "description": "Plain-text error emitted when trigger order listing fails.",
  "examples": [
    "Internal Server Error"
  ]
}
```

---

### SCHEMA-API_JUPITER_TXLOG
**Used by:** `GET /api/jupiter/txlog`

**Example**
```json
{
  "items": []
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "items": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_txlog.json",
  "examples": [
    {
      "items": []
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_TXLOG_BY-SIG
**Used by:** `GET /api/jupiter/txlog/by-sig`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "query",
        "sig"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_txlog_by-sig.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "query",
            "sig"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_TXLOG_LATEST
**Used by:** `GET /api/jupiter/txlog/latest`

**Example**
```json
{
  "detail": "empty"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "string"
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_txlog_latest.json",
  "examples": [
    {
      "detail": "empty"
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_WALLET_BALANCE
**Used by:** `GET /api/jupiter/wallet/balance`

**Example**
```json
{
  "detail": "Signer file not found: signer.txt. Tried: ['/workspace/sonic5/signer.txt', '/workspace/sonic5/backend/services/signer.txt', '/workspace/sonic5/backend/signer.txt']"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "string"
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_wallet_balance.json",
  "examples": [
    {
      "detail": "Signer file not found: signer.txt. Tried: ['/workspace/sonic5/signer.txt', '/workspace/sonic5/backend/services/signer.txt', '/workspace/sonic5/backend/signer.txt']"
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_WALLET_ESTIMATE-SOL-SPEND
**Used by:** `GET /api/jupiter/wallet/estimate-sol-spend`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "query",
        "outMint"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_wallet_estimate-sol-spend.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "query",
            "outMint"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_WALLET_PORTFOLIO
**Used by:** `GET /api/jupiter/wallet/portfolio`

**Example**
```json
{
  "detail": "portfolio failed: Signer file not found: signer.txt. Tried: ['/workspace/sonic5/signer.txt', '/workspace/sonic5/backend/services/signer.txt', '/workspace/sonic5/backend/signer.txt']"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "string"
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_wallet_portfolio.json",
  "examples": [
    {
      "detail": "portfolio failed: Signer file not found: signer.txt. Tried: ['/workspace/sonic5/signer.txt', '/workspace/sonic5/backend/services/signer.txt', '/workspace/sonic5/backend/signer.txt']"
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_WALLET_PREFLIGHT-SEND
**Used by:** `POST /api/jupiter/wallet/preflight-send`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_wallet_preflight-send.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_WALLET_SEND
**Used by:** `POST /api/jupiter/wallet/send`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_wallet_send.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_JUPITER_WHOAMI
**Used by:** `GET /api/jupiter/whoami`

**Example**
```json
{
  "detail": "Failed to load signer: Signer file not found: signer.txt. Tried: ['/workspace/sonic5/signer.txt', '/workspace/sonic5/backend/services/signer.txt', '/workspace/sonic5/backend/signer.txt']"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "string"
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_jupiter_whoami.json",
  "examples": [
    {
      "detail": "Failed to load signer: Signer file not found: signer.txt. Tried: ['/workspace/sonic5/signer.txt', '/workspace/sonic5/backend/services/signer.txt', '/workspace/sonic5/backend/signer.txt']"
    }
  ]
}
```

---

### SCHEMA-API_LIQUIDATION_NEAREST-DISTANCE
**Used by:** `GET /api/liquidation/nearest-distance`

**Example**
```json
{
  "BTC": null,
  "ETH": null,
  "SOL": null
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "BTC": {
      "type": [
        "null",
        "string",
        "number",
        "object",
        "array",
        "boolean"
      ]
    },
    "ETH": {
      "type": [
        "null",
        "string",
        "number",
        "object",
        "array",
        "boolean"
      ]
    },
    "SOL": {
      "type": [
        "null",
        "string",
        "number",
        "object",
        "array",
        "boolean"
      ]
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_liquidation_nearest-distance.json",
  "examples": [
    {
      "BTC": null,
      "ETH": null,
      "SOL": null
    }
  ]
}
```

---

### SCHEMA-API_MARKET_LATEST
**Used by:** `GET /api/market/latest`

**Example**
```json
{
  "BTC": {
    "1h": {
      "pct_move": 0.0,
      "threshold": null,
      "trigger": null
    },
    "6h": {
      "pct_move": 0.0,
      "threshold": null,
      "trigger": null
    },
    "24h": {
      "pct_move": -4.1775,
      "threshold": null,
      "trigger": null
    }
  },
  "SOL": {
    "1h": {
      "pct_move": 0.0,
      "threshold": null,
      "trigger": null
    },
    "6h": {
      "pct_move": 0.0,
      "threshold": null,
      "trigger": null
    },
    "24h": {
      "pct_move": 1.8932,
      "threshold": null,
      "trigger": null
    }
  },
  "ETH": {
    "1h": {
      "pct_move": 0.0,
      "threshold": null,
      "trigger": null
    },
    "6h": {
      "pct_move": 0.0,
      "threshold": null,
      "trigger": null
    },
    "24h": {
      "pct_move": 18.6776,
      "threshold": null,
      "trigger": null
    }
  }
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "BTC": {
      "type": "object",
      "properties": {
        "1h": {
          "type": "object",
          "properties": {
            "pct_move": {
              "type": "number"
            },
            "threshold": {
              "type": [
                "null",
                "string",
                "number",
                "object",
                "array",
                "boolean"
              ]
            },
            "trigger": {
              "type": [
                "null",
                "string",
                "number",
                "object",
                "array",
                "boolean"
              ]
            }
          },
          "additionalProperties": true
        },
        "6h": {
          "type": "object",
          "properties": {
            "pct_move": {
              "type": "number"
            },
            "threshold": {
              "type": [
                "null",
                "string",
                "number",
                "object",
                "array",
                "boolean"
              ]
            },
            "trigger": {
              "type": [
                "null",
                "string",
                "number",
                "object",
                "array",
                "boolean"
              ]
            }
          },
          "additionalProperties": true
        },
        "24h": {
          "type": "object",
          "properties": {
            "pct_move": {
              "type": "number"
            },
            "threshold": {
              "type": [
                "null",
                "string",
                "number",
                "object",
                "array",
                "boolean"
              ]
            },
            "trigger": {
              "type": [
                "null",
                "string",
                "number",
                "object",
                "array",
                "boolean"
              ]
            }
          },
          "additionalProperties": true
        }
      },
      "additionalProperties": true
    },
    "SOL": {
      "type": "object",
      "properties": {
        "1h": {
          "type": "object",
          "properties": {
            "pct_move": {
              "type": "number"
            },
            "threshold": {
              "type": [
                "null",
                "string",
                "number",
                "object",
                "array",
                "boolean"
              ]
            },
            "trigger": {
              "type": [
                "null",
                "string",
                "number",
                "object",
                "array",
                "boolean"
              ]
            }
          },
          "additionalProperties": true
        },
        "6h": {
          "type": "object",
          "properties": {
            "pct_move": {
              "type": "number"
            },
            "threshold": {
              "type": [
                "null",
                "string",
                "number",
                "object",
                "array",
                "boolean"
              ]
            },
            "trigger": {
              "type": [
                "null",
                "string",
                "number",
                "object",
                "array",
                "boolean"
              ]
            }
          },
          "additionalProperties": true
        },
        "24h": {
          "type": "object",
          "properties": {
            "pct_move": {
              "type": "number"
            },
            "threshold": {
              "type": [
                "null",
                "string",
                "number",
                "object",
                "array",
                "boolean"
              ]
            },
            "trigger": {
              "type": [
                "null",
                "string",
                "number",
                "object",
                "array",
                "boolean"
              ]
            }
          },
          "additionalProperties": true
        }
      },
      "additionalProperties": true
    },
    "ETH": {
      "type": "object",
      "properties": {
        "1h": {
          "type": "object",
          "properties": {
            "pct_move": {
              "type": "number"
            },
            "threshold": {
              "type": [
                "null",
                "string",
                "number",
                "object",
                "array",
                "boolean"
              ]
            },
            "trigger": {
              "type": [
                "null",
                "string",
                "number",
                "object",
                "array",
                "boolean"
              ]
            }
          },
          "additionalProperties": true
        },
        "6h": {
          "type": "object",
          "properties": {
            "pct_move": {
              "type": "number"
            },
            "threshold": {
              "type": [
                "null",
                "string",
                "number",
                "object",
                "array",
                "boolean"
              ]
            },
            "trigger": {
              "type": [
                "null",
                "string",
                "number",
                "object",
                "array",
                "boolean"
              ]
            }
          },
          "additionalProperties": true
        },
        "24h": {
          "type": "object",
          "properties": {
            "pct_move": {
              "type": "number"
            },
            "threshold": {
              "type": [
                "null",
                "string",
                "number",
                "object",
                "array",
                "boolean"
              ]
            },
            "trigger": {
              "type": [
                "null",
                "string",
                "number",
                "object",
                "array",
                "boolean"
              ]
            }
          },
          "additionalProperties": true
        }
      },
      "additionalProperties": true
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_market_latest.json",
  "examples": [
    {
      "BTC": {
        "1h": {
          "pct_move": 0.0,
          "threshold": null,
          "trigger": null
        },
        "6h": {
          "pct_move": 0.0,
          "threshold": null,
          "trigger": null
        },
        "24h": {
          "pct_move": -4.1775,
          "threshold": null,
          "trigger": null
        }
      },
      "SOL": {
        "1h": {
          "pct_move": 0.0,
          "threshold": null,
          "trigger": null
        },
        "6h": {
          "pct_move": 0.0,
          "threshold": null,
          "trigger": null
        },
        "24h": {
          "pct_move": 1.8932,
          "threshold": null,
          "trigger": null
        }
      },
      "ETH": {
        "1h": {
          "pct_move": 0.0,
          "threshold": null,
          "trigger": null
        },
        "6h": {
          "pct_move": 0.0,
          "threshold": null,
          "trigger": null
        },
        "24h": {
          "pct_move": 18.6776,
          "threshold": null,
          "trigger": null
        }
      }
    }
  ]
}
```

---

### SCHEMA-API_MONITOR-SETTINGS_LIQUIDATION
**Used by:** `GET /api/monitor-settings/liquidation`, `POST /api/monitor-settings/liquidation`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_monitor-settings_liquidation.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_MONITOR-SETTINGS_MARKET
**Used by:** `GET /api/monitor-settings/market`, `POST /api/monitor-settings/market`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_monitor-settings_market.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_MONITOR-SETTINGS_MARKET_RESET-ANCHORS
**Used by:** `POST /api/monitor-settings/market/reset-anchors`

**Example**
```json
{
  "baseline": {
    "BTC": {
      "price": 118755.0,
      "timestamp": "2025-07-26T02:07:14.887106+00:00",
      "mode": "EITHER"
    },
    "ETH": {
      "price": 2994.97,
      "timestamp": "2025-07-26T02:07:14.888106+00:00",
      "mode": "EITHER"
    },
    "SOL": {
      "price": 162.69,
      "timestamp": "2025-07-26T02:07:14.888106+00:00",
      "mode": "EITHER"
    },
    "SPX": {
      "value": 0,
      "time": 0
    }
  },
  "thresholds": {
    "BTC": {
      "1h": 2.0,
      "6h": 2.0,
      "24h": 5.0,
      "delta": 5.0,
      "direction": "both"
    },
    "ETH": {
      "1h": 2.0,
      "6h": 2.0,
      "24h": 5.0,
      "delta": 5.0,
      "direction": "both"
    },
    "SOL": {
      "1h": 2.0,
      "6h": 2.0,
      "24h": 5.0,
      "delta": 5.0,
      "direction": "both"
    },
    "SPX": {
      "1h": 2.0,
      "6h": 2.0,
      "24h": 5.0,
      "delta": 5.0,
      "direction": "both"
    }
  },
  "blast_radius": {
    "BTC": 2.1496967485184992,
    "ETH": 4.279853982436626,
    "SOL": 5.470781055725109
  },
  "blast_filters": {
    "window": "24h",
    "exchange": "coingecko"
  },
  "notifications": {
    "system": true,
    "voice": true,
    "sms": false,
    "tts": true
  },
  "rearm_mode": "ladder",
  "anchors": {
    "SPX": {
      "value": 0.0,
      "time": "2025-09-20T12:07:59.867286+00:00"
    },
    "BTC": {
      "value": 0.0,
      "time": "2025-09-20T12:07:59.867286+00:00"
    },
    "ETH": {
      "value": 0.0,
      "time": "2025-09-20T12:07:59.867286+00:00"
    },
    "SOL": {
      "value": 0.0,
      "time": "2025-09-20T12:07:59.867286+00:00"
    }
  },
  "armed": {
    "SPX": true,
    "BTC": true,
    "ETH": true,
    "SOL": true
  }
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "baseline": {
      "type": "object",
      "properties": {
        "BTC": {
          "type": "object",
          "properties": {
            "price": {
              "type": "number"
            },
            "timestamp": {
              "type": "string"
            },
            "mode": {
              "type": "string"
            }
          },
          "required": [
            "timestamp"
          ],
          "additionalProperties": true
        },
        "ETH": {
          "type": "object",
          "properties": {
            "price": {
              "type": "number"
            },
            "timestamp": {
              "type": "string"
            },
            "mode": {
              "type": "string"
            }
          },
          "required": [
            "timestamp"
          ],
          "additionalProperties": true
        },
        "SOL": {
          "type": "object",
          "properties": {
            "price": {
              "type": "number"
            },
            "timestamp": {
              "type": "string"
            },
            "mode": {
              "type": "string"
            }
          },
          "required": [
            "timestamp"
          ],
          "additionalProperties": true
        },
        "SPX": {
          "type": "object",
          "properties": {
            "value": {
              "type": "number"
            },
            "time": {
              "type": "number"
            }
          },
          "additionalProperties": true
        }
      },
      "additionalProperties": true
    },
    "thresholds": {
      "type": "object",
      "properties": {
        "BTC": {
          "type": "object",
          "properties": {
            "1h": {
              "type": "number"
            },
            "6h": {
              "type": "number"
            },
            "24h": {
              "type": "number"
            },
            "delta": {
              "type": "number"
            },
            "direction": {
              "type": "string"
            }
          },
          "additionalProperties": true
        },
        "ETH": {
          "type": "object",
          "properties": {
            "1h": {
              "type": "number"
            },
            "6h": {
              "type": "number"
            },
            "24h": {
              "type": "number"
            },
            "delta": {
              "type": "number"
            },
            "direction": {
              "type": "string"
            }
          },
          "additionalProperties": true
        },
        "SOL": {
          "type": "object",
          "properties": {
            "1h": {
              "type": "number"
            },
            "6h": {
              "type": "number"
            },
            "24h": {
              "type": "number"
            },
            "delta": {
              "type": "number"
            },
            "direction": {
              "type": "string"
            }
          },
          "additionalProperties": true
        },
        "SPX": {
          "type": "object",
          "properties": {
            "1h": {
              "type": "number"
            },
            "6h": {
              "type": "number"
            },
            "24h": {
              "type": "number"
            },
            "delta": {
              "type": "number"
            },
            "direction": {
              "type": "string"
            }
          },
          "additionalProperties": true
        }
      },
      "additionalProperties": true
    },
    "blast_radius": {
      "type": "object",
      "properties": {
        "BTC": {
          "type": "number"
        },
        "ETH": {
          "type": "number"
        },
        "SOL": {
          "type": "number"
        }
      },
      "additionalProperties": true
    },
    "blast_filters": {
      "type": "object",
      "properties": {
        "window": {
          "type": "string"
        },
        "exchange": {
          "type": "string"
        }
      },
      "additionalProperties": true
    },
    "notifications": {
      "type": "object",
      "properties": {
        "system": {
          "type": "boolean"
        },
        "voice": {
          "type": "boolean"
        },
        "sms": {
          "type": "boolean"
        },
        "tts": {
          "type": "boolean"
        }
      },
      "additionalProperties": true
    },
    "rearm_mode": {
      "type": "string"
    },
    "anchors": {
      "type": "object",
      "properties": {
        "SPX": {
          "type": "object",
          "properties": {
            "value": {
              "type": "number"
            },
            "time": {
              "type": "string"
            }
          },
          "additionalProperties": true
        },
        "BTC": {
          "type": "object",
          "properties": {
            "value": {
              "type": "number"
            },
            "time": {
              "type": "string"
            }
          },
          "additionalProperties": true
        },
        "ETH": {
          "type": "object",
          "properties": {
            "value": {
              "type": "number"
            },
            "time": {
              "type": "string"
            }
          },
          "additionalProperties": true
        },
        "SOL": {
          "type": "object",
          "properties": {
            "value": {
              "type": "number"
            },
            "time": {
              "type": "string"
            }
          },
          "additionalProperties": true
        }
      },
      "additionalProperties": true
    },
    "armed": {
      "type": "object",
      "properties": {
        "SPX": {
          "type": "boolean"
        },
        "BTC": {
          "type": "boolean"
        },
        "ETH": {
          "type": "boolean"
        },
        "SOL": {
          "type": "boolean"
        }
      },
      "additionalProperties": true
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_monitor-settings_market_reset-anchors.json",
  "examples": [
    {
      "baseline": {
        "BTC": {
          "price": 118755.0,
          "timestamp": "2025-07-26T02:07:14.887106+00:00",
          "mode": "EITHER"
        },
        "ETH": {
          "price": 2994.97,
          "timestamp": "2025-07-26T02:07:14.888106+00:00",
          "mode": "EITHER"
        },
        "SOL": {
          "price": 162.69,
          "timestamp": "2025-07-26T02:07:14.888106+00:00",
          "mode": "EITHER"
        },
        "SPX": {
          "value": 0,
          "time": 0
        }
      },
      "thresholds": {
        "BTC": {
          "1h": 2.0,
          "6h": 2.0,
          "24h": 5.0,
          "delta": 5.0,
          "direction": "both"
        },
        "ETH": {
          "1h": 2.0,
          "6h": 2.0,
          "24h": 5.0,
          "delta": 5.0,
          "direction": "both"
        },
        "SOL": {
          "1h": 2.0,
          "6h": 2.0,
          "24h": 5.0,
          "delta": 5.0,
          "direction": "both"
        },
        "SPX": {
          "1h": 2.0,
          "6h": 2.0,
          "24h": 5.0,
          "delta": 5.0,
          "direction": "both"
        }
      },
      "blast_radius": {
        "BTC": 2.1496967485184992,
        "ETH": 4.279853982436626,
        "SOL": 5.470781055725109
      },
      "blast_filters": {
        "window": "24h",
        "exchange": "coingecko"
      },
      "notifications": {
        "system": true,
        "voice": true,
        "sms": false,
        "tts": true
      },
      "rearm_mode": "ladder",
      "anchors": {
        "SPX": {
          "value": 0.0,
          "time": "2025-09-20T12:07:59.867286+00:00"
        },
        "BTC": {
          "value": 0.0,
          "time": "2025-09-20T12:07:59.867286+00:00"
        },
        "ETH": {
          "value": 0.0,
          "time": "2025-09-20T12:07:59.867286+00:00"
        },
        "SOL": {
          "value": 0.0,
          "time": "2025-09-20T12:07:59.867286+00:00"
        }
      },
      "armed": {
        "SPX": true,
        "BTC": true,
        "ETH": true,
        "SOL": true
      }
    }
  ]
}
```

---

### SCHEMA-API_MONITOR-SETTINGS_PROFIT
**Used by:** `GET /api/monitor-settings/profit`, `POST /api/monitor-settings/profit`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_monitor-settings_profit.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_MONITOR-SETTINGS_SONIC
**Used by:** `GET /api/monitor-settings/sonic`, `POST /api/monitor-settings/sonic`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_monitor-settings_sonic.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_MONITOR-STATUS_RESET-LIQUID-SNOOZE
**Used by:** `POST /api/monitor-status/reset-liquid-snooze`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_monitor-status_reset-liquid-snooze.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_MONITOR-STATUS_{MONITOR_TYPE}
**Used by:** `GET /api/monitor-status/{monitor_type}`, `POST /api/monitor-status/{monitor_type}`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_monitor-status_{monitor_type}.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_NOTIFICATIONS
**Used by:** `GET /api/notifications/`

**Example**
```json
[
  {
    "id": 10,
    "monitor_name": "position_monitor",
    "level": "HIGH",
    "subject": "❗ position_monitor error",
    "body": "No module named 'rich'",
    "metadata": "{\"trace\":\"Traceback (most recent call last):\\n  File \\\"/workspace/sonic5/backend/core/monitor_core/base_monitor.py\\\", line 44, in run_cycle\\n    result = self._do_work()\\n             ^^^^^^^^^^^^^^^\\n  File \\\"/workspace/sonic5/backend/core/monitor_core/position_monitor.py\\\", line 26, in _do_work\\n    sync_result = self.core.update_positions_from_jupiter(source=\\\"position_monitor\\\")\\n                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\n  File \\\"/workspace/sonic5/backend/core/positions_core/position_core.py\\\", line 174, in update_positions_from_jupiter\\n    from backend.core.positions_core.position_sync_service import (\\n  File \\\"/workspace/sonic5/backend/core/positions_core/position_sync_service.py\\\", line 6, in <module>\\n    from rich.console import Console\\nModuleNotFoundError: No module named 'rich'\\n\"}",
    "read": 0,
    "created_at": "2025-09-20T12:07:58.983Z"
  },
  {
    "id": 9,
    "monitor_name": "market_monitor",
    "level": "HIGH",
    "subject": "❗ market_monitor error",
    "body": "Binance API failure",
    "metadata": "{\"trace\":\"1024, in raise_for_status\\n    raise HTTPError(http_error_msg, response=self)\\nrequests.exceptions.HTTPError: 429 Client Error: Too Many Requests for url: https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=bitcoin%2Cethereum%2Csolana\\n\\nDuring handling of the above exception, another exception occurred:\\n\\nTraceback (most recent call last):\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\base_monitor.py\\\", line 44, in run_cycle\\n    result = self._do_work()\\n             ^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\market_monitor.py\\\", line 56, in _do_work\\n    hi_lo = self.swing.fetch(self.ASSETS)\\n            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\market_core\\\\daily_swing_service.py\\\", line 56, in fetch\\n    return self._from_binance(assets)\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\market_core\\\\daily_swing_service.py\\\", line 46, in _from_binance\\n    raise RuntimeError(\\\"Binance API failure\\\")\\nRuntimeError: Binance API failure\\n\"}",
    "read": 0,
    "created_at": "2025-07-26T02:37:07.582Z"
  },
  {
    "id": 8,
    "monitor_name": "market_monitor",
    "level": "HIGH",
    "subject": "❗ market_monitor error",
    "body": "Binance API failure",
    "metadata": "{\"trace\":\"1024, in raise_for_status\\n    raise HTTPError(http_error_msg, response=self)\\nrequests.exceptions.HTTPError: 429 Client Error: Too Many Requests for url: https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=bitcoin%2Cethereum%2Csolana\\n\\nDuring handling of the above exception, another exception occurred:\\n\\nTraceback (most recent call last):\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\base_monitor.py\\\", line 44, in run_cycle\\n    result = self._do_work()\\n             ^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\market_monitor.py\\\", line 56, in _do_work\\n    hi_lo = self.swing.fetch(self.ASSETS)\\n            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\market_core\\\\daily_swing_service.py\\\", line 56, in fetch\\n    return self._from_binance(assets)\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\market_core\\\\daily_swing_service.py\\\", line 46, in _from_binance\\n    raise RuntimeError(\\\"Binance API failure\\\")\\nRuntimeError: Binance API failure\\n\"}",
    "read": 0,
    "created_at": "2025-07-26T02:36:46.677Z"
  },
  {
    "id": 7,
    "monitor_name": "market_monitor",
    "level": "HIGH",
    "subject": "❗ market_monitor error",
    "body": "Binance API failure",
    "metadata": "{\"trace\":\"1024, in raise_for_status\\n    raise HTTPError(http_error_msg, response=self)\\nrequests.exceptions.HTTPError: 429 Client Error: Too Many Requests for url: https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=bitcoin%2Cethereum%2Csolana\\n\\nDuring handling of the above exception, another exception occurred:\\n\\nTraceback (most recent call last):\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\base_monitor.py\\\", line 44, in run_cycle\\n    result = self._do_work()\\n             ^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\market_monitor.py\\\", line 52, in _do_work\\n    hi_lo = self.swing.fetch(self.ASSETS)\\n            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\market_core\\\\daily_swing_service.py\\\", line 56, in fetch\\n    return self._from_binance(assets)\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\market_core\\\\daily_swing_service.py\\\", line 46, in _from_binance\\n    raise RuntimeError(\\\"Binance API failure\\\")\\nRuntimeError: Binance API failure\\n\"}",
    "read": 0,
    "created_at": "2025-07-26T02:33:21.075Z"
  },
  {
    "id": 6,
    "monitor_name": "market_monitor",
    "level": "LOW",
    "subject": "✅ market_monitor finished",
    "body": "market_monitor completed successfully",
    "metadata": "{\"result\":\"{'status': 'Success', 'timestamp': '2025-07-26T02:30:06.652660+00:00', 'trigger_any': False, 'details': [{'asset': 'BTC', 'price': 118755.0, 'pct_move': 0.0, 'baseline': 118755.0, 'blast_radius': 2.14\"}",
    "read": 0,
    "created_at": "2025-07-26T02:30:06.669Z"
  },
  {
    "id": 5,
    "monitor_name": "market_monitor",
    "level": "HIGH",
    "subject": "❗ market_monitor error",
    "body": "Binance API failure",
    "metadata": "{\"trace\":\"1024, in raise_for_status\\n    raise HTTPError(http_error_msg, response=self)\\nrequests.exceptions.HTTPError: 429 Client Error: Too Many Requests for url: https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=bitcoin%2Cethereum%2Csolana\\n\\nDuring handling of the above exception, another exception occurred:\\n\\nTraceback (most recent call last):\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\base_monitor.py\\\", line 44, in run_cycle\\n    result = self._do_work()\\n             ^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\market_monitor.py\\\", line 50, in _do_work\\n    hi_lo = self.swing.fetch(self.ASSETS)\\n            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\market_core\\\\daily_swing_service.py\\\", line 56, in fetch\\n    return self._from_binance(assets)\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\market_core\\\\daily_swing_service.py\\\", line 46, in _from_binance\\n    raise RuntimeError(\\\"Binance API failure\\\")\\nRuntimeError: Binance API failure\\n\"}",
    "read": 0,
    "created_at": "2025-07-26T02:24:58.172Z"
  },
  {
    "id": 4,
    "monitor_name": "market_monitor",
    "level": "LOW",
    "subject": "✅ market_monitor finished",
    "body": "market_monitor completed successfully",
    "metadata": "{\"result\":\"{'status': 'Success', 'timestamp': '2025-07-26T02:23:51.108081+00:00', 'trigger_any': False, 'details': [{'asset': 'BTC', 'price': 118755.0, 'pct_move': 0.0, 'baseline': 118755.0, 'blast_radius': 2.14\"}",
    "read": 0,
    "created_at": "2025-07-26T02:23:51.126Z"
  },
  {
    "id": 3,
    "monitor_name": "market_monitor",
    "level": "LOW",
    "subject": "✅ market_monitor finished",
    "body": "market_monitor completed successfully",
    "metadata": "{\"result\":\"{'status': 'Success', 'timestamp': '2025-07-26T02:07:15.081139+00:00', 'trigger_any': False, 'details': [{'asset': 'BTC', 'price': 118755.0, 'pct_move': 0.0, 'baseline': 118755.0, 'blast_radius': 2.14\"}",
    "read": 0,
    "created_at": "2025-07-26T02:07:15.100Z"
  },
  {
    "id": 2,
    "monitor_name": "market_monitor",
    "level": "HIGH",
    "subject": "❗ market_monitor error",
    "body": "'NoneType' object has no attribute 'get_var'",
    "metadata": "{\"trace\":\"Traceback (most recent call last):\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\base_monitor.py\\\", line 44, in run_cycle\\n    result = self._do_work()\\n             ^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\market_monitor.py\\\", line 44, in _do_work\\n    cfg = self._cfg()\\n          ^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\market_monitor.py\\\", line 20, in _cfg\\n    cfg = self.dl.system.get_var(\\\"market_monitor\\\") or {}\\n          ^^^^^^^^^^^^^^^^^^^^^^\\nAttributeError: 'NoneType' object has no attribute 'get_var'\\n\"}",
    "read": 0,
    "created_at": "2025-07-26T02:02:11.961Z"
  },
  {
    "id": 1,
    "monitor_name": "market_monitor",
    "level": "HIGH",
    "subject": "❗ market_monitor error",
    "body": "'NoneType' object has no attribute 'get_var'",
    "metadata": "{\"trace\":\"Traceback (most recent call last):\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\base_monitor.py\\\", line 44, in run_cycle\\n    result = self._do_work()\\n             ^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\market_monitor.py\\\", line 44, in _do_work\\n    cfg = self._cfg()\\n          ^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\market_monitor.py\\\", line 20, in _cfg\\n    cfg = self.dl.system.get_var(\\\"market_monitor\\\") or {}\\n          ^^^^^^^^^^^^^^^^^^^^^^\\nAttributeError: 'NoneType' object has no attribute 'get_var'\\n\"}",
    "read": 0,
    "created_at": "2025-07-26T02:01:16.668Z"
  }
]
```

**Schema**
```json
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "id": {
        "type": "number"
      },
      "monitor_name": {
        "type": "string"
      },
      "level": {
        "type": "string"
      },
      "subject": {
        "type": "string"
      },
      "body": {
        "type": "string"
      },
      "metadata": {
        "type": "string"
      },
      "read": {
        "type": "number"
      },
      "created_at": {
        "type": "string"
      }
    },
    "required": [
      "id"
    ],
    "additionalProperties": true
  },
  "$id": "schema/api_notifications.json",
  "examples": [
    [
      {
        "id": 10,
        "monitor_name": "position_monitor",
        "level": "HIGH",
        "subject": "❗ position_monitor error",
        "body": "No module named 'rich'",
        "metadata": "{\"trace\":\"Traceback (most recent call last):\\n  File \\\"/workspace/sonic5/backend/core/monitor_core/base_monitor.py\\\", line 44, in run_cycle\\n    result = self._do_work()\\n             ^^^^^^^^^^^^^^^\\n  File \\\"/workspace/sonic5/backend/core/monitor_core/position_monitor.py\\\", line 26, in _do_work\\n    sync_result = self.core.update_positions_from_jupiter(source=\\\"position_monitor\\\")\\n                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\n  File \\\"/workspace/sonic5/backend/core/positions_core/position_core.py\\\", line 174, in update_positions_from_jupiter\\n    from backend.core.positions_core.position_sync_service import (\\n  File \\\"/workspace/sonic5/backend/core/positions_core/position_sync_service.py\\\", line 6, in <module>\\n    from rich.console import Console\\nModuleNotFoundError: No module named 'rich'\\n\"}",
        "read": 0,
        "created_at": "2025-09-20T12:07:58.983Z"
      },
      {
        "id": 9,
        "monitor_name": "market_monitor",
        "level": "HIGH",
        "subject": "❗ market_monitor error",
        "body": "Binance API failure",
        "metadata": "{\"trace\":\"1024, in raise_for_status\\n    raise HTTPError(http_error_msg, response=self)\\nrequests.exceptions.HTTPError: 429 Client Error: Too Many Requests for url: https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=bitcoin%2Cethereum%2Csolana\\n\\nDuring handling of the above exception, another exception occurred:\\n\\nTraceback (most recent call last):\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\base_monitor.py\\\", line 44, in run_cycle\\n    result = self._do_work()\\n             ^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\market_monitor.py\\\", line 56, in _do_work\\n    hi_lo = self.swing.fetch(self.ASSETS)\\n            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\market_core\\\\daily_swing_service.py\\\", line 56, in fetch\\n    return self._from_binance(assets)\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\market_core\\\\daily_swing_service.py\\\", line 46, in _from_binance\\n    raise RuntimeError(\\\"Binance API failure\\\")\\nRuntimeError: Binance API failure\\n\"}",
        "read": 0,
        "created_at": "2025-07-26T02:37:07.582Z"
      },
      {
        "id": 8,
        "monitor_name": "market_monitor",
        "level": "HIGH",
        "subject": "❗ market_monitor error",
        "body": "Binance API failure",
        "metadata": "{\"trace\":\"1024, in raise_for_status\\n    raise HTTPError(http_error_msg, response=self)\\nrequests.exceptions.HTTPError: 429 Client Error: Too Many Requests for url: https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=bitcoin%2Cethereum%2Csolana\\n\\nDuring handling of the above exception, another exception occurred:\\n\\nTraceback (most recent call last):\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\base_monitor.py\\\", line 44, in run_cycle\\n    result = self._do_work()\\n             ^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\market_monitor.py\\\", line 56, in _do_work\\n    hi_lo = self.swing.fetch(self.ASSETS)\\n            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\market_core\\\\daily_swing_service.py\\\", line 56, in fetch\\n    return self._from_binance(assets)\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\market_core\\\\daily_swing_service.py\\\", line 46, in _from_binance\\n    raise RuntimeError(\\\"Binance API failure\\\")\\nRuntimeError: Binance API failure\\n\"}",
        "read": 0,
        "created_at": "2025-07-26T02:36:46.677Z"
      },
      {
        "id": 7,
        "monitor_name": "market_monitor",
        "level": "HIGH",
        "subject": "❗ market_monitor error",
        "body": "Binance API failure",
        "metadata": "{\"trace\":\"1024, in raise_for_status\\n    raise HTTPError(http_error_msg, response=self)\\nrequests.exceptions.HTTPError: 429 Client Error: Too Many Requests for url: https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=bitcoin%2Cethereum%2Csolana\\n\\nDuring handling of the above exception, another exception occurred:\\n\\nTraceback (most recent call last):\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\base_monitor.py\\\", line 44, in run_cycle\\n    result = self._do_work()\\n             ^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\market_monitor.py\\\", line 52, in _do_work\\n    hi_lo = self.swing.fetch(self.ASSETS)\\n            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\market_core\\\\daily_swing_service.py\\\", line 56, in fetch\\n    return self._from_binance(assets)\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\market_core\\\\daily_swing_service.py\\\", line 46, in _from_binance\\n    raise RuntimeError(\\\"Binance API failure\\\")\\nRuntimeError: Binance API failure\\n\"}",
        "read": 0,
        "created_at": "2025-07-26T02:33:21.075Z"
      },
      {
        "id": 6,
        "monitor_name": "market_monitor",
        "level": "LOW",
        "subject": "✅ market_monitor finished",
        "body": "market_monitor completed successfully",
        "metadata": "{\"result\":\"{'status': 'Success', 'timestamp': '2025-07-26T02:30:06.652660+00:00', 'trigger_any': False, 'details': [{'asset': 'BTC', 'price': 118755.0, 'pct_move': 0.0, 'baseline': 118755.0, 'blast_radius': 2.14\"}",
        "read": 0,
        "created_at": "2025-07-26T02:30:06.669Z"
      },
      {
        "id": 5,
        "monitor_name": "market_monitor",
        "level": "HIGH",
        "subject": "❗ market_monitor error",
        "body": "Binance API failure",
        "metadata": "{\"trace\":\"1024, in raise_for_status\\n    raise HTTPError(http_error_msg, response=self)\\nrequests.exceptions.HTTPError: 429 Client Error: Too Many Requests for url: https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=bitcoin%2Cethereum%2Csolana\\n\\nDuring handling of the above exception, another exception occurred:\\n\\nTraceback (most recent call last):\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\base_monitor.py\\\", line 44, in run_cycle\\n    result = self._do_work()\\n             ^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\market_monitor.py\\\", line 50, in _do_work\\n    hi_lo = self.swing.fetch(self.ASSETS)\\n            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\market_core\\\\daily_swing_service.py\\\", line 56, in fetch\\n    return self._from_binance(assets)\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\market_core\\\\daily_swing_service.py\\\", line 46, in _from_binance\\n    raise RuntimeError(\\\"Binance API failure\\\")\\nRuntimeError: Binance API failure\\n\"}",
        "read": 0,
        "created_at": "2025-07-26T02:24:58.172Z"
      },
      {
        "id": 4,
        "monitor_name": "market_monitor",
        "level": "LOW",
        "subject": "✅ market_monitor finished",
        "body": "market_monitor completed successfully",
        "metadata": "{\"result\":\"{'status': 'Success', 'timestamp': '2025-07-26T02:23:51.108081+00:00', 'trigger_any': False, 'details': [{'asset': 'BTC', 'price': 118755.0, 'pct_move': 0.0, 'baseline': 118755.0, 'blast_radius': 2.14\"}",
        "read": 0,
        "created_at": "2025-07-26T02:23:51.126Z"
      },
      {
        "id": 3,
        "monitor_name": "market_monitor",
        "level": "LOW",
        "subject": "✅ market_monitor finished",
        "body": "market_monitor completed successfully",
        "metadata": "{\"result\":\"{'status': 'Success', 'timestamp': '2025-07-26T02:07:15.081139+00:00', 'trigger_any': False, 'details': [{'asset': 'BTC', 'price': 118755.0, 'pct_move': 0.0, 'baseline': 118755.0, 'blast_radius': 2.14\"}",
        "read": 0,
        "created_at": "2025-07-26T02:07:15.100Z"
      },
      {
        "id": 2,
        "monitor_name": "market_monitor",
        "level": "HIGH",
        "subject": "❗ market_monitor error",
        "body": "'NoneType' object has no attribute 'get_var'",
        "metadata": "{\"trace\":\"Traceback (most recent call last):\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\base_monitor.py\\\", line 44, in run_cycle\\n    result = self._do_work()\\n             ^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\market_monitor.py\\\", line 44, in _do_work\\n    cfg = self._cfg()\\n          ^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\market_monitor.py\\\", line 20, in _cfg\\n    cfg = self.dl.system.get_var(\\\"market_monitor\\\") or {}\\n          ^^^^^^^^^^^^^^^^^^^^^^\\nAttributeError: 'NoneType' object has no attribute 'get_var'\\n\"}",
        "read": 0,
        "created_at": "2025-07-26T02:02:11.961Z"
      },
      {
        "id": 1,
        "monitor_name": "market_monitor",
        "level": "HIGH",
        "subject": "❗ market_monitor error",
        "body": "'NoneType' object has no attribute 'get_var'",
        "metadata": "{\"trace\":\"Traceback (most recent call last):\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\base_monitor.py\\\", line 44, in run_cycle\\n    result = self._do_work()\\n             ^^^^^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\market_monitor.py\\\", line 44, in _do_work\\n    cfg = self._cfg()\\n          ^^^^^^^^^^^\\n  File \\\"C:\\\\sonic4\\\\backend\\\\core\\\\monitor_core\\\\market_monitor.py\\\", line 20, in _cfg\\n    cfg = self.dl.system.get_var(\\\"market_monitor\\\") or {}\\n          ^^^^^^^^^^^^^^^^^^^^^^\\nAttributeError: 'NoneType' object has no attribute 'get_var'\\n\"}",
        "read": 0,
        "created_at": "2025-07-26T02:01:16.668Z"
      }
    ]
  ]
}
```

---

### SCHEMA-API_NOTIFICATIONS_MARK_ALL_READ
**Used by:** `POST /api/notifications/mark_all_read`

**Example**
```json
{
  "success": true
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "success": {
      "type": "boolean"
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_notifications_mark_all_read.json",
  "examples": [
    {
      "success": true
    }
  ]
}
```

---

### SCHEMA-API_NOTIFICATIONS_UNREAD-COUNT
**Used by:** `GET /api/notifications/unread-count`

**Example**
```json
{
  "count": 10
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "count": {
      "type": "number"
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_notifications_unread-count.json",
  "examples": [
    {
      "count": 10
    }
  ]
}
```

---

### SCHEMA-API_NOTIFICATIONS_{NOTIF_ID}_READ
**Used by:** `POST /api/notifications/{notif_id}/read`

**Example**
```json
{
  "success": true
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "success": {
      "type": "boolean"
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_notifications_{notif_id}_read.json",
  "examples": [
    {
      "success": true
    }
  ]
}
```

---

### SCHEMA-API_PERPS_CLOSE
**Used by:** `POST /api/perps/close`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_perps_close.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_PERPS_DEBUG_IDL
**Used by:** `GET /api/perps/debug/idl`

**Example**
```json
{
  "programId": "PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu",
  "instructions": 35,
  "accounts": 5,
  "accountNames": [
    "Custody",
    "Perpetuals",
    "Pool",
    "PositionRequest",
    "Position"
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "programId": {
      "type": "string"
    },
    "instructions": {
      "type": "number"
    },
    "accounts": {
      "type": "number"
    },
    "accountNames": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_perps_debug_idl.json",
  "examples": [
    {
      "programId": "PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu",
      "instructions": 35,
      "accounts": 5,
      "accountNames": [
        "Custody",
        "Perpetuals",
        "Pool",
        "PositionRequest",
        "Position"
      ]
    }
  ]
}
```

---

### SCHEMA-API_PERPS_DEBUG_IDL-INSPECT
**Used by:** `GET /api/perps/debug/idl-inspect`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "query",
        "name"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_perps_debug_idl-inspect.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "query",
            "name"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_PERPS_DEBUG_IDL-NAMES
**Used by:** `GET /api/perps/debug/idl-names`

**Example**
```json
{
  "count": 35,
  "instructions": [
    "init",
    "addPool",
    "addCustody",
    "setCustodyConfig",
    "setCustodyGlobalLimit",
    "reallocCustody",
    "setPoolConfig",
    "setPerpetualsConfig",
    "transferAdmin",
    "withdrawFees2",
    "createTokenMetadata",
    "testInit",
    "setTestTime",
    "swap2",
    "addLiquidity2",
    "removeLiquidity2",
    "createIncreasePositionMarketRequest",
    "createDecreasePositionRequest2",
    "createDecreasePositionMarketRequest",
    "updateDecreasePositionRequest2",
    "closePositionRequest",
    "increasePosition4",
    "increasePositionPreSwap",
    "decreasePosition4",
    "liquidateFullPosition4",
    "refreshAssetsUnderManagement",
    "instantCreateTpsl",
    "instantCreateLimitOrder",
    "instantIncreasePosition",
    "instantDecreasePosition",
    "instantUpdateLimitOrder",
    "instantUpdateTpsl",
    "getAddLiquidityAmountAndFee2",
    "getRemoveLiquidityAmountAndFee2",
    "getAssetsUnderManagement2"
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "count": {
      "type": "number"
    },
    "instructions": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_perps_debug_idl-names.json",
  "examples": [
    {
      "count": 35,
      "instructions": [
        "init",
        "addPool",
        "addCustody",
        "setCustodyConfig",
        "setCustodyGlobalLimit",
        "reallocCustody",
        "setPoolConfig",
        "setPerpetualsConfig",
        "transferAdmin",
        "withdrawFees2",
        "createTokenMetadata",
        "testInit",
        "setTestTime",
        "swap2",
        "addLiquidity2",
        "removeLiquidity2",
        "createIncreasePositionMarketRequest",
        "createDecreasePositionRequest2",
        "createDecreasePositionMarketRequest",
        "updateDecreasePositionRequest2",
        "closePositionRequest",
        "increasePosition4",
        "increasePositionPreSwap",
        "decreasePosition4",
        "liquidateFullPosition4",
        "refreshAssetsUnderManagement",
        "instantCreateTpsl",
        "instantCreateLimitOrder",
        "instantIncreasePosition",
        "instantDecreasePosition",
        "instantUpdateLimitOrder",
        "instantUpdateTpsl",
        "getAddLiquidityAmountAndFee2",
        "getRemoveLiquidityAmountAndFee2",
        "getAssetsUnderManagement2"
      ]
    }
  ]
}
```

---

### SCHEMA-API_PERPS_DEBUG_OWNER-OFFSET
**Used by:** `GET /api/perps/debug/owner-offset`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "query",
        "owner"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_perps_debug_owner-offset.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "query",
            "owner"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_PERPS_MARKETS
**Used by:** `GET /api/perps/markets`

**Example**
```json
{
  "ok": false,
  "error": "Pool GPA failed: RPC exhausted for getProgramAccounts",
  "programId": "PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu",
  "accounts": null
}
```

**Schema**
```json
{
  "$id": "schema/api_perps_markets.json",
  "type": "object",
  "properties": {
    "ok": {
      "type": "boolean"
    },
    "error": {
      "type": "string"
    },
    "programId": {
      "type": "string"
    },
    "accounts": {
      "type": [
        "null",
        "array"
      ]
    }
  },
  "required": [
    "ok",
    "error"
  ],
  "additionalProperties": true,
  "examples": [
    {
      "ok": false,
      "error": "Pool GPA failed: RPC exhausted for getProgramAccounts",
      "programId": "PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu",
      "accounts": null
    }
  ]
}
```

---

### SCHEMA-API_PERPS_MARKETS_RESOLVE
**Used by:** `GET /api/perps/markets/resolve`

**Example**
```json
{
  "detail": "resolve failed: Pool GPA failed: RPC exhausted for getProgramAccounts"
}
```

**Schema**
```json
{
  "$id": "schema/api_perps_markets_resolve.json",
  "type": "object",
  "properties": {
    "detail": {
      "type": "string"
    }
  },
  "required": [
    "detail"
  ],
  "additionalProperties": false,
  "examples": [
    {
      "detail": "resolve failed: Pool GPA failed: RPC exhausted for getProgramAccounts"
    }
  ]
}
```

---

### SCHEMA-API_PERPS_ORDER
**Used by:** `POST /api/perps/order`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_perps_order.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_PERPS_ORDER_CLOSE
**Used by:** `POST /api/perps/order/close`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_perps_order_close.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_PERPS_ORDER_OPEN
**Used by:** `POST /api/perps/order/open`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_perps_order_open.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_PERPS_POSITION_BY-MARKET
**Used by:** `GET /api/perps/position/by-market`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "query",
        "market"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_perps_position_by-market.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "query",
            "market"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_PERPS_POSITIONS
**Used by:** `GET /api/perps/positions`

**Example**
```json
{
  "detail": "positions fetch failed: RPC exhausted for getProgramAccounts"
}
```

**Schema**
```json
{
  "$id": "schema/api_perps_positions.json",
  "type": "object",
  "properties": {
    "detail": {
      "type": "string"
    }
  },
  "required": [
    "detail"
  ],
  "additionalProperties": false,
  "examples": [
    {
      "detail": "positions fetch failed: RPC exhausted for getProgramAccounts"
    }
  ]
}
```

---

### SCHEMA-API_PERPS_POSITIONS_DB
**Used by:** `GET /api/perps/positions/db`

**Example**
```json
{
  "detail": "DB probe failed: DataLocker.__init__() missing 1 required positional argument: 'db_path'"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "string"
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_perps_positions_db.json",
  "examples": [
    {
      "detail": "DB probe failed: DataLocker.__init__() missing 1 required positional argument: 'db_path'"
    }
  ]
}
```

---

### SCHEMA-API_PERPS_POSITIONS_DETAILED
**Used by:** `GET /api/perps/positions/detailed`, `GET /api/perps/positions/detailed`, `GET /api/perps/positions/detailed`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "query",
        "owner"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_perps_positions_detailed.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "query",
            "owner"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_PERPS_POSITIONS_HEALTH
**Used by:** `GET /api/perps/positions/health`

**Example**
```json
{
  "detail": "health failed: Signer file not found: signer.txt. Tried: ['/workspace/sonic5/signer.txt', '/workspace/sonic5/backend/services/signer.txt', '/workspace/sonic5/backend/signer.txt']"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "string"
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_perps_positions_health.json",
  "examples": [
    {
      "detail": "health failed: Signer file not found: signer.txt. Tried: ['/workspace/sonic5/signer.txt', '/workspace/sonic5/backend/services/signer.txt', '/workspace/sonic5/backend/signer.txt']"
    }
  ]
}
```

---

### SCHEMA-API_PERPS_POSITIONS_RAW
**Used by:** `GET /api/perps/positions/raw`

**Example**
```json
{
  "detail": "raw fetch failed: Signer file not found: signer.txt. Tried: ['/workspace/sonic5/signer.txt', '/workspace/sonic5/backend/services/signer.txt', '/workspace/sonic5/backend/signer.txt']"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "string"
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_perps_positions_raw.json",
  "examples": [
    {
      "detail": "raw fetch failed: Signer file not found: signer.txt. Tried: ['/workspace/sonic5/signer.txt', '/workspace/sonic5/backend/services/signer.txt', '/workspace/sonic5/backend/signer.txt']"
    }
  ]
}
```

---

### SCHEMA-API_PORTFOLIO_LATEST_SNAPSHOT
**Used by:** `GET /api/portfolio/latest_snapshot`

**Example**
```json
{
  "id": "8071140e-98c0-4b69-8797-d27886b663e9",
  "snapshot_time": "2025-09-20T12:07:58.406202",
  "total_size": 1857.4499999999998,
  "total_long_size": 518.3299999999999,
  "total_short_size": 1339.12,
  "total_value": 143.0,
  "total_collateral": 142.87,
  "avg_leverage": 14.539847425233518,
  "avg_travel_percent": 0.15390243015538882,
  "avg_heat_index": 8.782821771783897,
  "total_heat_index": 44.08,
  "market_average_sp500": 0.0,
  "session_start_time": "2025-09-20T12:07:58.859859",
  "session_start_value": 0.0,
  "current_session_value": 143.0,
  "session_goal_value": 0.0,
  "session_performance_value": 0.0
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    },
    "snapshot_time": {
      "type": "string"
    },
    "total_size": {
      "type": "number"
    },
    "total_long_size": {
      "type": "number"
    },
    "total_short_size": {
      "type": "number"
    },
    "total_value": {
      "type": "number"
    },
    "total_collateral": {
      "type": "number"
    },
    "avg_leverage": {
      "type": "number"
    },
    "avg_travel_percent": {
      "type": "number"
    },
    "avg_heat_index": {
      "type": "number"
    },
    "total_heat_index": {
      "type": "number"
    },
    "market_average_sp500": {
      "type": "number"
    },
    "session_start_time": {
      "type": "string"
    },
    "session_start_value": {
      "type": "number"
    },
    "current_session_value": {
      "type": "number"
    },
    "session_goal_value": {
      "type": "number"
    },
    "session_performance_value": {
      "type": "number"
    }
  },
  "required": [
    "id"
  ],
  "additionalProperties": true,
  "$id": "schema/api_portfolio_latest_snapshot.json",
  "examples": [
    {
      "id": "8071140e-98c0-4b69-8797-d27886b663e9",
      "snapshot_time": "2025-09-20T12:07:58.406202",
      "total_size": 1857.4499999999998,
      "total_long_size": 518.3299999999999,
      "total_short_size": 1339.12,
      "total_value": 143.0,
      "total_collateral": 142.87,
      "avg_leverage": 14.539847425233518,
      "avg_travel_percent": 0.15390243015538882,
      "avg_heat_index": 8.782821771783897,
      "total_heat_index": 44.08,
      "market_average_sp500": 0.0,
      "session_start_time": "2025-09-20T12:07:58.859859",
      "session_start_value": 0.0,
      "current_session_value": 143.0,
      "session_goal_value": 0.0,
      "session_performance_value": 0.0
    }
  ]
}
```

---

### SCHEMA-API_PORTFOLIO_UPDATE_SNAPSHOT
**Used by:** `POST /api/portfolio/update_snapshot`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_portfolio_update_snapshot.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_SOLANA_BALANCE
**Used by:** `POST /api/solana/balance`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_solana_balance.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_STATUS
**Used by:** `GET /api/status`

**Example**
```json
{
  "status": "FastAPI backend online 🚀"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    }
  },
  "required": [
    "status"
  ],
  "additionalProperties": true,
  "$id": "schema/api_status.json",
  "examples": [
    {
      "status": "FastAPI backend online 🚀"
    }
  ]
}
```

---

### SCHEMA-API_TRADERS
**Used by:** `GET /api/traders/`, `POST /api/traders/`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_traders.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_TRADERS_EXPORT
**Used by:** `GET /api/traders/export`

**Example**
```json
{
  "detail": "Trader not found"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "string"
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_traders_export.json",
  "examples": [
    {
      "detail": "Trader not found"
    }
  ]
}
```

---

### SCHEMA-API_TRADERS_QUICK_IMPORT
**Used by:** `POST /api/traders/quick_import`

**Example**
```json
{
  "status": "created"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    }
  },
  "required": [
    "status"
  ],
  "additionalProperties": true,
  "$id": "schema/api_traders_quick_import.json",
  "examples": [
    {
      "status": "created"
    }
  ]
}
```

---

### SCHEMA-API_TRADERS_{NAME}
**Used by:** `GET /api/traders/{name}`, `PUT /api/traders/{name}`, `DELETE /api/traders/{name}`

**Example**
```json
{
  "detail": "Trader not found"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "string"
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_traders_{name}.json",
  "examples": [
    {
      "detail": "Trader not found"
    }
  ]
}
```

---

### SCHEMA-API_WALLET_DEBUG
**Used by:** `GET /api/wallet/debug`

**Example**
```json
{
  "detail": "wallet debug failed: Signer file not found: signer.txt. Tried: ['/workspace/sonic5/signer.txt', '/workspace/sonic5/backend/services/signer.txt', '/workspace/sonic5/backend/signer.txt']"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "string"
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_wallet_debug.json",
  "examples": [
    {
      "detail": "wallet debug failed: Signer file not found: signer.txt. Tried: ['/workspace/sonic5/signer.txt', '/workspace/sonic5/backend/services/signer.txt', '/workspace/sonic5/backend/signer.txt']"
    }
  ]
}
```

---

### SCHEMA-API_WALLET_SEND
**Used by:** `POST /api/wallet/send`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_wallet_send.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_WALLETS_VERIFY
**Used by:** `POST /api/wallets/verify`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_wallets_verify.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-API_WALLETS_VERIFY-BULK
**Used by:** `POST /api/wallets/verify-bulk`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/api_wallets_verify-bulk.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-CYCLONE_DATA
**Used by:** `DELETE /cyclone/data`

**Example**
```json
{
  "status": "clear started"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    }
  },
  "required": [
    "status"
  ],
  "additionalProperties": true,
  "$id": "schema/cyclone_data.json",
  "examples": [
    {
      "status": "clear started"
    }
  ]
}
```

---

### SCHEMA-CYCLONE_POSITIONS
**Used by:** `POST /cyclone/positions`

**Example**
```json
{
  "status": "position update started"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    }
  },
  "required": [
    "status"
  ],
  "additionalProperties": true,
  "$id": "schema/cyclone_positions.json",
  "examples": [
    {
      "status": "position update started"
    }
  ]
}
```

---

### SCHEMA-CYCLONE_PRICES
**Used by:** `POST /cyclone/prices`

**Example**
```json
{
  "status": "price update started"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    }
  },
  "required": [
    "status"
  ],
  "additionalProperties": true,
  "$id": "schema/cyclone_prices.json",
  "examples": [
    {
      "status": "price update started"
    }
  ]
}
```

---

### SCHEMA-CYCLONE_RUN
**Used by:** `POST /cyclone/run`

**Example**
```json
{
  "status": "cycle started"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    }
  },
  "required": [
    "status"
  ],
  "additionalProperties": true,
  "$id": "schema/cyclone_run.json",
  "examples": [
    {
      "status": "cycle started"
    }
  ]
}
```

---

### SCHEMA-DB_ADMIN_TABLES
**Used by:** `GET /db_admin/tables`

**Example**
```json
[
  "monitor_ledger",
  "wallets",
  "alerts",
  "alert_thresholds",
  "brokers",
  "positions",
  "positions_totals_history",
  "modifiers",
  "prices",
  "monitor_heartbeat",
  "global_config",
  "system_vars",
  "traders",
  "sessions",
  "alert_config",
  "alert_threshold",
  "alert_state",
  "alert_event",
  "sonic_monitor_log"
]
```

**Schema**
```json
{
  "type": "array",
  "items": {
    "type": "string"
  },
  "$id": "schema/db_admin_tables.json",
  "examples": [
    [
      "monitor_ledger",
      "wallets",
      "alerts",
      "alert_thresholds",
      "brokers",
      "positions",
      "positions_totals_history",
      "modifiers",
      "prices",
      "monitor_heartbeat",
      "global_config",
      "system_vars",
      "traders",
      "sessions",
      "alert_config",
      "alert_threshold",
      "alert_state",
      "alert_event",
      "sonic_monitor_log"
    ]
  ]
}
```

---

### SCHEMA-DB_ADMIN_TABLES_{TABLE}
**Used by:** `GET /db_admin/tables/{table}`

**Example**
```json
[]
```

**Schema**
```json
{
  "type": "array",
  "items": {
    "type": "string"
  },
  "$id": "schema/db_admin_tables_{table}.json",
  "examples": [
    []
  ]
}
```

---

### SCHEMA-MONITOR_STATUS
**Used by:** `GET /monitor_status/`

**Example**
```json
{
  "monitors": {
    "Sonic Monitoring": {
      "status": "Healthy",
      "last_updated": "2025-07-13T17:06:13.150233Z",
      "metadata": {}
    },
    "Price Monitoring": {
      "status": "Error",
      "last_updated": "2025-09-20T12:07:58.921221Z",
      "metadata": {}
    },
    "Positions Monitoring": {
      "status": "Error",
      "last_updated": "2025-09-20T12:07:59.087978Z",
      "metadata": {}
    },
    "XCom Communication": {
      "status": "Warning",
      "last_updated": "2025-07-13T18:16:12.176846Z",
      "metadata": {}
    }
  },
  "sonic_next": 0,
  "liquid_snooze": 0,
  "sonic_last_complete": "2025-07-13T17:06:13.150233+00:00"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "monitors": {
      "type": "object",
      "properties": {
        "Sonic Monitoring": {
          "type": "object",
          "properties": {
            "status": {
              "type": "string"
            },
            "last_updated": {
              "type": "string"
            },
            "metadata": {
              "type": "object",
              "properties": {},
              "additionalProperties": true
            }
          },
          "required": [
            "status"
          ],
          "additionalProperties": true
        },
        "Price Monitoring": {
          "type": "object",
          "properties": {
            "status": {
              "type": "string"
            },
            "last_updated": {
              "type": "string"
            },
            "metadata": {
              "type": "object",
              "properties": {},
              "additionalProperties": true
            }
          },
          "required": [
            "status"
          ],
          "additionalProperties": true
        },
        "Positions Monitoring": {
          "type": "object",
          "properties": {
            "status": {
              "type": "string"
            },
            "last_updated": {
              "type": "string"
            },
            "metadata": {
              "type": "object",
              "properties": {},
              "additionalProperties": true
            }
          },
          "required": [
            "status"
          ],
          "additionalProperties": true
        },
        "XCom Communication": {
          "type": "object",
          "properties": {
            "status": {
              "type": "string"
            },
            "last_updated": {
              "type": "string"
            },
            "metadata": {
              "type": "object",
              "properties": {},
              "additionalProperties": true
            }
          },
          "required": [
            "status"
          ],
          "additionalProperties": true
        }
      },
      "additionalProperties": true
    },
    "sonic_next": {
      "type": "number"
    },
    "liquid_snooze": {
      "type": "number"
    },
    "sonic_last_complete": {
      "type": "string"
    }
  },
  "additionalProperties": true,
  "$id": "schema/monitor_status.json",
  "examples": [
    {
      "monitors": {
        "Sonic Monitoring": {
          "status": "Healthy",
          "last_updated": "2025-07-13T17:06:13.150233Z",
          "metadata": {}
        },
        "Price Monitoring": {
          "status": "Error",
          "last_updated": "2025-09-20T12:07:58.921221Z",
          "metadata": {}
        },
        "Positions Monitoring": {
          "status": "Error",
          "last_updated": "2025-09-20T12:07:59.087978Z",
          "metadata": {}
        },
        "XCom Communication": {
          "status": "Warning",
          "last_updated": "2025-07-13T18:16:12.176846Z",
          "metadata": {}
        }
      },
      "sonic_next": 0,
      "liquid_snooze": 0,
      "sonic_last_complete": "2025-07-13T17:06:13.150233+00:00"
    }
  ]
}
```

---

### SCHEMA-MONITORS
**Used by:** `GET /monitors/`

**Example**
```json
[
  "liquid_monitor",
  "market_monitor",
  "operations_monitor",
  "position_monitor",
  "price_monitor",
  "profit_monitor",
  "risk_monitor",
  "twilio_monitor",
  "xcom_monitor"
]
```

**Schema**
```json
{
  "type": "array",
  "items": {
    "type": "string"
  },
  "$id": "schema/monitors.json",
  "examples": [
    [
      "liquid_monitor",
      "market_monitor",
      "operations_monitor",
      "position_monitor",
      "price_monitor",
      "profit_monitor",
      "risk_monitor",
      "twilio_monitor",
      "xcom_monitor"
    ]
  ]
}
```

---

### SCHEMA-MONITORS_SONIC_CYCLE
**Used by:** `POST /monitors/sonic_cycle`

**Example**
```json
{
  "status": "sonic cycle started"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    }
  },
  "required": [
    "status"
  ],
  "additionalProperties": true,
  "$id": "schema/monitors_sonic_cycle.json",
  "examples": [
    {
      "status": "sonic cycle started"
    }
  ]
}
```

---

### SCHEMA-MONITORS_SONIC_EVENTS
**Used by:** `GET /monitors/sonic_events`

**Example**
```json
{
  "event": "sonic_complete",
  "data": "done"
}
```

**Schema**
```json
{
  "$id": "schema/monitors_sonic_events.json",
  "type": "object",
  "properties": {
    "event": {
      "type": "string"
    },
    "data": {
      "type": "string"
    }
  },
  "required": [
    "event",
    "data"
  ],
  "additionalProperties": false,
  "examples": [
    {
      "event": "sonic_complete",
      "data": "done"
    }
  ]
}
```

---

### SCHEMA-MONITORS_{NAME}
**Used by:** `POST /monitors/{name}`

**Example**
```json
{
  "detail": "Monitor '{name}' not found"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "string"
    }
  },
  "additionalProperties": true,
  "$id": "schema/monitors_{name}.json",
  "examples": [
    {
      "detail": "Monitor '{name}' not found"
    }
  ]
}
```

---

### SCHEMA-MONITORSTATUS
**Used by:** `GET /api/monitor-status/`

**Example**
```json
{
  "timestamp": "2025-09-20T11:51:39Z",
  "status": "ok"
}
```

**Schema**
```json
{
  "$id": "schema/MonitorStatus.json",
  "type": "object",
  "required": [
    "timestamp"
  ],
  "properties": {
    "status": {
      "type": "string",
      "enum": [
        "ok",
        "degraded",
        "error"
      ]
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    }
  },
  "additionalProperties": true,
  "examples": [
    {
      "timestamp": "2025-09-20T11:51:39Z",
      "status": "ok"
    }
  ]
}
```

---

### SCHEMA-PORTFOLIO
**Used by:** `GET /portfolio/latest`, `GET /portfolio/`, `POST /portfolio/`

**Example**
```json
{
  "balances": [
    {
      "mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
      "amount": "1000000",
      "decimals": 6
    }
  ],
  "positions": {
    "items": [
      {
        "symbol": "SOL",
        "side": "long",
        "sizeUsd": 25.0,
        "entryPrice": 155.12
      }
    ],
    "count": 1
  }
}
```

**Schema**
```json
{
  "$id": "schema/Portfolio.json",
  "type": "object",
  "required": [
    "balances",
    "positions"
  ],
  "properties": {
    "balances": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "mint",
          "amount",
          "decimals"
        ],
        "properties": {
          "mint": {
            "type": "string"
          },
          "amount": {
            "type": "string",
            "description": "raw atoms as string"
          },
          "decimals": {
            "type": "integer",
            "minimum": 0
          }
        }
      }
    },
    "positions": {
      "$ref": "Positions.json"
    }
  },
  "examples": [
    {
      "balances": [
        {
          "mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
          "amount": "1000000",
          "decimals": 6
        }
      ],
      "positions": {
        "items": [
          {
            "symbol": "SOL",
            "side": "long",
            "sizeUsd": 25.0,
            "entryPrice": 155.12
          }
        ],
        "count": 1
      }
    }
  ]
}
```

---

### SCHEMA-PORTFOLIO_{ENTRY_ID}
**Used by:** `PUT /portfolio/{entry_id}`, `DELETE /portfolio/{entry_id}`

**Example**
```json
{
  "status": "deleted"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    }
  },
  "required": [
    "status"
  ],
  "additionalProperties": true,
  "$id": "schema/portfolio_{entry_id}.json",
  "examples": [
    {
      "status": "deleted"
    }
  ]
}
```

---

### SCHEMA-POSITION
**Used by:** _not mapped_

**Example**
```json
{
  "symbol": "SOL",
  "side": "long",
  "sizeUsd": 25.0,
  "entryPrice": 155.12,
  "metadata": {
    "note": "typical small long"
  }
}
```

**Schema**
```json
{
  "$id": "schema/Position.json",
  "type": "object",
  "required": [
    "symbol",
    "side",
    "sizeUsd",
    "entryPrice"
  ],
  "properties": {
    "symbol": {
      "type": "string",
      "examples": [
        "SOL",
        "ETH"
      ]
    },
    "side": {
      "type": "string",
      "enum": [
        "long",
        "short"
      ]
    },
    "sizeUsd": {
      "type": "number",
      "minimum": 0
    },
    "entryPrice": {
      "type": "number",
      "minimum": 0
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    }
  },
  "examples": [
    {
      "symbol": "SOL",
      "side": "long",
      "sizeUsd": 25.0,
      "entryPrice": 155.12,
      "metadata": {
        "note": "typical small long"
      }
    },
    {
      "symbol": "ETH",
      "side": "short",
      "sizeUsd": 10000.0,
      "entryPrice": 3100.0,
      "metadata": {
        "risk": "hedge"
      }
    }
  ]
}
```

---

### SCHEMA-POSITIONS
**Used by:** `GET /positions/`, `POST /positions/`

**Example**
```json
{
  "items": [
    {
      "symbol": "SOL",
      "side": "long",
      "sizeUsd": 25.0,
      "entryPrice": 155.12
    }
  ],
  "count": 1
}
```

**Schema**
```json
{
  "$id": "schema/Positions.json",
  "type": "object",
  "required": [
    "items"
  ],
  "properties": {
    "items": {
      "type": "array",
      "items": {
        "$ref": "Position.json"
      }
    },
    "count": {
      "type": "integer",
      "minimum": 0
    }
  },
  "examples": [
    {
      "items": [
        {
          "symbol": "SOL",
          "side": "long",
          "sizeUsd": 25.0,
          "entryPrice": 155.12
        }
      ],
      "count": 1
    }
  ]
}
```

---

### SCHEMA-POSITIONS_ENRICH
**Used by:** `POST /positions/enrich`

**Example**
```json
{
  "msg": "Enrichment started"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "msg": {
      "type": "string"
    }
  },
  "additionalProperties": true,
  "$id": "schema/positions_enrich.json",
  "examples": [
    {
      "msg": "Enrichment started"
    }
  ]
}
```

---

### SCHEMA-POSITIONS_SNAPSHOT
**Used by:** `POST /positions/snapshot`

**Example**
```json
{
  "status": "snapshot recorded"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    }
  },
  "required": [
    "status"
  ],
  "additionalProperties": true,
  "$id": "schema/positions_snapshot.json",
  "examples": [
    {
      "status": "snapshot recorded"
    }
  ]
}
```

---

### SCHEMA-POSITIONS_UPDATE
**Used by:** `POST /positions/update`

**Example**
```json
{
  "msg": "Position sync started"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "msg": {
      "type": "string"
    }
  },
  "additionalProperties": true,
  "$id": "schema/positions_update.json",
  "examples": [
    {
      "msg": "Position sync started"
    }
  ]
}
```

---

### SCHEMA-POSITIONS_{POS_ID}
**Used by:** `DELETE /positions/{pos_id}`

**Example**
```json
{
  "status": "deleted"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    }
  },
  "required": [
    "status"
  ],
  "additionalProperties": true,
  "$id": "schema/positions_{pos_id}.json",
  "examples": [
    {
      "status": "deleted"
    }
  ]
}
```

---

### SCHEMA-PRICES
**Used by:** `GET /prices/`

**Example**
```json
[]
```

**Schema**
```json
{
  "type": "array",
  "items": {
    "type": "string"
  },
  "$id": "schema/prices.json",
  "examples": [
    []
  ]
}
```

---

### SCHEMA-SESSION
**Used by:** _not mapped_

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/session.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-SESSION_HISTORY
**Used by:** `GET /session/history`

**Example**
```json
[]
```

**Schema**
```json
{
  "type": "array",
  "items": {
    "type": "string"
  },
  "$id": "schema/session_history.json",
  "examples": [
    []
  ]
}
```

---

### SCHEMA-SESSION_STATE
**Used by:** `GET /session/`, `POST /session/`, `PUT /session/`, `POST /session/reset`, `POST /session/close`

**Example**
```json
null
```

**Schema**
```json
{
  "$id": "schema/session_state.json",
  "type": [
    "null",
    "object"
  ],
  "description": "Active session state when no session is running the API returns null.",
  "properties": {},
  "examples": [
    null
  ],
  "additionalProperties": true
}
```

---

### SCHEMA-SESSION_{SID}
**Used by:** `PUT /session/{sid}`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/session_{sid}.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-WALLETS
**Used by:** `GET /wallets/`, `POST /wallets/`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/wallets.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-WALLETS_STAR_WARS
**Used by:** `POST /wallets/star_wars`

**Example**
```json
{
  "status": "inserted",
  "count": 0
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    },
    "count": {
      "type": "number"
    }
  },
  "required": [
    "status"
  ],
  "additionalProperties": true,
  "$id": "schema/wallets_star_wars.json",
  "examples": [
    {
      "status": "inserted",
      "count": 0
    }
  ]
}
```

---

### SCHEMA-WALLETS_{NAME}
**Used by:** `PUT /wallets/{name}`, `DELETE /wallets/{name}`

**Example**
```json
{
  "status": "deleted"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    }
  },
  "required": [
    "status"
  ],
  "additionalProperties": true,
  "$id": "schema/wallets_{name}.json",
  "examples": [
    {
      "status": "deleted"
    }
  ]
}
```

---

### SCHEMA-XCOM_LAST_PING
**Used by:** `GET /xcom/last_ping`

**Example**
```json
{
  "comm_type": "system",
  "source": "system",
  "timestamp": "6:16 PM"
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "comm_type": {
      "type": "string"
    },
    "source": {
      "type": "string"
    },
    "timestamp": {
      "type": "string"
    }
  },
  "required": [
    "timestamp"
  ],
  "additionalProperties": true,
  "$id": "schema/xcom_last_ping.json",
  "examples": [
    {
      "comm_type": "system",
      "source": "system",
      "timestamp": "6:16 PM"
    }
  ]
}
```

---

### SCHEMA-XCOM_PROVIDERS
**Used by:** `GET /xcom/providers`, `PUT /xcom/providers`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/xcom_providers.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```

---

### SCHEMA-XCOM_STATUS
**Used by:** `GET /xcom/status`

**Example**
```json
{
  "smtp": "please run connection tests",
  "twilio": "Missing Twilio credentials"
}
```

**Schema**
```json
{
  "$id": "schema/xcom_status.json",
  "type": "object",
  "description": "Status flags returned by the XCom health probe.",
  "additionalProperties": {
    "type": "string"
  },
  "examples": [
    {
      "smtp": "please run connection tests",
      "twilio": "Missing Twilio credentials"
    }
  ]
}
```

---

### SCHEMA-XCOM_TEST
**Used by:** `POST /xcom/test`

**Example**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "body"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Schema**
```json
{
  "type": "object",
  "properties": {
    "detail": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string"
          },
          "loc": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "msg": {
            "type": "string"
          },
          "input": {
            "type": [
              "null",
              "string",
              "number",
              "object",
              "array",
              "boolean"
            ]
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": true,
  "$id": "schema/xcom_test.json",
  "examples": [
    {
      "detail": [
        {
          "type": "missing",
          "loc": [
            "body"
          ],
          "msg": "Field required",
          "input": null
        }
      ]
    }
  ]
}
```
