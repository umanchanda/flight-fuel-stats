from fastapi import FastAPI, HTTPException, Query

from app.data.aircraft import AIRCRAFT_PROFILES
from app.data.airports import AIRPORTS
from app.models import (
    AircraftListResponse,
    AirportSearchResponse,
    FuelBreakdown,
    FuelComparisonDelta,
    FuelComparisonItem,
    FuelComparisonResponse,
    RouteFuelEstimateItem,
    RouteFuelEstimatesResponse,
)
from app.services.fuel import estimate_fuel
from app.services.route_aircraft import RouteAircraftLookupError, get_supported_aircraft_for_route

DEFAULT_PAYLOAD_KG = 12000.0

app = FastAPI(
    title="Flight Fuel Stats API",
    version="1.0.0",
    description="Estimate fuel consumption between origin and destination airports by aircraft type.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/aircraft", response_model=AircraftListResponse)
def list_aircraft() -> AircraftListResponse:
    aircraft = []
    for code, profile in AIRCRAFT_PROFILES.items():
        aircraft.append(
            {
                "code": code,
                "name": str(profile["name"]),
                "cruise_speed_kts": float(profile["cruise_speed_kts"]),
                "burn_kg_per_hour": float(profile["burn_kg_per_hour"]),
            }
        )
    return AircraftListResponse(aircraft=aircraft)


def _fuel_breakdown(result: dict[str, float]) -> FuelBreakdown:
    return FuelBreakdown(
        taxi_kg=result["taxi_kg"],
        taxi_tons=round(result["taxi_kg"] / 1000.0, 3),
        trip_kg=result["trip_kg"],
        trip_tons=round(result["trip_kg"] / 1000.0, 3),
        contingency_kg=result["contingency_kg"],
        contingency_tons=round(result["contingency_kg"] / 1000.0, 3),
        reserve_kg=result["reserve_kg"],
        reserve_tons=round(result["reserve_kg"] / 1000.0, 3),
        total_kg=result["total_kg"],
        total_tons=round(result["total_kg"] / 1000.0, 3),
    )


@app.get("/v1/airports/search", response_model=AirportSearchResponse)
def search_airports(q: str = Query(..., min_length=2, description="Airport code or name query")) -> AirportSearchResponse:
    query = q.strip().upper()
    matches = []

    for code, airport in AIRPORTS.items():
        if query in code or query in str(airport["name"]).upper():
            matches.append(
                {
                    "code": code,
                    "name": str(airport["name"]),
                    "lat": float(airport["lat"]),
                    "lon": float(airport["lon"]),
                }
            )

    return AirportSearchResponse(airports=matches)


@app.get("/v1/fuel/by-route", response_model=RouteFuelEstimatesResponse)
def fuel_by_route(
    origin: str = Query(..., min_length=3, max_length=4, description="IATA or ICAO origin code"),
    destination: str = Query(..., min_length=3, max_length=4, description="IATA or ICAO destination code"),
    routing_factor: float = Query(1.06, ge=1.0, le=1.2),
    contingency_pct: float = Query(0.05, ge=0.0, le=0.2),
    payload_kg: float | None = Query(None, ge=0.0),
) -> RouteFuelEstimatesResponse:
    origin_code = origin.strip().upper()
    destination_code = destination.strip().upper()

    if origin_code not in AIRPORTS:
        raise HTTPException(status_code=404, detail=f"Unknown origin airport: {origin_code}")
    if destination_code not in AIRPORTS:
        raise HTTPException(status_code=404, detail=f"Unknown destination airport: {destination_code}")
    if origin_code == destination_code:
        raise HTTPException(status_code=400, detail="Origin and destination must be different")

    origin_airport = AIRPORTS[origin_code]
    destination_airport = AIRPORTS[destination_code]
    effective_payload_kg = payload_kg if payload_kg is not None else DEFAULT_PAYLOAD_KG

    try:
        route_exists, route_aircraft_codes, _route_notes = get_supported_aircraft_for_route(origin_code, destination_code)
    except RouteAircraftLookupError as exc:
        raise HTTPException(status_code=502, detail="Unable to retrieve route aircraft data") from exc

    if not route_exists:
        raise HTTPException(status_code=404, detail=f"No known route found for {origin_code} to {destination_code}")
    if not route_aircraft_codes:
        raise HTTPException(
            status_code=404,
            detail=f"No supported aircraft found for route {origin_code} to {destination_code}",
        )

    estimates: list[RouteFuelEstimateItem] = []
    for aircraft_code in route_aircraft_codes:
        aircraft = AIRCRAFT_PROFILES[aircraft_code]
        result = estimate_fuel(
            origin=origin_airport,
            destination=destination_airport,
            aircraft=aircraft,
            routing_factor=routing_factor,
            contingency_pct=contingency_pct,
            payload_kg=effective_payload_kg,
        )
        estimates.append(
            RouteFuelEstimateItem(
                aircraft_type=aircraft_code,
                aircraft_name=str(aircraft["name"]),
                distance_nm=result["distance_nm"],
                block_time_min=result["block_time_min"],
                fuel_tons=_fuel_breakdown(result),
            )
        )

    estimates.sort(key=lambda item: item.fuel_tons.total_kg)

    return RouteFuelEstimatesResponse(
        origin=origin_code,
        destination=destination_code,
        assumptions={
            "routing_factor": routing_factor,
            "contingency_pct": contingency_pct,
            "payload_kg": effective_payload_kg,
        },
        estimates=estimates,
    )


