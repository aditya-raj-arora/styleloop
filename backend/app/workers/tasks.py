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


def generate_tryon(user_id: int, outfit_id: int) -> None:
    """Render + cache a try-on for one outfit.

    The daily cap is enforced by the API *before* this is enqueued (see
    routers/outfits.py) — this task's own job is idempotency and graceful
    failure: if a cached render already exists for this exact
    (user_id, outfit_id, photo_version), a retried/duplicate job no-ops
    rather than spending another FASHN call; if rendering fails for any
    reason, it logs and returns without writing a row, so the API's polling
    endpoint just keeps reporting "pending" and the frontend falls back to
    the flat outfit view — never crashes the worker.
    """
    from app.database import SessionLocal
    from app.models.garment import Garment
    from app.models.outfit import Outfit
    from app.models.tryon import TryonRender
    from app.models.user import User
    from app.services import storage, tryon

    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        outfit = db.get(Outfit, outfit_id)
        if user is None or outfit is None or outfit.user_id != user_id:
            logger.warning(
                "generate_tryon: user %s / outfit %s not found or mismatched", user_id, outfit_id
            )
            return
        if user.base_photo_url is None:
            logger.warning("generate_tryon: user %s has no base photo set", user_id)
            return

        already_cached = (
            db.query(TryonRender)
            .filter(
                TryonRender.user_id == user_id,
                TryonRender.outfit_id == outfit_id,
                TryonRender.photo_version == user.base_photo_version,
            )
            .first()
        )
        if already_cached is not None:
            return

        garments = (
            db.query(Garment)
            .filter(Garment.id.in_(outfit.garment_ids), Garment.user_id == user_id)
            .all()
        )
        # Render order: a dress (there's ever only one) before a top before
        # a bottom — matches the "base combination" shape rotation.py builds
        # candidates from. Untagged garments can't be placed, same as the
        # rotation engine's own rule.
        _render_order = {"dress": 0, "top": 1, "bottom": 2}
        ordered = sorted(
            (g for g in garments if g.category is not None),
            key=lambda g: _render_order.get(g.category, 9),
        )
        tryon_garments = [
            tryon.TryonGarment(
                image_url=storage.presigned_download_url(g.processed_url or g.image_url),
                category=g.category,
            )
            for g in ordered
        ]
        base_photo_url = storage.presigned_download_url(user.base_photo_url)

        try:
            rendered_bytes = tryon.render_tryon(base_photo_url, tryon_garments)
        except tryon.TryonError:
            logger.warning("generate_tryon: render failed for outfit %s", outfit_id, exc_info=True)
            return

        key = f"tryon/{user_id}/{outfit_id}-v{user.base_photo_version}.png"
        storage.upload_bytes(key, rendered_bytes, "image/png")

        db.add(
            TryonRender(
                user_id=user_id,
                outfit_id=outfit_id,
                photo_version=user.base_photo_version,
                rendered_url=key,
            )
        )
        db.commit()
    finally:
        db.close()
