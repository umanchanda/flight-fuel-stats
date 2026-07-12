from pydantic import BaseModel, Field


class FuelBreakdown(BaseModel):
    taxi_tons: float
    trip_tons: float
    contingency_tons: float
    reserve_tons: float
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
