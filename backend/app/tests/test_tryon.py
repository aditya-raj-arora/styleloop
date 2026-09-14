"""services.tryon.render_tryon — mocks every FASHN/fal.ai HTTP call (this is
a unit test of the sequencing/error-handling logic, not an integration test
of the real API). See services/tryon.py's module docstring for the algorithm.
"""

from __future__ import annotations

import httpx
import pytest

from app.services import tryon


class _FakeResponse:
    def __init__(self, json_data: dict | None = None, *, status_code: int = 200):
        self._json = json_data or {}
        self.status_code = status_code
        self.content = b"fake-rendered-image-bytes"

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)  # type: ignore[arg-type]

    def json(self) -> dict:
        return self._json


_TOP = tryon.TryonGarment("https://g/top.png", "top")
_BASE_PHOTO = "https://base/photo.png"


@pytest.fixture(autouse=True)
def _fake_api_key(monkeypatch):
    monkeypatch.setattr(tryon.settings, "FASHN_API_KEY", "test-key")


def test_render_tryon_requires_an_api_key(monkeypatch) -> None:
    monkeypatch.setattr(tryon.settings, "FASHN_API_KEY", "")
    with pytest.raises(tryon.TryonError):
        tryon.render_tryon(_BASE_PHOTO, [_TOP])


def test_render_tryon_raises_without_any_renderable_garment(monkeypatch) -> None:
    monkeypatch.setattr(tryon.httpx, "post", lambda *a, **k: pytest.fail("should not call FASHN"))
    garments = [tryon.TryonGarment("https://g/shoes.png", "shoes")]
    with pytest.raises(tryon.TryonError):
        tryon.render_tryon("https://base/photo.png", garments)


def test_render_tryon_chains_multiple_garments_and_skips_unsupported(monkeypatch) -> None:
    submitted: list[dict] = []
    result_urls: list[str] = []

    def fake_post(url, headers=None, json=None, timeout=None):
        submitted.append(json)
        return _FakeResponse({"request_id": f"req-{len(submitted)}"})

    def fake_get(url, headers=None, timeout=None):
        if url.endswith("/status"):
            return _FakeResponse({"status": "COMPLETED"})
        if "/requests/" in url:
            index = len(result_urls) + 1
            out_url = f"https://cdn.fake/out-{index}.png"
            result_urls.append(out_url)
            return _FakeResponse({"images": [{"url": out_url}]})
        return _FakeResponse()  # final image download

    monkeypatch.setattr(tryon.httpx, "post", fake_post)
    monkeypatch.setattr(tryon.httpx, "get", fake_get)

    garments = [
        tryon.TryonGarment("https://g/top.png", "top"),
        tryon.TryonGarment("https://g/bottom.png", "bottom"),
        tryon.TryonGarment("https://g/shoes.png", "shoes"),  # unsupported - skipped
    ]
    result = tryon.render_tryon("https://base/photo.png", garments)

    assert result == b"fake-rendered-image-bytes"
    # Only 2 FASHN calls - shoes never submitted.
    assert len(submitted) == 2
    assert submitted[0]["model_image"] == "https://base/photo.png"
    assert submitted[0]["garment_image"] == "https://g/top.png"
    assert submitted[0]["category"] == "tops"
    # Second call's "model" is the first call's *output* - the chaining.
    assert submitted[1]["model_image"] == result_urls[0]
    assert submitted[1]["garment_image"] == "https://g/bottom.png"
    assert submitted[1]["category"] == "bottoms"


def test_render_tryon_maps_dress_to_one_pieces(monkeypatch) -> None:
    submitted: list[dict] = []

    def fake_post(url, headers=None, json=None, timeout=None):
        submitted.append(json)
        return _FakeResponse({"request_id": "req-1"})

    def fake_get(url, headers=None, timeout=None):
        if url.endswith("/status"):
            return _FakeResponse({"status": "COMPLETED"})
        if "/requests/" in url:
            return _FakeResponse({"images": [{"url": "https://cdn.fake/out.png"}]})
        return _FakeResponse()

    monkeypatch.setattr(tryon.httpx, "post", fake_post)
    monkeypatch.setattr(tryon.httpx, "get", fake_get)

    dress = tryon.TryonGarment("https://g/dress.png", "dress")
    tryon.render_tryon(_BASE_PHOTO, [dress])
    assert submitted[0]["category"] == "one-pieces"


def test_render_tryon_wraps_http_errors(monkeypatch) -> None:
    def fake_post(url, headers=None, json=None, timeout=None):
        return _FakeResponse(status_code=500)

    monkeypatch.setattr(tryon.httpx, "post", fake_post)

    with pytest.raises(tryon.TryonError):
        tryon.render_tryon(_BASE_PHOTO, [_TOP])


def test_render_tryon_raises_on_unexpected_status(monkeypatch) -> None:
    def fake_post(url, headers=None, json=None, timeout=None):
        return _FakeResponse({"request_id": "req-1"})

    def fake_get(url, headers=None, timeout=None):
        return _FakeResponse({"status": "FAILED"})

    monkeypatch.setattr(tryon.httpx, "post", fake_post)
    monkeypatch.setattr(tryon.httpx, "get", fake_get)

    with pytest.raises(tryon.TryonError):
        tryon.render_tryon(_BASE_PHOTO, [_TOP])


def test_render_tryon_times_out_if_never_completed(monkeypatch) -> None:
    monkeypatch.setattr(tryon, "_POLL_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(tryon, "_POLL_INTERVAL_SECONDS", 0.01)

    def fake_post(url, headers=None, json=None, timeout=None):
        return _FakeResponse({"request_id": "req-1"})

    def fake_get(url, headers=None, timeout=None):
        return _FakeResponse({"status": "IN_PROGRESS"})

    monkeypatch.setattr(tryon.httpx, "post", fake_post)
    monkeypatch.setattr(tryon.httpx, "get", fake_get)

    with pytest.raises(tryon.TryonError):
        tryon.render_tryon(_BASE_PHOTO, [_TOP])
