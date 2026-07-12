import os
from typing import Any

import httpx

from app.data.aircraft import AIRCRAFT_PROFILES

DEFAULT_ROUTE_ANALYZER_URL = "https://route-analyzer-nfu1.onrender.com/aircraft"

# Map known external IATA/ICAO/type identifiers to local aircraft catalog codes.
AIRCRAFT_CODE_ALIASES: dict[str, str] = {
    "B77L": "B772LR",
    "77L": "B772LR",
    "B772": "B772LR",
    "772": "B772LR",
    "B789": "B787",
    "789": "B787",
    "B77W": "B77W",
    "77W": "B77W",
    "B78X": "B78X",
    "78X": "B78X",
    "A359": "A350",
    "359": "A350",
    "A35K": "A35K",
    "35K": "A35K",
    "A333": "A333",
    "333": "A333",
    "A388": "A388",
    "388": "A388",
    "B748": "B748",
    "748": "B748",
    "A320": "A320",
    "320": "A320",
    "B738": "B737",
    "738": "B737",
}

TYPE_ALIASES: dict[str, str] = {
    "BOEING 777-300ER": "B77W",
    "BOEING 777-200LR": "B772LR",
    "BOEING 777-200ER": "B772LR",
    "BOEING 787-9 DREAMLINER": "B787",
    "BOEING 787-10 DREAMLINER": "B78X",
    "AIRBUS A350-900": "A350",
    "AIRBUS A350-1000": "A35K",
    "AIRBUS A330-300": "A333",
    "AIRBUS A380-800": "A388",
    "BOEING 747-8": "B748",
    "AIRBUS A320": "A320",
    "BOEING 737-800": "B737",
}


class RouteAircraftLookupError(Exception):
    pass


def _normalize(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().upper()


def _resolve_local_code(aircraft_item: dict[str, Any]) -> str | None:
    icao = _normalize(str(aircraft_item.get("icao", "")))
    iata = _normalize(str(aircraft_item.get("iata", "")))
    aircraft_type = _normalize(str(aircraft_item.get("type", "")))

    candidates = [icao, iata]
    for candidate in candidates:
        if not candidate:
            continue
        code = AIRCRAFT_CODE_ALIASES.get(candidate, candidate)
        if code in AIRCRAFT_PROFILES:
            return code

    if aircraft_type in TYPE_ALIASES:
        type_code = TYPE_ALIASES[aircraft_type]
        if type_code in AIRCRAFT_PROFILES:
            return type_code

    return None


def get_supported_aircraft_for_route(origin: str, destination: str) -> tuple[bool, list[str], str | None]:
    base_url = os.getenv("ROUTE_ANALYZER_BASE_URL", DEFAULT_ROUTE_ANALYZER_URL).rstrip("/")
    url = f"{base_url}/{origin}/{destination}"

    try:
        response = httpx.get(url, timeout=8.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RouteAircraftLookupError("Failed to fetch route aircraft data") from exc

    payload = response.json()
    route_exists = bool(payload.get("routeExists", False))
    route_notes = payload.get("routeNotes")

    if not route_exists:
        return False, [], route_notes

    aircraft_items = payload.get("aircraft", [])
    if not isinstance(aircraft_items, list):
        raise RouteAircraftLookupError("Invalid route analyzer response format")

    selected: list[str] = []
    for item in aircraft_items:
        if not isinstance(item, dict):
            continue
        code = _resolve_local_code(item)
        if code and code not in selected:
            selected.append(code)

    return True, selected, route_notes