def _comparison_item(aircraft_code: str, result: dict[str, float]) -> FuelComparisonItem:
    aircraft = AIRCRAFT_PROFILES[aircraft_code]
    return FuelComparisonItem(
        aircraft_type=aircraft_code,
        aircraft_name=str(aircraft["name"]),
        distance_nm=result["distance_nm"],
        block_time_min=result["block_time_min"],
        fuel=_fuel_breakdown(result),
    )


@app.get("/v1/fuel/compare", response_model=FuelComparisonResponse)
def compare_fuel(
    origin: str = Query(..., min_length=3, max_length=4, description="IATA or ICAO origin code"),
    destination: str = Query(..., min_length=3, max_length=4, description="IATA or ICAO destination code"),
    aircraft_a: str = Query(..., description="First aircraft code to compare"),
    aircraft_b: str = Query(..., description="Second aircraft code to compare"),
    routing_factor: float = Query(1.06, ge=1.0, le=1.2),
    contingency_pct: float = Query(0.05, ge=0.0, le=0.2),
    payload_kg: float | None = Query(None, ge=0.0),
) -> FuelComparisonResponse:
    origin_code = origin.strip().upper()
    destination_code = destination.strip().upper()
    code_a = aircraft_a.strip().upper()
    code_b = aircraft_b.strip().upper()

    if origin_code not in AIRPORTS:
        raise HTTPException(status_code=404, detail=f"Unknown origin airport: {origin_code}")
    if destination_code not in AIRPORTS:
        raise HTTPException(status_code=404, detail=f"Unknown destination airport: {destination_code}")
    if origin_code == destination_code:
        raise HTTPException(status_code=400, detail="Origin and destination must be different")
    if code_a not in AIRCRAFT_PROFILES:
        raise HTTPException(status_code=404, detail=f"Unknown aircraft: {code_a}")
    if code_b not in AIRCRAFT_PROFILES:
        raise HTTPException(status_code=404, detail=f"Unknown aircraft: {code_b}")

    origin_airport = AIRPORTS[origin_code]
    destination_airport = AIRPORTS[destination_code]
    effective_payload_kg = payload_kg if payload_kg is not None else DEFAULT_PAYLOAD_KG

    result_a = estimate_fuel(
        origin=origin_airport,
        destination=destination_airport,
        aircraft=AIRCRAFT_PROFILES[code_a],
        routing_factor=routing_factor,
        contingency_pct=contingency_pct,
        payload_kg=effective_payload_kg,
    )
    result_b = estimate_fuel(
        origin=origin_airport,
        destination=destination_airport,
        aircraft=AIRCRAFT_PROFILES[code_b],
        routing_factor=routing_factor,
        contingency_pct=contingency_pct,
        payload_kg=effective_payload_kg,
    )

    def _delta_tons(kg: float) -> float:
        return round(kg / 1000.0, 3)

    delta_taxi_kg = round(result_b["taxi_kg"] - result_a["taxi_kg"], 1)
    delta_trip_kg = round(result_b["trip_kg"] - result_a["trip_kg"], 1)
    delta_contingency_kg = round(result_b["contingency_kg"] - result_a["contingency_kg"], 1)
    delta_reserve_kg = round(result_b["reserve_kg"] - result_a["reserve_kg"], 1)
    delta_total_kg = round(result_b["total_kg"] - result_a["total_kg"], 1)
    total_pct = round((delta_total_kg / result_a["total_kg"]) * 100.0, 2) if result_a["total_kg"] != 0 else 0.0

    return FuelComparisonResponse(
        origin=origin_code,
        destination=destination_code,
        assumptions={
            "routing_factor": routing_factor,
            "contingency_pct": contingency_pct,
            "payload_kg": effective_payload_kg,
        },
        aircraft_a=_comparison_item(code_a, result_a),
        aircraft_b=_comparison_item(code_b, result_b),
        delta=FuelComparisonDelta(
            taxi_kg=delta_taxi_kg,
            taxi_tons=_delta_tons(delta_taxi_kg),
            trip_kg=delta_trip_kg,
            trip_tons=_delta_tons(delta_trip_kg),
            contingency_kg=delta_contingency_kg,
            contingency_tons=_delta_tons(delta_contingency_kg),
            reserve_kg=delta_reserve_kg,
            reserve_tons=_delta_tons(delta_reserve_kg),
            total_kg=delta_total_kg,
            total_tons=_delta_tons(delta_total_kg),
            total_pct=total_pct,
        ),
    )
