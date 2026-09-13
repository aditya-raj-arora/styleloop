"""RQ worker tasks.

All slow work (background removal, tagging, try-on rendering) runs here, enqueued
onto Redis by the API — never inline in a request. Run a worker with:

    python -m app.workers.run

Service modules are imported lazily inside each task so this module stays
importable even if a heavy ML dependency (e.g. rembg) is missing.
"""

import logging

logger = logging.getLogger(__name__)


def process_garment(garment_id: int) -> None:
    """bg-removal -> tagging -> persist processed_url + tags for a garment.

    Idempotent and safe to retry: always re-downloads the raw image and
    overwrites the processed key + tags rather than assuming partial state
    from a prior attempt. Photos are never logged or placed in URLs — only
    storage *keys* (see services/storage.py) are persisted; the API generates
    short-lived signed URLs from those keys at read time.
    """
    from app.database import SessionLocal
    from app.models.garment import Garment
    from app.services import bg_removal, storage, tagging

    db = SessionLocal()
    try:
        garment = db.get(Garment, garment_id)
        if garment is None:
            logger.warning("process_garment: garment %s not found (deleted?)", garment_id)
            return

        raw_bytes = storage.download_bytes(garment.image_url)
        cutout = bg_removal.remove_background(raw_bytes)

        processed_key = f"garments/{garment.user_id}/{garment_id}-processed.png"
        storage.upload_bytes(processed_key, cutout, "image/png")

        tags = tagging.tag_garment(cutout)

        garment.processed_url = processed_key
        garment.category = tags["category"]
        garment.colors = tags["colors"]
        garment.pattern = tags["pattern"]
        garment.fabric = tags["fabric"]
        garment.fabric_confidence = tags["fabric_confidence"]
        garment.season = tags["season"]
        garment.formality = tags["formality"]
        db.commit()
    finally:
        db.close()


def generate_tryon(user_id: int, garment_id: int, photo_version: str) -> None:
    """Render + cache a try-on for one garment (respects daily cap; graceful fallback).

    Delegates to services.tryon.render_tryon and stores the cached result keyed by
    (photo_version, garment_id).
    """
    raise NotImplementedError
