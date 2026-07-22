"""Garment routes.

owner: Backend + ML

Upload returns immediately; the RQ worker performs bg-removal + tagging async, so
the frontend shows a placeholder until `processed_url` is populated. Responses use
the frozen `GarmentOut` contract. Stubbed for Sprint 1.
"""

from fastapi import APIRouter, status

router = APIRouter(prefix="/garments", tags=["garments"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def create_garment() -> None:
    # TODO(Backend): store upload to private bucket, create Garment row,
    #   enqueue workers.tasks.process_garment(id), return GarmentOut immediately.
    raise NotImplementedError


@router.get("")
def list_garments() -> None:
    # TODO(Backend): return the authenticated user's garments as list[GarmentOut].
    raise NotImplementedError


@router.get("/{garment_id}")
def get_garment(garment_id: int) -> None:
    # TODO(Backend): return a single GarmentOut (404 if not owned by user).
    raise NotImplementedError


@router.patch("/{garment_id}/tags")
def update_tags(garment_id: int) -> None:
    # TODO(Backend + ML): apply TagUpdate corrections, return updated GarmentOut.
    raise NotImplementedError


@router.post("/{garment_id}/state")
def set_state(garment_id: int) -> None:
    # TODO(Backend): transition laundry state (clean/worn/laundry); update
    #   wear_count + last_worn_at when marked worn.
    raise NotImplementedError
