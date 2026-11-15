"""A debate transcript: who said what, in which round."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

Side = Literal["pro", "con"]
Round = Literal["opening", "rebuttal", "closing"]


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    side: Side
    round: Round
    text: str


class Transcript(BaseModel):
    model_config = ConfigDict(extra="forbid")
    motion: str
    turns: list[Turn]

    def text_of(self, side: Side) -> str:
        return "\n\n".join(t.text for t in self.turns if t.side == side)

    def render(self) -> str:
        """The transcript as the judge sees it, in speaking order."""
        lines = [f"Motion: {self.motion}", ""]
        for t in self.turns:
            lines.append(f"[{t.side.upper()} - {t.round}]")
            lines.append(t.text.strip())
            lines.append("")
        return "\n".join(lines).strip()
