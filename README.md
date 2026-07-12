# Flight Fuel Stats API

FastAPI service to estimate route fuel usage using:
- origin and destination airport
- aircraft type
- route distance with a routing factor
- optional payload and contingency settings

## Endpoints

- GET /health
- GET /v1/aircraft
- GET /v1/airports/search?q=<query>
- GET /v1/fuel/by-route?origin=<code>&destination=<code>
- POST /v1/fuel/estimate

### GET /v1/fuel/by-route example (no JSON body)

Request:

```bash
curl "http://127.0.0.1:8000/v1/fuel/by-route?origin=SFO&destination=LAX"
```

This returns all supported aircraft and the fuel estimate for each one, sorted by total fuel (lowest first).

### POST /v1/fuel/estimate example

Request:

```json
{
  "origin": "SFO",
  "destination": "LAX",
  "aircraft_type": "A320",
  "payload_kg": 12000,
  "routing_factor": 1.06,
  "contingency_pct": 0.05
}
```

Response includes distance, block time, fuel breakdown, and assumptions.

## Run locally

1. Create a virtual environment and install dependencies.
2. Start the API:

```bash
uvicorn app.main:app --reload
```

3. Open docs at /docs.

## Test

```bash
pytest -q
```

## Deploy to Render

This repo includes render.yaml for Blueprint deployment.

1. Push this project to GitHub.
2. In Render, choose New + then Blueprint.
3. Connect the GitHub repo and select this project.
4. Render reads render.yaml and provisions the web service.
5. After deploy, use:
   - /health for health checks
   - /docs for interactive API docs

Render start command is:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```
