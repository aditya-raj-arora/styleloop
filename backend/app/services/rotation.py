"""Rotation engine — THE DIFFERENTIATOR.

Generates fresh, non-repeating, weather-aware daily outfit suggestions by scoring
candidate garment combinations and optimizing for novelty.

Score for a candidate outfit:

    score = validity
          + recency_penalty      # penalize recently/frequently worn items -> novelty
          + fairness             # boost under-worn items so the whole wardrobe rotates
          + taste_weight         # nudge toward items the user has liked (FeedbackEvent)

Constraints:
    - Only 'clean' garments are eligible (respect laundry state).
    - Weather-aware: filter/weight by season + formality against today's weather
      (see services/weather.py).
    - Deterministic per day: seed the sampler with (user_id, generated_for) so a
      given day yields a stable suggestion, while different days differ.

Returns scored Outfit candidates for persistence by the outfits router.
"""


def generate_outfits(user_id: int, day, weather: dict, limit: int = 3) -> list:
    # TODO(ML/Engine): implement the scored, seeded, novelty-optimizing rotation.
    raise NotImplementedError
