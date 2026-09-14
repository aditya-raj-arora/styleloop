"""Weather service.

Algorithm:
    - Query OpenWeatherMap's Current Weather API for the user's lat/lon.
    - Normalize the response to a compact dict the rotation engine consumes:
        {"temp_c": float | None, "condition": str, "rain": bool}
    - Cache per (lat, lon), rounded to ~1km, for a short TTL — weather doesn't
      change meaningfully faster than that, and this keeps repeated dashboard
      loads from hammering the API.
    - Degrade gracefully rather than fail the request: no API key configured,
      a network error, or a bad/unexpected response all fall back to
      `_UNKNOWN_WEATHER` (`temp_c=None`) instead of raising.
      `rotation._validity` already treats `temp_c is None` as "no weather
      signal — don't penalize what we can't judge" (see rotation.py), so
      this is a real, already-handled degradation path, not a stub — a
      dashboard load shouldn't 500 just because OpenWeatherMap is down.
      Unlike a real lookup, a fallback result is never cached, so the very
      next call retries instead of being stuck on "unknown" for the full TTL.
"""

from __future__ import annotations

import logging
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_API_URL = "https://api.openweathermap.org/data/2.5/weather"
_CACHE_TTL_SECONDS = 600  # 10 minutes

# OpenWeatherMap's top-level condition groups that mean "bring an umbrella".
# See https://openweathermap.org/weather-conditions for the full list.
_RAIN_CONDITIONS = {"rain", "drizzle", "thunderstorm", "snow"}

_UNKNOWN_WEATHER: dict = {"temp_c": None, "condition": "unknown", "rain": False}

# Module-level cache: {(lat, lon) rounded to 2dp: (cached_at, result)}. Plain
# in-process dict rather than Redis — weather lookups are cheap to redo on a
# cold process, and this avoids a Redis round-trip on the common warm path.
_cache: dict[tuple[float, float], tuple[float, dict]] = {}


def get_weather(lat: float, lon: float) -> dict:
    """Return {"temp_c": float | None, "condition": str, "rain": bool} for
    (lat, lon). Never raises — see the module docstring's fallback rule."""
    key = (round(lat, 2), round(lon, 2))  # ~1km grid — plenty of granularity for outfit weather
    now = time.monotonic()

    cached = _cache.get(key)
    if cached is not None and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    if not settings.OPENWEATHER_API_KEY:
        return _UNKNOWN_WEATHER

    try:
        response = httpx.get(
            _API_URL,
            params={
                "lat": lat,
                "lon": lon,
                "appid": settings.OPENWEATHER_API_KEY,
                "units": "metric",
            },
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
        condition = data["weather"][0]["main"]
        result = {
            "temp_c": data["main"]["temp"],
            "condition": condition,
            "rain": condition.lower() in _RAIN_CONDITIONS,
        }
    except (httpx.HTTPError, KeyError, IndexError, ValueError):
        logger.warning(
            "OpenWeatherMap lookup failed for (%s, %s); scoring without a weather signal",
            lat,
            lon,
            exc_info=True,
        )
        return _UNKNOWN_WEATHER

    _cache[key] = (now, result)
    return result
