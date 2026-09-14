"""Weather normalization + short-TTL caching + graceful degradation. No
network — httpx is mocked throughout."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.config import settings
from app.services import weather


def _fake_owm_response(main: str, temp: float = 18.5) -> MagicMock:
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "main": {"temp": temp},
        "weather": [{"main": main}],
    }
    return response


@pytest.fixture(autouse=True)
def _fake_api_key(monkeypatch):
    # Most of this file is about a *configured* key succeeding/failing;
    # the "no key at all" behavior gets its own explicit test below.
    monkeypatch.setattr(settings, "OPENWEATHER_API_KEY", "fake-key")


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


# --- Graceful degradation --------------------------------------------------


def test_get_weather_returns_unknown_without_an_api_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "OPENWEATHER_API_KEY", "")
    with patch("httpx.get") as mock_get:
        result = weather.get_weather(12.9716, 77.5946)

    mock_get.assert_not_called()  # never even tries the API with no key
    assert result["temp_c"] is None


def test_get_weather_degrades_gracefully_on_a_network_error() -> None:
    with patch("httpx.get", side_effect=httpx.ConnectError("boom")):
        result = weather.get_weather(12.9716, 77.5946)

    assert result["temp_c"] is None


def test_get_weather_degrades_gracefully_on_an_http_error_status() -> None:
    response = MagicMock()
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401", request=MagicMock(), response=response
    )
    with patch("httpx.get", return_value=response):
        result = weather.get_weather(12.9716, 77.5946)

    assert result["temp_c"] is None


def test_get_weather_degrades_gracefully_on_an_unexpected_response_shape() -> None:
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"unexpected": "shape"}  # missing "weather"/"main"
    with patch("httpx.get", return_value=response):
        result = weather.get_weather(12.9716, 77.5946)

    assert result["temp_c"] is None


def test_a_failed_lookup_is_not_cached() -> None:
    # A failure shouldn't poison the cache for the full TTL - the very next
    # call should retry rather than being stuck on "unknown" for 10 minutes.
    with patch("httpx.get", side_effect=httpx.ConnectError("boom")):
        weather.get_weather(12.9716, 77.5946)

    with patch("httpx.get", return_value=_fake_owm_response("Clear")) as mock_get:
        result = weather.get_weather(12.9716, 77.5946)

    mock_get.assert_called_once()
    assert result["condition"] == "Clear"
