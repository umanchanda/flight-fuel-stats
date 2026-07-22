import os
import time
from typing import Any

import httpx

from app.data.aircraft import AIRCRAFT_PROFILES

DEFAULT_ROUTE_ANALYZER_URL = "https://route-analyzer-nfu1.onrender.com/aircraft"
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_RETRIES = 3
DEFAULT_RETRY_BACKOFF_SECONDS = 0.6

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


def _int_from_env(name: str, default: int, *, min_value: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(min_value, value)


def _float_from_env(name: str, default: float, *, min_value: float = 0.0) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return max(min_value, value)


def _normalize(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().upper()


def _build_route_lookup_url(origin: str, destination: str) -> str:
    base_url = os.getenv("ROUTE_ANALYZER_BASE_URL", DEFAULT_ROUTE_ANALYZER_URL).rstrip("/")

    # Support both forms:
    # - https://.../aircraft
    # - https://...
    if not base_url.endswith("/aircraft"):
        base_url = f"{base_url}/aircraft"

    return f"{base_url}/{origin}/{destination}"


def _safe_json(response: httpx.Response) -> dict[str, Any] | None:
    try:
        payload = response.json()
    except ValueError:
        return None

    if isinstance(payload, dict):
        return payload
    return None


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
    url = _build_route_lookup_url(origin, destination)
    timeout_seconds = _float_from_env("ROUTE_ANALYZER_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS, min_value=1.0)
    retries = _int_from_env("ROUTE_ANALYZER_RETRIES", DEFAULT_RETRIES, min_value=1)
    retry_backoff_seconds = _float_from_env(
        "ROUTE_ANALYZER_RETRY_BACKOFF_SECONDS",
        DEFAULT_RETRY_BACKOFF_SECONDS,
        min_value=0.0,
    )

    response: httpx.Response | None = None
    last_error: Exception | None = None
    transient_statuses = {502, 503, 504}

    for attempt in range(retries):
        try:
            candidate = httpx.get(url, timeout=timeout_seconds, follow_redirects=True)
        except httpx.HTTPError as exc:
            last_error = exc
            if attempt + 1 < retries and retry_backoff_seconds > 0:
                time.sleep(retry_backoff_seconds * (2**attempt))
            continue

        if candidate.status_code in transient_statuses and attempt + 1 < retries:
            if retry_backoff_seconds > 0:
                time.sleep(retry_backoff_seconds * (2**attempt))
            continue

        response = candidate
        break

    if response is None:
        raise RouteAircraftLookupError("Failed to fetch route aircraft data") from last_error

    payload = _safe_json(response)
    route_notes = payload.get("routeNotes") if payload else None

    # Upstream may use 4xx for unsupported routes.
    if response.status_code in {400, 404, 422}:
        return False, [], route_notes
    if response.status_code == 429:
        raise RouteAircraftLookupError("Route analyzer rate limit exceeded")
    if response.status_code >= 500:
        raise RouteAircraftLookupError("Route analyzer service is unavailable")
    if response.status_code >= 400:
        raise RouteAircraftLookupError("Route analyzer rejected the request")

    if payload is None:
        raise RouteAircraftLookupError("Invalid route analyzer response format")

    route_exists = bool(payload.get("routeExists"))
    aircraft_items = payload.get("aircraft", [])
    if not route_exists and isinstance(aircraft_items, list) and len(aircraft_items) > 0:
        # Some upstream deployments omit routeExists on successful matches.
        route_exists = True

    if not route_exists:
        return False, [], route_notes

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
