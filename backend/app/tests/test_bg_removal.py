"""Background removal: DeepAI fallback (rembg isn't installed in CI, so the
local path always fails over to this — which is itself a useful regression
check that the fallback triggers correctly)."""

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
