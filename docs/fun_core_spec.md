
# fun_core — Design & API Specification

**Version:** 1.0  
**Last updated:** 2025-07-31 04:06:21

fun_core is a lightweight content micro‑service delivering short
'fun' payloads such as jokes, trivia questions and inspirational
quotes.  It wraps multiple public APIs behind a unified FastAPI
router to provide zero‑config entertainment for the Sonic frontend.

## Endpoints
| Method | Path              | Query params      | Description                   |
| ------ | ----------------- | ----------------- | ----------------------------- |
| GET    | `/api/fun/random` | `type=<enum>`     | Returns a random FunContent.  |

### FunType values
* `joke`
* `trivia`
* `quote`

### Response schema (FunContent)
```
{
  "type": "joke",
  "text": "Why did the scarecrow win an award? Because he was outstanding in his field.",
  "source": "JokeAPI",
  "fetched_at": "2025-07-31T17:00:00Z",
  "extra": null
}
```
