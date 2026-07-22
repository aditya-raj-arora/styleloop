"""RQ worker tasks.

All slow work (background removal, tagging, try-on rendering) runs here, enqueued
onto Redis by the API — never inline in a request. Run a worker with:

    rq worker --url $REDIS_URL styleloop

Service modules are imported lazily inside each task (once implemented) so this
module stays importable even if a heavy ML dependency is missing at enqueue time.
"""


def process_garment(garment_id: int) -> None:
    """bg-removal -> tagging -> persist processed_url + tags for a garment.

    Steps (TODO Backend + ML):
        1. Load the garment + its raw image from the private bucket.
        2. cutout = services.bg_removal.remove_background(image_bytes)
        3. tags = services.tagging.tag_garment(cutout)
        4. Upload cutout, set processed_url + tags, commit.
    Photos are never logged or placed in URLs.
    """
    raise NotImplementedError


def generate_tryon(user_id: int, garment_id: int, photo_version: str) -> None:
    """Render + cache a try-on for one garment (respects daily cap; graceful fallback).

    Delegates to services.tryon.render_tryon and stores the cached result keyed by
    (photo_version, garment_id).
    """
    raise NotImplementedError
