"""Try-on API schema.

owner: ML/Engine
"""

from typing import Literal

from pydantic import BaseModel


class TryonOut(BaseModel):
    """Response for both `POST /outfits/{id}/tryon` (kicks off or returns a
    cached render) and `GET /outfits/{id}/tryon` (polls it). `rendered_url`
    is a presigned download URL, set only once `status` is "ready"."""

    status: Literal["pending", "ready"]
    rendered_url: str | None = None
