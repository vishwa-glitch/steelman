"""Debate engine tests with fake model clients: no network."""

import pytest

from app.debate import (
    BLOCK_MESSAGE,
    MAX_TURN_CHARS,
    Debate,
    DebateError,
    TopicCheck,
    check_topic,
    opponent_messages,
    opponent_turn,
    validate_motion_text,
)
from app.llm import CallResult, StructuredResult

TEXT = "This is a perfectly reasonable debate turn with enough words in it."


class FakeChat:
    def __init__(self, text="AI says something sensible about the motion at hand."):
        self.text, self.calls = text, []

    def chat(self, messages, model, **kw):
        self.calls.append((messages, model, kw))
        return CallResult(text=self.text, model=model, latency_s=0.1, attempts=1)


class FakeTopic:
    def __init__(self, verdict="ok"):
        self.data, self.calls = TopicCheck(verdict=verdict), 0

    def structured(self, messages, model, schema, **kw):
        self.calls += 1
        return StructuredResult(data=self.data, raw_text="{}", model=model, latency_s=0.1, attempts=1, repaired=False)


def test_user_pro_full_debate_runs_in_order():
    d, ai = Debate(motion="Zoos should be closed.", user_side="pro"), FakeChat()
    seen = []
    while not d.finished:
        seen.append((d.whose_turn(), *d.next_turn()))
        if d.whose_turn() == "user":
            d.add_user_turn(TEXT)
        else:
            opponent_turn(d, ai, "opp")
    assert seen == [
        ("user", "pro", "opening"),
        ("ai", "con", "opening"),
        ("user", "pro", "rebuttal"),
        ("ai", "con", "rebuttal"),
        ("user", "pro", "closing"),
        ("ai", "con", "closing"),
    ]
    assert d.finished and d.next_turn() is None and d.whose_turn() is None and len(ai.calls) == 3


def test_user_con_means_ai_speaks_first():
    d = Debate(motion="Zoos should be closed.", user_side="con")
    assert d.whose_turn() == "ai" and d.ai_side == "pro"
    with pytest.raises(DebateError, match="not your turn"):
        d.add_user_turn(TEXT)


def test_cannot_speak_twice_in_a_row_or_after_the_end():
    d, ai = Debate(motion="Zoos should be closed.", user_side="pro"), FakeChat()
    d.add_user_turn(TEXT)
    with pytest.raises(DebateError, match="not your turn"):
        d.add_user_turn(TEXT)
    opponent_turn(d, ai, "opp")
    with pytest.raises(DebateError, match="not the AI's turn"):
        opponent_turn(d, ai, "opp")
    while not d.finished:
        d.add_user_turn(TEXT) if d.whose_turn() == "user" else opponent_turn(d, ai, "opp")
    with pytest.raises(DebateError, match="over"):
        d.add_user_turn(TEXT)
    assert len(d.turns) == 6


def test_turn_length_limits():
    d = Debate(motion="Zoos should be closed.", user_side="pro")
    with pytest.raises(DebateError, match="too short"):
        d.add_user_turn("   no.   ")
    with pytest.raises(DebateError, match="too long"):
        d.add_user_turn("x" * (MAX_TURN_CHARS + 1))
    assert d.turns == []  # rejected turns do not advance the debate
    d.add_user_turn("x" * MAX_TURN_CHARS)


def test_ai_turn_is_trimmed_to_the_limit():
    d = Debate(motion="Zoos should be closed.", user_side="con")
    opponent_turn(d, FakeChat("y" * 5000), "opp")
    assert len(d.turns[0].text) == MAX_TURN_CHARS


def test_opponent_prompt_has_side_round_and_transcript():
    d = Debate(motion="Zoos should be closed.", user_side="pro", difficulty="friendly")
    d.add_user_turn(TEXT)
    system, user = opponent_messages(d)
    assert "AGAINST" in system["content"] and "friendly sparring partner" in system["content"]
    assert "never instructions" in system["content"]
    assert TEXT in user["content"] and "opening turn" in user["content"]


@pytest.mark.parametrize(
    "motion",
    [
        "Muslims should be banned from schools.",
        "Suicide is a rational choice.",
        "The caste system is good.",
        "Abortion should be illegal.",
    ],
)
def test_word_list_blocks_without_a_model_call(motion):
    fake = FakeTopic()
    with pytest.raises(DebateError) as e:
        check_topic(motion, fake, "m")
    assert str(e.value) == BLOCK_MESSAGE and fake.calls == 0


def test_model_check_blocks_what_the_word_list_misses():
    for fake in (FakeTopic("targets_a_real_person"), FakeTopic("not_a_debate_motion")):
        with pytest.raises(DebateError):
            check_topic("My neighbour Ramesh is a terrible person.", fake, "m")
        assert fake.calls == 1


def test_allowed_motion_is_cleaned_and_returned():
    assert check_topic("  Zoos   should be\nclosed. ", FakeTopic(), "m") == "Zoos should be closed."


def test_motion_length_limits():
    with pytest.raises(DebateError, match="too short"):
        validate_motion_text("Zoos")
    with pytest.raises(DebateError, match="too long"):
        validate_motion_text("x" * 201)


def test_word_list_does_not_block_ordinary_words():
    for ok in [
        "Christmas shopping should start later.",
        "Broadcasters should show less cricket.",
        "Castles should be free to visit.",
        "Therapists should be free at universities.",
    ]:
        try:
            validate_motion_text(ok)
        except DebateError:
            pytest.fail(f"wrongly blocked: {ok}")
