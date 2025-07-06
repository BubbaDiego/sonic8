# Alert Thresholds API

This document describes the REST endpoints under `/alert_thresholds`.

## Endpoints

- `GET /alert_thresholds/` – List all threshold records.
- `GET /alert_thresholds/{id}` – Retrieve a single threshold.
- `POST /alert_thresholds/` – Create a new threshold. If `id` is omitted a UUID is generated.
- `PUT /alert_thresholds/{id}` – Update an existing threshold with a JSON body of fields to change.
- `DELETE /alert_thresholds/{i[seed_alert_thresholds.py](../backend/scripts/seed_alert_thresholds.py)d}` – Delete a threshold.

Bulk import/export endpoints will live under `/alert_thresholds/bulk` once the feature is implemented.

## Payload shape

Threshold objects use the following fields:

```json
{
  "id": "string",
  "alert_type": "string",
  "alert_class": "string",
  "metric_key": "string",
  "condition": "string",
  "low": 0.0,
  "medium": 0.0,
  "high": 0.0,
  "enabled": true,
  "last_modified": "ISO8601",
  "low_notify": "",
  "medium_notify": "",
  "high_notify": ""
}
```

## Example commands

```bash
# list existing thresholds
curl http://localhost:5000/alert_thresholds/

# create a new threshold
curl -X POST http://localhost:5000/alert_thresholds/ \
     -H 'Content-Type: application/json' \
     -d '{"alert_type":"TravelPercent","alert_class":"Position","metric_key":"travel_percent","condition":"BELOW","low":50,"medium":70,"high":90}'

# update threshold by id
curl -X PUT http://localhost:5000/alert_thresholds/<id> \
     -H 'Content-Type: application/json' \
     -d '{"enabled":false}'

# delete threshold by id
curl -X DELETE http://localhost:5000/alert_thresholds/<id>
```
