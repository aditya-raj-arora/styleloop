"""Auto-tagging service.

Algorithm:
    - colors:   deterministic — quantize the cutout's pixels (e.g. k-means in LAB)
                and map to named palette entries. Fully reproducible, no model.
    - category / pattern:  CLIP zero-shot or a vision-LLM classifier over a fixed
                label set (e.g. top/bottom/dress/outerwear/shoes; solid/striped/…).
    - fabric:   best-effort, low confidence — return (label, confidence) and store
                None when confidence is below threshold so the UI can prompt the user.

Returns a dict matching the Garment tag columns. Runs in the RQ worker only.
"""


def tag_garment(image_bytes: bytes) -> dict:
    # TODO(ML): color=deterministic; category/pattern=CLIP/vision-LLM; fabric=low-conf/None.
    raise NotImplementedError
