"""Background removal: DeepAI fallback (rembg isn't installed in CI, so the
local path always fails over to this — which is itself a useful regression
check that the fallback triggers correctly)."""

import sys
import types
from unittest.mock import MagicMock, patch

from app.services import bg_removal


def test_remove_background_falls_back_to_deepai_without_rembg(monkeypatch) -> None:
    monkeypatch.setattr(bg_removal.settings, "DEEPAI_API_KEY", "test-key")

    post_response = MagicMock()
    post_response.json.return_value = {"output_url": "https://deepai.example/out.png"}
    post_response.raise_for_status.return_value = None

    get_response = MagicMock()
    get_response.content = b"cutout-bytes"
    get_response.raise_for_status.return_value = None

    with (
        patch("httpx.post", return_value=post_response) as mock_post,
        patch("httpx.get", return_value=get_response) as mock_get,
    ):
        result = bg_removal.remove_background(b"raw-image-bytes")

    assert result == b"cutout-bytes"
    assert mock_post.call_args.kwargs["headers"] == {"api-key": "test-key"}
    assert mock_get.call_args.args[0] == "https://deepai.example/out.png"


def test_remove_background_via_api_raises_without_key(monkeypatch) -> None:
    monkeypatch.setattr(bg_removal.settings, "DEEPAI_API_KEY", "")

    try:
        bg_removal._remove_background_via_api(b"raw")
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "DEEPAI_API_KEY" in str(exc)


def test_remove_background_via_api_raises_when_output_url_missing(monkeypatch) -> None:
    monkeypatch.setattr(bg_removal.settings, "DEEPAI_API_KEY", "test-key")

    post_response = MagicMock()
    post_response.json.return_value = {}
    post_response.raise_for_status.return_value = None

    with patch("httpx.post", return_value=post_response):
        try:
            bg_removal._remove_background_via_api(b"raw")
            raise AssertionError("expected RuntimeError")
        except RuntimeError as exc:
            assert "output_url" in str(exc)


def test_remove_background_local_pins_lightweight_u2netp_session() -> None:
    # rembg isn't a real dependency here (it's optional/lazy-imported) — fake
    # the module via sys.modules so this test doesn't need it installed.
    new_session_calls: list[str] = []
    remove_calls: list[tuple] = []
    fake_session = object()

    def fake_new_session(name):
        new_session_calls.append(name)
        return fake_session

    def fake_remove(data, session=None):
        remove_calls.append((data, session))
        return b"cutout-bytes"

    fake_rembg = types.ModuleType("rembg")
    fake_rembg.new_session = fake_new_session
    fake_rembg.remove = fake_remove

    bg_removal._rembg_session = None  # ensure a clean cache for this test
    try:
        with patch.dict(sys.modules, {"rembg": fake_rembg}):
            result = bg_removal._remove_background_local(b"raw-image-bytes")
            # A second call must reuse the cached session, not reload it.
            bg_removal._remove_background_local(b"more-raw-bytes")
    finally:
        bg_removal._rembg_session = None  # don't leak state into other tests

    assert result == b"cutout-bytes"
    assert new_session_calls == ["u2netp"]  # loaded once, reused on the 2nd call
    assert remove_calls == [
        (b"raw-image-bytes", fake_session),
        (b"more-raw-bytes", fake_session),
    ]
