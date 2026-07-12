from fastapi import FastAPI, HTTPException, Query

from app.data.aircraft import AIRCRAFT_PROFILES
from app.data.airports import AIRPORTS
from app.models import (
    AircraftListResponse,
    AirportSearchResponse,
    FuelBreakdown,
    FuelEstimateRequest,
    FuelEstimateResponse,
    RouteFuelEstimateItem,
    RouteFuelEstimatesResponse,
)
from app.services.fuel import estimate_fuel

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


@app.post("/v1/fuel/estimate", response_model=FuelEstimateResponse)
def fuel_estimate(payload: FuelEstimateRequest) -> FuelEstimateResponse:
    origin_code = payload.origin.strip().upper()
    destination_code = payload.destination.strip().upper()
    aircraft_code = payload.aircraft_type.strip().upper()

    if origin_code not in AIRPORTS:
        raise HTTPException(status_code=404, detail=f"Unknown origin airport: {origin_code}")
    if destination_code not in AIRPORTS:
        raise HTTPException(status_code=404, detail=f"Unknown destination airport: {destination_code}")
    if aircraft_code not in AIRCRAFT_PROFILES:
        raise HTTPException(status_code=404, detail=f"Unsupported aircraft type: {aircraft_code}")
    if origin_code == destination_code:
        raise HTTPException(status_code=400, detail="Origin and destination must be different")

    origin = AIRPORTS[origin_code]
    destination = AIRPORTS[destination_code]
    aircraft = AIRCRAFT_PROFILES[aircraft_code]

    result = estimate_fuel(
        origin=origin,
        destination=destination,
        aircraft=aircraft,
        routing_factor=payload.routing_factor,
        contingency_pct=payload.contingency_pct,
        payload_kg=payload.payload_kg,
    )

    confidence = "medium"
    if payload.payload_kg is not None:
        confidence = "medium-high"

    return FuelEstimateResponse(
        origin=origin_code,
        destination=destination_code,
        aircraft_type=aircraft_code,
        distance_nm=result["distance_nm"],
        block_time_min=result["block_time_min"],
        fuel_kg=FuelBreakdown(
            taxi_kg=result["taxi_kg"],
            trip_kg=result["trip_kg"],
            contingency_kg=result["contingency_kg"],
            reserve_kg=result["reserve_kg"],
            total_kg=result["total_kg"],
        ),
        assumptions={
            "routing_factor": payload.routing_factor,
            "contingency_pct": payload.contingency_pct,
            "reserve_minutes": float(aircraft["reserve_minutes"]),
            "taxi_fuel_kg": float(aircraft["taxi_kg"]),
        },
        confidence=confidence,
    )


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

    estimates: list[RouteFuelEstimateItem] = []
    for aircraft_code, aircraft in AIRCRAFT_PROFILES.items():
        result = estimate_fuel(
            origin=origin_airport,
            destination=destination_airport,
            aircraft=aircraft,
            routing_factor=routing_factor,
            contingency_pct=contingency_pct,
            payload_kg=payload_kg,
        )
        estimates.append(
            RouteFuelEstimateItem(
                aircraft_type=aircraft_code,
                aircraft_name=str(aircraft["name"]),
                distance_nm=result["distance_nm"],
                block_time_min=result["block_time_min"],
                fuel_kg=FuelBreakdown(
                    taxi_kg=result["taxi_kg"],
                    trip_kg=result["trip_kg"],
                    contingency_kg=result["contingency_kg"],
                    reserve_kg=result["reserve_kg"],
                    total_kg=result["total_kg"],
                ),
            )
        )

    estimates.sort(key=lambda item: item.fuel_kg.total_kg)

    return RouteFuelEstimatesResponse(
        origin=origin_code,
        destination=destination_code,
        assumptions={
            "routing_factor": routing_factor,
            "contingency_pct": contingency_pct,
            "payload_kg": payload_kg or 0.0,
        },
        estimates=estimates,
    )
