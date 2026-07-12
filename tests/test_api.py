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


def test_fuel_by_route_success() -> None:
    response = client.get("/v1/fuel/by-route?origin=SFO&destination=LAX")
    assert response.status_code == 200
    data = response.json()
    assert data["origin"] == "SFO"
    assert data["destination"] == "LAX"
    assert len(data["estimates"]) >= 1
    assert data["estimates"][0]["fuel_kg"]["total_kg"] > 0


def test_fuel_by_route_same_origin_destination() -> None:
    response = client.get("/v1/fuel/by-route?origin=SFO&destination=SFO")
    assert response.status_code == 400


def test_fuel_by_route_ewr_to_del() -> None:
    response = client.get("/v1/fuel/by-route?origin=EWR&destination=DEL")
    assert response.status_code == 200
    data = response.json()
    assert data["origin"] == "EWR"
    assert data["destination"] == "DEL"
    assert len(data["estimates"]) >= 1
