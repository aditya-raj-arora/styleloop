"""Outfit routes.

owner: ML/Engine

The daily suggestion comes from the novelty-optimizing rotation engine
(services/rotation.py). Feedback records swipe actions; wear marks garments worn.
Stubbed for Sprint 1.
"""

from fastapi import APIRouter, status

router = APIRouter(prefix="/outfits", tags=["outfits"])


@router.get("/daily")
def daily() -> None:
    # TODO(ML/Engine): return today's suggestion, generating it if absent.
    raise NotImplementedError


@router.post("/generate", status_code=status.HTTP_201_CREATED)
def generate() -> None:
    # TODO(ML/Engine): run rotation.generate_outfits(...) over 'clean' garments,
    #   persist scored Outfit rows for generated_for = today.
    raise NotImplementedError


@router.post("/{outfit_id}/feedback", status_code=status.HTTP_201_CREATED)
def feedback(outfit_id: int) -> None:
    # TODO(ML/Engine): record a FeedbackEvent (like/dislike/skip) for taste weighting.
    raise NotImplementedError


@router.post("/{outfit_id}/wear")
def wear(outfit_id: int) -> None:
    # TODO(ML/Engine): mark each garment worn (state, wear_count, last_worn_at).
    raise NotImplementedError
