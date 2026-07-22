"""Weather service.

Algorithm:
    - Query OpenWeatherMap for the user's lat/lon (current + short forecast).
    - Normalize to a compact dict the rotation engine consumes:
        {"temp_c": float, "condition": str, "rain": bool}
    - Cache per (lat, lon) for a short TTL to avoid hammering the API.
"""


def get_weather(lat: float, lon: float) -> dict:
    # TODO(Backend): OpenWeatherMap lat/lon -> {temp_c, condition, rain}.
    raise NotImplementedError
