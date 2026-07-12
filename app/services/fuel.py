from app.services.distance import routed_distance_nm


def estimate_fuel(
    origin: dict[str, float | str],
    destination: dict[str, float | str],
    aircraft: dict[str, float | str],
    routing_factor: float,
    contingency_pct: float,
    payload_kg: float | None,
) -> dict[str, float]:
    distance_nm = routed_distance_nm(
        float(origin["lat"]),
        float(origin["lon"]),
        float(destination["lat"]),
        float(destination["lon"]),
        routing_factor,
    )

    cruise_speed_kts = float(aircraft["cruise_speed_kts"])
    burn_kg_per_hour = float(aircraft["burn_kg_per_hour"])
    taxi_kg = float(aircraft["taxi_kg"])
    climb_descent_factor = float(aircraft["climb_descent_factor"])
    reserve_minutes = float(aircraft["reserve_minutes"])
    payload_factor = float(aircraft["payload_factor_per_1000kg"])

    payload_multiplier = 1.0
    if payload_kg is not None:
        payload_multiplier += (payload_kg / 1000.0) * payload_factor

    trip_time_hr = distance_nm / cruise_speed_kts
    trip_kg = trip_time_hr * burn_kg_per_hour * climb_descent_factor * payload_multiplier

    contingency_kg = trip_kg * contingency_pct
    reserve_kg = (reserve_minutes / 60.0) * burn_kg_per_hour
    total_kg = taxi_kg + trip_kg + contingency_kg + reserve_kg

    return {
        "distance_nm": round(distance_nm, 1),
        "block_time_min": round((trip_time_hr * 60.0) + 20.0, 1),
        "taxi_kg": round(taxi_kg, 1),
        "trip_kg": round(trip_kg, 1),
        "contingency_kg": round(contingency_kg, 1),
        "reserve_kg": round(reserve_kg, 1),
        "total_kg": round(total_kg, 1),
    }
