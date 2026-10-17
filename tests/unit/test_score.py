import pytest

from genetic_opt.score import Score

# ── Score Tests ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "score",
    [
        Score(value=1.5),
        Score(value=1.5, name="ones", extra_metrics={"zeros": 2}),
        Score(value=1.5, name="", extra_metrics={}),
        Score(value=1.5, extra_metrics=[]),
    ],
)
def test_a_score_comes_back_equal_from_its_dict(score):
    assert Score(**score.to_dict()) == score


def test_to_dict_leaves_out_what_the_score_does_not_have():
    assert Score(value=0).to_dict() == {"value": 0}
