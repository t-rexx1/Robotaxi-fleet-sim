# Robotaxi Fleet Simulation

A multi-agent simulation of an autonomous robotaxi fleet with real-time interactive dashboard.

Built to demonstrate fleet-level simulation design: agent state machines, fault injection, data pipelines, and live visualisation — directly relevant to AV/robotaxi software engineering roles.

---

## What it does

- **15 autonomous agents** move across a 20×20 city grid
- Each agent has a full **state machine**: `AVAILABLE → DISPATCHED → RIDING → RETURNING → CHARGING → FAULT → OFFLINE`
- **Ride requests** are generated at random intervals; the fleet manager dispatches the nearest available agent
- **Fault injection scenarios**:
  - `random_fault` — fault one agent instantly
  - `mass_outage` — take 30–50% of the fleet offline
  - `battery_drain` — drain 3 agents to critical battery
  - `cascading_fault` — fault spreads to nearby agents
  - `rider_surge` — inject 5 simultaneous ride requests
- All tick metrics are **persisted to SQLite** (`data/simulation.db`)
- Live **Plotly dashboard** shows fleet map, state breakdown, utilisation trends, and event log

---

## Quick start

```bash
pip install -r requirements.txt

# Interactive dashboard
streamlit run dashboard/app.py

# Headless runner (generates dataset, no UI)
python main.py --ticks 200 --agents 15 --verbose
```

---

## Project structure

```
├── simulation/
│   ├── agent.py          # Agent state machine
│   ├── city_grid.py      # City grid + charging station placement
│   ├── fleet_manager.py  # Orchestration, dispatch, metrics
│   └── fault_injector.py # Fault scenarios
├── data/
│   └── logger.py         # SQLite data pipeline
├── dashboard/
│   └── app.py            # Streamlit real-time dashboard
├── main.py               # Headless CLI runner
└── requirements.txt
```

---

## Dashboard

| Panel | What it shows |
|---|---|
| Fleet Map | Live agent positions, state (colour + shape), hover for battery/trips |
| Fleet State Breakdown | Bar chart of agent count by state |
| Event Log | Colour-coded real-time events (faults in red, low battery in orange) |
| Fleet Utilisation | % of fleet actively dispatched or riding over time |
| Avg Battery & Faults | Battery health and fault count over simulation time |

### Controls

- **Start / Pause** — run or freeze the simulation
- **Inject Fault** — trigger any fault scenario mid-run
- **Bring All Online** — recover all offline agents
- **Reset** — start fresh
- **Fleet size** — resize the fleet (5–30 agents)
- **Tick speed** — control simulation speed

---

## Deploying to Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo, set main file to `dashboard/app.py`
4. Deploy — free, no config needed

---

## Tech stack

| Layer | Tool |
|---|---|
| Simulation core | Python — dataclasses, state machines |
| Visualisation | Plotly, Streamlit |
| Data pipeline | SQLite via `sqlite3` stdlib |
| Data processing | Pandas |
