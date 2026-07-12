from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_fuel_estimate_success() -> None:
    payload = {
        "origin": "SFO",
        "destination": "LAX",
        "aircraft_type": "A320",
    }
    response = client.post("/v1/fuel/estimate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["origin"] == "SFO"
    assert data["destination"] == "LAX"
    assert data["aircraft_type"] == "A320"
    assert data["fuel_kg"]["total_kg"] > 0


def test_fuel_estimate_unknown_airport() -> None:
    payload = {
        "origin": "XXX",
        "destination": "LAX",
        "aircraft_type": "A320",
    }
    response = client.post("/v1/fuel/estimate", json=payload)
    assert response.status_code == 404
