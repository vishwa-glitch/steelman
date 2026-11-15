"""Check that a quote the judge cites really appears in what that side said.

Matching ignores differences a model commonly introduces when copying text (curly vs straight quotes,
dash styles, extra whitespace, letter case) but nothing else: a paraphrase is not a quote.
"""

import re

_TRANSLATE = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "…": "...",
    }
)
MIN_QUOTE_CHARS = 8  # shorter "quotes" (a word or two) prove nothing


def normalize(text: str) -> str:
    text = text.translate(_TRANSLATE).lower()
    return re.sub(r"\s+", " ", text).strip()


def _strip_wrapping(quote: str) -> str:
    """Models often wrap a quote in quote marks or trail it with an ellipsis."""
    q = quote.strip()
    q = q.strip("\"'‘’“”")
    q = re.sub(r"(\.\.\.|…)$", "", q)
    q = re.sub(r"^(\.\.\.|…)", "", q)
    return q.strip()


def is_real_quote(quote: str, source: str) -> bool:
    q = normalize(_strip_wrapping(quote))
    if len(q) < MIN_QUOTE_CHARS:
        return False
    return q in normalize(source)
