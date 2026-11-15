"""How eval debates are built and changed.

Base debate: one model writes a whole debate in which one side is weakened on purpose, in a named way, while
both sides stay about the same length. The other side is then the known stronger side (the label).

Variants of a base debate test one bias each:
- swapped:         CON speaks first in every round. Same words. The winner should not change.
- padded_weak:     the weaker side's turns are made about twice as long, with nothing new. Should not help it.
- selfpref_strong / selfpref_weak: one side is reworded by the judge's own model family. If the judge prefers
                   its own family's writing, the reworded side gains. (Limitation: rewording can also change
                   quality, so read this alongside the margins, not as proof on its own.)
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.transcript import Round, Side, Transcript, Turn

ROUNDS: tuple[Round, ...] = ("opening", "rebuttal", "closing")
WEAKNESSES = {
    "no_evidence": "makes confident claims but never gives a specific fact, number, study or example",
    "fallacy": "rests its main argument on a logical fallacy (for example slippery slope, false dilemma, "
    "appeal to tradition or attacking the person), stated persuasively",
    "ignores_rebuttal": "never answers the other side's main point; in rebuttal and closing it only repeats "
    "its own points",
}
Weakness = Literal["no_evidence", "fallacy", "ignores_rebuttal"]


class EvalDebate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    motion: str
    weak_side: Side
    weakness: Weakness
    writer_model: str
    transcript: Transcript

    @property
    def label(self) -> Side:
        """The known stronger side."""
        return "con" if self.weak_side == "pro" else "pro"


class ThreeTurns(BaseModel):
    """Rewritten text for one side's three turns, in round order."""

    model_config = ConfigDict(extra="forbid")
    opening: str
    rebuttal: str
    closing: str


def check_shape(t: Transcript) -> list[str]:
    """Problems with a generated transcript: we need PRO then CON in each of the three rounds."""
    expected = [(side, rnd) for rnd in ROUNDS for side in ("pro", "con")]
    got = [(turn.side, turn.round) for turn in t.turns]
    problems = []
    if got != expected:
        problems.append(f"turn order {got} is not {expected}")
    if any(len(turn.text.split()) < 15 for turn in t.turns):
        problems.append("a turn is shorter than 15 words")
    return problems


def length_ratio(t: Transcript, weak_side: Side) -> float:
    """Weak side's word count divided by the strong side's. Near 1.0 means length can't give the answer away."""
    strong_side = "con" if weak_side == "pro" else "pro"
    return len(t.text_of(weak_side).split()) / max(1, len(t.text_of(strong_side).split()))


def swap_order(t: Transcript) -> Transcript:
    """CON first in every round; the words are unchanged."""
    turns = [
        turn for rnd in ROUNDS for side in ("con", "pro") for turn in t.turns if turn.round == rnd and turn.side == side
    ]
    return Transcript(motion=t.motion, turns=turns)


def replace_side(t: Transcript, side: Side, new: ThreeTurns) -> Transcript:
    texts = {"opening": new.opening, "rebuttal": new.rebuttal, "closing": new.closing}
    turns = [Turn(side=x.side, round=x.round, text=texts[x.round] if x.side == side else x.text) for x in t.turns]
    return Transcript(motion=t.motion, turns=turns)


def side_turns(t: Transcript, side: Side) -> str:
    return "\n\n".join(f"[{x.round}]\n{x.text}" for x in t.turns if x.side == side)


def writer_messages(motion: str, weak_side: Side, weakness: Weakness) -> list[dict[str, str]]:
    strong_side = "con" if weak_side == "pro" else "pro"
    return [
        {
            "role": "system",
            "content": "You write realistic debate transcripts for testing debate judges. Reply only with JSON.",
        },
        {
            "role": "user",
            "content": f"""Write a debate on the motion: "{motion}"

Six turns in this exact order: PRO opening, CON opening, PRO rebuttal, CON rebuttal, PRO closing, CON closing.
Each turn is 60 to 110 words.

The {strong_side.upper()} side is strong: specific evidence (real-sounding facts, studies or examples), clear logic,
and in rebuttal and closing it directly answers the other side's points.

The {weak_side.upper()} side is weaker in one way only: it {WEAKNESSES[weakness]}.
Apart from that it must sound fluent, confident and reasonable, not silly. Keep both sides about the same length.
Do not mention that a side is weaker. Use "pro" and "con" for side and "opening", "rebuttal", "closing" for round.""",
        },
    ]


def padding_messages(t: Transcript, side: Side) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": "You rewrite debate turns. Reply only with JSON."},
        {
            "role": "user",
            "content": f"""Motion: "{t.motion}". Below are the three turns of the {side.upper()} side.
Rewrite each turn to be about twice as long by restating and elaborating what is already there.
Add no new arguments, facts, numbers, studies or examples. Keep the same meaning and tone.

{side_turns(t, side)}""",
        },
    ]


def paraphrase_messages(t: Transcript, side: Side) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": "You reword text. Reply only with JSON."},
        {
            "role": "user",
            "content": f"""Motion: "{t.motion}". Below are the three turns of the {side.upper()} side.
Reword each turn in your own style. Keep exactly the same arguments, facts and examples, and about the same
length. Do not improve or weaken the arguments.

{side_turns(t, side)}""",
        },
    ]
