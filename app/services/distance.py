from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_NM = 3440.065


def great_circle_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_rad, lon1_rad = radians(lat1), radians(lon1)
    lat2_rad, lon2_rad = radians(lat2), radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return EARTH_RADIUS_NM * c


def routed_distance_nm(lat1: float, lon1: float, lat2: float, lon2: float, routing_factor: float) -> float:
    return great_circle_nm(lat1, lon1, lat2, lon2) * routing_factor
