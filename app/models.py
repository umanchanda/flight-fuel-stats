from pydantic import BaseModel, Field


class FuelBreakdown(BaseModel):
    taxi_kg: float
    taxi_tons: float
    trip_kg: float
    trip_tons: float
    contingency_kg: float
    contingency_tons: float
    reserve_kg: float
    reserve_tons: float
    total_kg: float
    total_tons: float


class RouteFuelEstimateItem(BaseModel):
    aircraft_type: str
    aircraft_name: str
    distance_nm: float
    block_time_min: float
    fuel_tons: FuelBreakdown


class RouteFuelEstimatesResponse(BaseModel):
    origin: str
    destination: str
    assumptions: dict[str, float]
    estimates: list[RouteFuelEstimateItem]


class AircraftListResponse(BaseModel):
    aircraft: list[dict[str, float | str]]


class AirportSearchResponse(BaseModel):
    airports: list[dict[str, float | str]]
