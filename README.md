# Flight Fuel Stats API

FastAPI service to estimate route fuel usage using:
- origin and destination airport
- aircraft type
- route distance with a routing factor
- optional payload and contingency settings

The aircraft catalog now includes common long-haul types such as the 777-300ER, A380, 747-8, 787 variants, A350 variants, and A330-300.

## Endpoints

- GET /health
- GET /v1/aircraft
- GET /v1/airports/search?q=<query>
- GET /v1/fuel/by-route?origin=<code>&destination=<code>

### GET /v1/fuel/by-route example (no JSON body)

Request:

```bash
curl "http://127.0.0.1:8000/v1/fuel/by-route?origin=SFO&destination=LAX"
```

This returns all supported aircraft and the fuel estimate for each one, sorted by total fuel (lowest first).

Use optional query params for tuning:
- `routing_factor` (default `1.06`)
- `contingency_pct` (default `0.05`)
- `payload_kg` (default `12000` if omitted)

Response includes distance, block time, fuel breakdown in both kg and tons, and assumptions.

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
