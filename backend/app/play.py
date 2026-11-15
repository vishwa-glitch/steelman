"""Play a full debate in the terminal: python -m app.play "Motion text" --side pro [--difficulty sharp]

Type each of your turns on one line. Uses about 5 model calls (topic check, 3 AI turns, the judge).
"""

import argparse
import sys

from app.config import load_settings
from app.debate import Debate, DebateError, check_topic, opponent_turn
from app.judge import format_scorecard, judge
from app.llm import LLMClient


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("motion")
    p.add_argument("--side", choices=["pro", "con"], default="pro")
    p.add_argument("--difficulty", choices=["friendly", "sharp"], default="sharp")
    args = p.parse_args()
    s = load_settings()
    client = LLMClient(s)
    try:
        motion = check_topic(args.motion, client, s.judge_backup_model)
    except DebateError as e:
        print(e)
        return 1
    d = Debate(motion=motion, user_side=args.side, difficulty=args.difficulty)
    print(f"Motion: {motion}\nYou are {d.user_side.upper()}; the AI is {d.ai_side.upper()}.\n")
    while not d.finished:
        side, rnd = d.next_turn()  # type: ignore[misc]
        if d.whose_turn() == "ai":
            turn = opponent_turn(d, client, s.opponent_model)
            print(f"[AI {side.upper()} - {rnd}]\n{turn.text}\n")
        else:
            while True:
                try:
                    d.add_user_turn(input(f"[YOU {side.upper()} - {rnd}] > "))
                    print()
                    break
                except DebateError as e:
                    print(e)
                except EOFError:
                    print("\nInput ended before the debate finished.")
                    return 1
    print("The judge is deliberating...\n")
    print(format_scorecard(judge(d.transcript(), client, s.judge_model)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
