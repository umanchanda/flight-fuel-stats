import httpx
import pytest

from app.services.route_aircraft import RouteAircraftLookupError, get_supported_aircraft_for_route


def test_get_supported_aircraft_for_route_treats_upstream_400_as_no_route(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_get(_url: str, timeout: float, follow_redirects: bool) -> httpx.Response:
        assert timeout > 0
        assert follow_redirects is True
        return httpx.Response(400, json={"routeNotes": "route not found"})

    monkeypatch.setattr(httpx, "get", mock_get)

    route_exists, aircraft_codes, route_notes = get_supported_aircraft_for_route("SFO", "LAX")

    assert route_exists is False
    assert aircraft_codes == []
    assert route_notes == "route not found"


def test_get_supported_aircraft_for_route_accepts_payload_without_route_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_get(_url: str, timeout: float, follow_redirects: bool) -> httpx.Response:
        assert timeout > 0
        assert follow_redirects is True
        return httpx.Response(
            200,
            json={
                "aircraft": [
                    {"icao": "B77W", "iata": "77W", "type": "Boeing 777-300ER"},
                ]
            },
        )

    monkeypatch.setattr(httpx, "get", mock_get)

    route_exists, aircraft_codes, route_notes = get_supported_aircraft_for_route("EWR", "DEL")

    assert route_exists is True
    assert aircraft_codes == ["B77W"]
    assert route_notes is None


def test_get_supported_aircraft_for_route_raises_on_429(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_get(_url: str, timeout: float, follow_redirects: bool) -> httpx.Response:
        assert timeout > 0
        assert follow_redirects is True
        return httpx.Response(429)

    monkeypatch.setattr(httpx, "get", mock_get)

    with pytest.raises(RouteAircraftLookupError):
        get_supported_aircraft_for_route("SFO", "LAX")
