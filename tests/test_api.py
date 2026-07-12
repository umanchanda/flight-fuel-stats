from fastapi.testclient import TestClient

from app import main as main_module
from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_aircraft_catalog_includes_long_haul_types() -> None:
    response = client.get("/v1/aircraft")
    assert response.status_code == 200
    data = response.json()
    codes = {item["code"] for item in data["aircraft"]}
    assert {"B77W", "A388", "B748"}.issubset(codes)


def test_airport_search_includes_new_airports() -> None:
    response = client.get("/v1/airports/search?q=SYD")
    assert response.status_code == 200
    data = response.json()
    codes = {item["code"] for item in data["airports"]}
    assert "SYD" in codes

    response = client.get("/v1/airports/search?q=Shanghai")
    assert response.status_code == 200
    data = response.json()
    codes = {item["code"] for item in data["airports"]}
    assert "PVG" in codes

    response = client.get("/v1/airports/search?q=Paris")
    assert response.status_code == 200
    data = response.json()
    codes = {item["code"] for item in data["airports"]}
    assert "CDG" in codes

    response = client.get("/v1/airports/search?q=Amsterdam")
    assert response.status_code == 200
    data = response.json()
    codes = {item["code"] for item in data["airports"]}
    assert "AMS" in codes

    response = client.get("/v1/airports/search?q=Hamad")
    assert response.status_code == 200
    data = response.json()
    codes = {item["code"] for item in data["airports"]}
    assert "DOH" in codes

    response = client.get("/v1/airports/search?q=Singapore")
    assert response.status_code == 200
    data = response.json()
    codes = {item["code"] for item in data["airports"]}
    assert "SIN" in codes


def test_fuel_by_route_success() -> None:
    def mock_route_lookup(origin: str, destination: str) -> tuple[bool, list[str], str | None]:
        assert origin == "SFO"
        assert destination == "LAX"
        return True, ["A320", "B737"], None

    main_module.get_supported_aircraft_for_route = mock_route_lookup

    response = client.get("/v1/fuel/by-route?origin=SFO&destination=LAX")
    assert response.status_code == 200
    data = response.json()
    assert data["origin"] == "SFO"
    assert data["destination"] == "LAX"
    assert len(data["estimates"]) == 2
    types = {item["aircraft_type"] for item in data["estimates"]}
    assert types == {"A320", "B737"}
    breakdown = data["estimates"][0]["fuel_tons"]
    assert breakdown["total_kg"] > 0
    assert breakdown["total_tons"] > 0
    assert breakdown["total_kg"] > breakdown["total_tons"]


def test_fuel_by_route_same_origin_destination() -> None:
    response = client.get("/v1/fuel/by-route?origin=SFO&destination=SFO")
    assert response.status_code == 400


def test_fuel_by_route_ewr_to_del() -> None:
    def mock_route_lookup(origin: str, destination: str) -> tuple[bool, list[str], str | None]:
        assert origin == "EWR"
        assert destination == "DEL"
        return True, ["B77W", "B772LR", "B787"], "mocked route notes"

    main_module.get_supported_aircraft_for_route = mock_route_lookup

    response = client.get("/v1/fuel/by-route?origin=EWR&destination=DEL")
    assert response.status_code == 200
    data = response.json()
    assert data["origin"] == "EWR"
    assert data["destination"] == "DEL"
    types = {item["aircraft_type"] for item in data["estimates"]}
    assert types == {"B77W", "B772LR", "B787"}


def test_fuel_by_route_returns_404_when_no_route_exists() -> None:
    def mock_route_lookup(_origin: str, _destination: str) -> tuple[bool, list[str], str | None]:
        return False, [], None

    main_module.get_supported_aircraft_for_route = mock_route_lookup

    response = client.get("/v1/fuel/by-route?origin=SFO&destination=LAX")
    assert response.status_code == 404
