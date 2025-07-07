# 🧠 Trader Core Specification

> Version: `v1.5`
> Author: `CoreOps 🧠`
> Scope: Build, persist, and manage Trader personas tied to portfolio strategy and mood evaluation.


---

## 📂 Module Structure
```txt
trader_core/
├── __init__.py                # Package marker
├── trader_core.py             # Main service logic
├── trader_store.py            # In-memory fallback store
├── trader_factory_service.py  # UI helper around TraderCore
├── trader_loader.py           # Build Trader from live data
├── mood_engine.py             # Heat-based mood selection
├── persona_avatars.py         # Avatar registry
├── personas/                  # Example persona JSON files
├── trader_bp.py               # Flask blueprint
├── trader_core_spec.md        # This document
├── trader_core_ui_spec.md     # UI overview
├── ../models/trader.py        # Trader dataclass
```
The `personas/` directory stores predefined persona JSON files used by `PersonaManager`.

---

## 🧠 Purpose
The Trader module generates strategy-aware trader personas from live portfolio data, based on:
- Persona configuration
- Strategy weights
- Risk & heat index metrics

It serves:
- Console workflows
- GPT query context
- UI previews + saving to DB

---
 
## ⚙️ `TraderCore`

### Constructor
```python
TraderCore(data_locker, persona_manager=None, strategy_manager=None)
```

### Key Methods
| Method                | Description |
|-----------------------|-------------|
| `create_trader(name)` | Generate Trader object with live metrics |
| `save_trader(t)`      | Save to DB or fallback to memory |
| `get_trader(name)`    | Load trader, fall back to create + cache |
| `list_traders()`      | List all persisted or persona-based traders |
| `delete_trader(name)` | Remove from DL or memory store |
| `refresh_trader(name)` | Recalculate wallet metrics and persist |

---

## 📋 Trader Dataclass
```python
@dataclass
class Trader:
    name: str
    avatar: str = ""
    color: str = ""
    persona: str = ""
    origin_story: str = ""
    risk_profile: str = ""
    born_on: str = ""
    initial_collateral: float = 0.0
    mood: str = "neutral"
    moods: Dict[str, str] = field(default_factory=dict)
    strategies: Dict[str, float] = field(default_factory=dict)
    strategy_notes: str = ""
    wallet: str = ""
    wallet_balance: float = 0.0
    profit: float = 0.0
    portfolio: Dict = field(default_factory=dict)
    positions: List[Dict] = field(default_factory=list)
    hedges: List[Dict] = field(default_factory=list)
    performance_score: int = 0
    heat_index: float = 0.0


## 🛢️ Persistence

### 🔘 In-Memory Store
Used for dev testing (`TraderStore`)

### 💾 DL Trader Store (`DLTraderManager`)
- Table: `traders`
- Fields:
  - `name TEXT PRIMARY KEY`
  - `trader_json TEXT NOT NULL`
  - `created_at TEXT`
  - `last_updated TEXT`
- JSON-encodes entire object
- Fills missing `born_on` and `initial_collateral` when loading

---


## 🎨 UI (HTML)
The repository no longer includes HTML templates. `TraderFactoryService`
can be used by a separate Flask app to build pages with features such as:
- dropdown persona selection
- preview panels
- save and delete actions
- real-time metrics

---

## 🚏 Flask Routes
All paths are under the `/trader` blueprint prefix.
- `/shop` – legacy shop page for managing personas (template not included)
- `/factory/<name>` – minimal factory view for tests
- `/cards` – legacy page showing trader names
- `/api/wallets` – list wallet names and balances
- `/api/traders/create` – create a new trader entry
- `/api/traders/create_star_wars` – generate sample Star Wars traders
- `/api/traders/quick_import` – build traders from active wallets
- `/api/persona_colors` – return persona color mapping
- `/api/persona_colors/<name>` – update a persona's color
- `/api/traders/<name>` (GET) – fetch trader details
- `/api/traders` (GET) – list all traders with metrics
- `/api/traders/<name>` (PUT) – update trader fields
- `/api/traders/<name>/delete` – delete a trader
- `/api/traders/delete_all` – remove all traders
- `/api/traders/export` – export traders to `active_traders.json`
- `/api/traders/import` – import traders from a JSON file or payload

---

## 🔮 GPT Integration
`OracleCore.ask_trader()` uses Trader object to:
- Merge persona strategy modifiers
- Add context from trader.portfolio + positions
- Inject mood

---

## ✅ Summary
TraderCore makes GPT-guided trader personas actionable.
It enables strategy tuning, UI simulation, logging, and full DB lifecycle management.
Perfect for simulation dashboards, GPT context delivery, and user-driven portfolios.

---
