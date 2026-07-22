"""Background removal service.

Algorithm:
    1. Run local rembg (U2Net) to produce a transparent PNG cutout of the garment.
    2. If the local result is empty/low-quality (or rembg is unavailable), fall
       back to the remove.bg HTTP API.
    3. Upload the cutout to the private bucket and return its storage key. The
       caller (worker) generates signed URLs; raw bytes and photos are never logged.

Runs inside the RQ worker only — never in a request path.
"""


def remove_background(image_bytes: bytes) -> bytes:
    # TODO(ML): rembg (U2Net) local, remove.bg fallback.
    raise NotImplementedError
