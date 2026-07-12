from pydantic import BaseModel, Field


class FuelEstimateRequest(BaseModel):
    origin: str = Field(..., min_length=3, max_length=4, description="IATA or ICAO origin code")
    destination: str = Field(..., min_length=3, max_length=4, description="IATA or ICAO destination code")
    aircraft_type: str = Field(..., min_length=1, description="Supported aircraft model code")
    payload_kg: float | None = Field(default=None, ge=0)
    routing_factor: float = Field(default=1.06, ge=1.0, le=1.2)
    contingency_pct: float = Field(default=0.05, ge=0.0, le=0.2)


class FuelBreakdown(BaseModel):
    taxi_kg: float
    trip_kg: float
    contingency_kg: float
    reserve_kg: float
    total_kg: float


class FuelEstimateResponse(BaseModel):
    origin: str
    destination: str
    aircraft_type: str
    distance_nm: float
    block_time_min: float
    fuel_kg: FuelBreakdown
    assumptions: dict[str, float | str]
    confidence: str


class AircraftListResponse(BaseModel):
    aircraft: list[dict[str, float | str]]


class AirportSearchResponse(BaseModel):
    airports: list[dict[str, float | str]]
