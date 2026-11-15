"""A stand-in for the model client, for local development and browser tests: no network, no AI calls.

Used only when FAKE_LLM=1 is set. It allows every motion, streams a canned reply word by word, and returns a
scorecard whose quotes are copied from the transcript (so the quote check and highlighting are exercised).
"""

import re
import time

from app.judge import CRITERIA, Scorecard
from app.llm import StructuredResult

REPLY = (
    "That sounds reasonable at first, but it skips the main cost. When a city tried this, the people it was "
    "meant to help were the first to lose out, because the money had to come from somewhere. My opponent has "
    "not said who pays, and until they do, the case does not stand."
)


class FakeLLM:
    def chat_stream(self, messages, model, **kw):
        for word in REPLY.split(" "):
            time.sleep(0.01)
            yield word + " "

    def structured(self, messages, model, schema, **kw):
        if schema is not Scorecard:
            data = schema.model_validate({"verdict": "ok"})
        else:
            said = {"pro": [], "con": []}
            for side, text in re.findall(r"\[(PRO|CON) - \w+\]\n(.+)", messages[-1]["content"]):
                said[side.lower()].append(text.split(". ")[0].strip())

            def side_scores(side, score):
                return {
                    "side": side,
                    "scores": [
                        {
                            "criterion": c,
                            "score": score,
                            "quotes": said[side][i % 3 : i % 3 + 1],
                            "reason": f"Fake reason for {c}.",
                        }
                        for i, c in enumerate(CRITERIA)
                    ],
                }

            data = Scorecard.model_validate(
                {
                    "sides": [side_scores("pro", 7), side_scores("con", 6)],
                    "winner": "pro",
                    "summary": "Fake verdict for local testing: PRO was slightly more specific.",
                }
            )
        return StructuredResult(data=data, raw_text="{}", model="fake-model", latency_s=0.0, attempts=1, repaired=False)
