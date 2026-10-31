# RouteMind — AI Route Planner

> Type your trip in plain English. RouteMind finds the optimal stop order, respects time windows, and shows everything on an interactive map.

---

## Demo

```
Start from Railway Station at 9am.
Deliver to Mananchira after 10am, Beach by 12pm.
Then stop at Medical College.
Return to start.
```

RouteMind reads the text, extracts stops and time windows, solves the Travelling Salesman Problem with time constraints (Held-Karp DP), and renders an annotated route on a Leaflet map.

---

## Features

| Feature | Detail |
|---|---|
| **Natural-language input** | Claude (Anthropic API) parses the trip; a regex fallback works offline |
| **Held-Karp solver** | Exact DP algorithm for ≤ 20 stops with time-window constraints |
| **Time windows** | "after 11am", "by 1pm", "at 9am" — wait times calculated automatically |
| **Leaflet map** | Interactive markers + dashed polyline; popups show arrival / wait / depart |
| **Dark UI** | Responsive two-pane layout: timeline panel + full-height map |
| **Geocoding** | Nominatim (OpenStreetMap) with offline Kozhikode landmark fallback |
| **No API key needed** | Regex parser handles common patterns; set `ANTHROPIC_API_KEY` for Claude |

---

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) Add Claude for smarter parsing
export ANTHROPIC_API_KEY=sk-ant-...

# 3. Run
python app.py
# → http://localhost:5000
```

---

## Project structure

```
routemind/
├── app.py            # Flask routes
├── solver.py         # Held-Karp TSP with time windows
├── trip_parser.py    # Claude + regex parser
├── geocode.py        # Nominatim + offline fallback
├── templates/
│   └── index.html    # Full UI (Leaflet map, timeline, dark theme)
├── tests/
│   └── test_routemind.py
├── requirements.txt
└── README.md
```

---

## Architecture

```
User text
    │
    ▼
trip_parser.py ──► Claude API  (if ANTHROPIC_API_KEY set)
    │           └► Regex fallback  (always available)
    │
    ▼  [{name, earliest, latest}, ...]
geocode.py ──► Nominatim / offline table → (lat, lon)
    │
    ▼  [Stop(name, lat, lon, earliest, latest), ...]
solver.py ──► Held-Karp bitmask DP → Solution(order, steps, km, feasible)
    │
    ▼
app.py ──► JSON response → Leaflet map + timeline
```

**Why AI only reads the text, not the route:**  
Claude is good at understanding ambiguous language but can produce invalid plans. The DP solver guarantees optimality and time-window correctness. This separation means the AI can't accidentally skip a stop or ignore a deadline.

---

## Held-Karp algorithm

Standard bitmask DP with O(2ⁿ · n²) complexity.

- `dp[mask][i]` = earliest time we can finish stop `i` having visited exactly the stops in `mask`
- At each state we try extending to every unvisited stop, obeying time windows (waiting if early, marking infeasible if late)
- Final answer: minimum time to return to depot after visiting all stops

For n ≤ 12 stops (typical delivery run) this solves in milliseconds.

---

## Known limitations

| Limitation | Impact |
|---|---|
| Straight-line distance × 1.3 detour factor | Travel times are estimates; not road distances |
| Map lines join stops directly | Not turn-by-turn; use OSRM/Google Maps API for real routing |
| Nominatim rate limit (1 req/s) | First request per stop takes ~1 s; cached afterwards |
| Held-Karp is exact but exponential | Practical up to ~18–20 stops; use heuristics beyond that |
| Offline coordinates are Kozhikode only | Other cities geocode via Nominatim (needs internet) |

---

## Deployment (Render free tier)

1. Push to GitHub
2. New **Web Service** → connect repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add env var `ANTHROPIC_API_KEY` in Render dashboard (optional)

---

## Running tests

```bash
pytest tests/ -v
```

---

## License

MIT
