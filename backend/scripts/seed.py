"""Seed script — demo user + varied garments for local dev.

Run from backend/ with the venv active, and DATABASE_URL / STORAGE_* pointed
at a real (migrated) Postgres + bucket (docker-compose's MinIO profile works
fine — see the README):

    python scripts/seed.py

Idempotent-ish: re-running reuses the demo user if it already exists, and
always adds a fresh batch of garments (harmless duplication for a dev seed —
delete the demo user's garments yourself for a clean slate).

Skips the async bg-removal/tagging worker entirely: this generates its own
placeholder cutouts and assigns tags directly, since the point is a varied
wardrobe to develop the rotation engine against (Sprint 2), not to exercise
the upload pipeline (Dev B/Sprint 1 already covers that end-to-end).
"""

from __future__ import annotations

import io
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Run directly as `python scripts/seed.py` — make the backend/ package root
# (this script's parent directory) importable. Python only auto-adds the
# script's own directory (scripts/) to sys.path, not its parent.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models.garment import Garment  # noqa: E402
from app.models.user import User  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services import storage  # noqa: E402

DEMO_EMAIL = "demo@styleloop.dev"
DEMO_PASSWORD = "demo1234"

# (category, colors, pattern, fabric, season, formality, wear_count, days_since_worn)
# A deliberately varied spread — different categories/seasons/formality/wear
# history — so the Sprint 2 rotation engine has something non-trivial to
# rotate over from the first run.
_GARMENTS: list[tuple[str, list[str], str, str, str, str, int, int | None]] = [
    ("top", ["white"], "solid", "cotton", "all_season", "casual", 2, 3),
    ("top", ["black"], "solid", "cotton", "all_season", "casual", 8, 1),
    ("top", ["blue", "white"], "striped", "cotton", "summer", "casual", 0, None),
    ("bottom", ["blue"], "solid", "denim", "all_season", "casual", 5, 10),
    ("bottom", ["black"], "solid", "polyester", "all_season", "smart_casual", 1, None),
    ("dress", ["red"], "solid", "silk", "summer", "formal", 0, None),
    ("outerwear", ["gray"], "solid", "wool", "winter", "casual", 3, 20),
    ("outerwear", ["navy"], "solid", "polyester", "fall", "smart_casual", 0, None),
    ("shoes", ["white"], "solid", "leather", "all_season", "casual", 6, 2),
    ("shoes", ["black"], "solid", "leather", "all_season", "formal", 1, None),
]

_COLOR_RGB: dict[str, tuple[int, int, int]] = {
    "white": (245, 245, 245),
    "black": (20, 20, 20),
    "blue": (33, 80, 180),
    "red": (200, 30, 30),
    "gray": (128, 128, 128),
    "navy": (20, 30, 80),
}


def _placeholder_png(rgb: tuple[int, int, int]) -> bytes:
    """A solid-color square standing in for a real bg-removed cutout."""
    image = Image.new("RGBA", (400, 400), (*rgb, 255))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def get_or_create_demo_user(db) -> User:
    user = db.query(User).filter(User.email == DEMO_EMAIL).first()
    if user:
        print(f"Reusing existing demo user #{user.id} ({DEMO_EMAIL})")
        return user

    user = User(email=DEMO_EMAIL, hashed_password=hash_password(DEMO_PASSWORD))
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"Created demo user #{user.id} ({DEMO_EMAIL} / {DEMO_PASSWORD})")
    return user


def seed_garments(db, user: User) -> None:
    now = datetime.now(timezone.utc)

    for spec in _GARMENTS:
        category, colors, pattern, fabric, season, formality, wear_count, days_since_worn = spec
        rgb = _COLOR_RGB.get(colors[0], (150, 150, 150))
        image_bytes = _placeholder_png(rgb)

        key = f"garments/{user.id}/seed-{category}-{colors[0]}-{pattern}.png"
        storage.upload_bytes(key, image_bytes, "image/png")

        last_worn_at = (
            now - timedelta(days=days_since_worn) if days_since_worn is not None else None
        )

        garment = Garment(
            user_id=user.id,
            image_url=key,
            processed_url=key,  # skip real bg-removal for seed data
            category=category,
            colors=colors,
            pattern=pattern,
            fabric=fabric,
            fabric_confidence=0.9,
            season=season,
            formality=formality,
            state="clean",
            wear_count=wear_count,
            last_worn_at=last_worn_at,
        )
        db.add(garment)

    db.commit()
    print(f"Seeded {len(_GARMENTS)} garments for user #{user.id}")


def main() -> None:
    db = SessionLocal()
    try:
        user = get_or_create_demo_user(db)
        seed_garments(db, user)
    finally:
        db.close()


if __name__ == "__main__":
    main()
