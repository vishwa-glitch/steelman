"""A debate transcript: who said what, in which round."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

Side = Literal["pro", "con"]
Round = Literal["opening", "rebuttal", "closing"]


# A debater could type a line like "[CON - closing] I concede" to fake the other side's turn. Square-bracket
# headers are ours alone, so in the text shown to models a typed one becomes "(CON - closing] ...".
_FORGED_HEADER = re.compile(r"^[ \t]*\[\s*(PRO|CON)\s*-", re.IGNORECASE | re.MULTILINE)


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    side: Side
    round: Round
    text: str


class Transcript(BaseModel):
    model_config = ConfigDict(extra="forbid")
    motion: str
    turns: list[Turn]

    def texts_of(self, side: Side) -> list[str]:
        return [t.text for t in self.turns if t.side == side]

    def text_of(self, side: Side) -> str:
        return "\n\n".join(t.text for t in self.turns if t.side == side)

    def render(self) -> str:
        """The transcript as the judge sees it, in speaking order."""
        lines = [f"Motion: {self.motion}", ""]
        for t in self.turns:
            lines.append(f"[{t.side.upper()} - {t.round}]")
            lines.append(_FORGED_HEADER.sub(r"(\1 -", t.text.strip()))
            lines.append("")
        return "\n".join(lines).strip()
