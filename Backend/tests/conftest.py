import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.transcript import TranscriptEntry  # noqa: E402


@pytest.fixture
def sample_entries() -> list[TranscriptEntry]:
    """
    A synthetic transcript covering three distinct topics at known times,
    used to check that chunk timestamps stay faithful to the source and
    that retrieval finds the right topic at the right time.
    """
    script = [
        (0.0, 4.0, "Welcome to this tutorial on baking sourdough bread at home."),
        (4.0, 5.0, "Today we will cover starters, kneading, and proofing."),
        (9.0, 5.0, "First, let's talk about the sourdough starter and how to feed it daily."),
        (14.0, 6.0, "A healthy starter should double in size within four to six hours after feeding."),
        (20.0, 5.0, "Now let's move on to kneading the dough properly."),
        (25.0, 6.0, "Kneading develops the gluten network, which gives the bread its structure."),
        (31.0, 5.0, "You should knead for about ten minutes until the dough is smooth."),
        (36.0, 6.0, "Finally, we will discuss proofing times and temperatures for the best rise."),
        (42.0, 6.0, "Proof the dough at room temperature for four hours, or overnight in the fridge."),
        (48.0, 5.0, "That's it for today, thanks for watching this bread tutorial."),
    ]
    return [TranscriptEntry(text=t, start=s, duration=d) for s, d, t in script]
