"""Weather normalization + short-TTL caching. No network — httpx is mocked."""

from unittest.mock import MagicMock, patch

from app.services import weather


def _fake_owm_response(main: str, temp: float = 18.5) -> MagicMock:
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "main": {"temp": temp},
        "weather": [{"main": main}],
    }
    return response


def setup_function() -> None:
    # Each test starts with a clean cache — otherwise test order/timing would
    # leak between them (they all use the same (lat, lon) key).
    weather._cache.clear()


def test_get_weather_normalizes_clear_conditions() -> None:
    with patch("httpx.get", return_value=_fake_owm_response("Clear", temp=22.0)):
        result = weather.get_weather(12.9716, 77.5946)

    assert result == {"temp_c": 22.0, "condition": "Clear", "rain": False}


def test_get_weather_flags_rain_conditions() -> None:
    for condition in ["Rain", "Drizzle", "Thunderstorm", "Snow"]:
        weather._cache.clear()
        with patch("httpx.get", return_value=_fake_owm_response(condition)):
            result = weather.get_weather(12.9716, 77.5946)
        assert result["rain"] is True, f"{condition} should be flagged as rain"


def test_get_weather_caches_within_ttl() -> None:
    with patch("httpx.get", return_value=_fake_owm_response("Clear")) as mock_get:
        weather.get_weather(12.9716, 77.5946)
        weather.get_weather(12.9716, 77.5946)  # same coords, should hit the cache

    assert mock_get.call_count == 1


def test_get_weather_refetches_after_ttl_expires() -> None:
    with patch("httpx.get", return_value=_fake_owm_response("Clear")) as mock_get:
        weather.get_weather(12.9716, 77.5946)
        with patch("time.monotonic", return_value=time_far_future()):
            weather.get_weather(12.9716, 77.5946)

    assert mock_get.call_count == 2


def time_far_future() -> float:
    import time

    return time.monotonic() + weather._CACHE_TTL_SECONDS + 1
