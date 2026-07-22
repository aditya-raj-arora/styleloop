"""Virtual try-on service (later release).

Algorithm:
    - Render an outfit onto the user's base photo via the FASHN API through fal.ai.
    - On-demand only, and cached by (photo_version, garment_id) so repeat views are
      free and instant.
    - Enforce a per-user daily cap on renders (cost control); when the cap is hit or
      the API errors, fall back gracefully to the flat (non-rendered) outfit view.

Runs in the RQ worker (see workers/tasks.generate_tryon). Never blocks a request.
"""


def render_tryon(user_id: int, garment_id: int, photo_version: str) -> str:
    # TODO(ML): FASHN via fal.ai; cache by (photo_version+garment_id); daily cap; fallback.
    raise NotImplementedError
