"""Every ready-made topic on the site must pass the free checks (length, word list), so "Surprise me"
never offers a topic the backend would refuse."""

import json
from pathlib import Path

from app.debate import validate_motion_text

BANK = Path(__file__).resolve().parents[2] / "frontend/src/data/topics.json"


def test_every_ready_made_topic_passes_the_free_checks():
    topics = [t for group in json.loads(BANK.read_text()).values() for t in group]
    assert len(topics) >= 50 and len(set(topics)) == len(topics)
    for t in topics:
        assert validate_motion_text(t) == t
