from app.quotes import is_real_quote

SOURCE = (
    "Homework at this age mostly measures how much help a child gets at home, which widens the gap between families."
)


def test_exact_quote_passes():
    assert is_real_quote("measures how much help a child gets at home", SOURCE)


def test_ignores_case_whitespace_and_wrapping_marks():
    assert is_real_quote('"Homework  at this AGE mostly measures..."', SOURCE)
    assert is_real_quote("“widens the gap between families.”", SOURCE)


def test_curly_apostrophes_and_dashes_match_straight_ones():
    assert is_real_quote("it’s fine — really", "It's fine - really, honestly.")


def test_edited_quote_fails():
    assert not is_real_quote("measures how much help a child gets at school", SOURCE)


def test_paraphrase_fails():
    assert not is_real_quote("homework shows how much parents help", SOURCE)


def test_too_short_quote_fails_even_if_present():
    assert not is_real_quote("home", SOURCE)
