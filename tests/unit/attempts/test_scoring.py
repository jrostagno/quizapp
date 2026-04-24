import pytest

from app.attempts.scoring import compute_percentage, feedback_for_percentage


@pytest.mark.parametrize(
    "score,total,expected",
    [
        (5, 5, 100.0),
        (4, 5, 80.0),
        (3, 5, 60.0),
        (2, 5, 40.0),
        (0, 5, 0.0),
        (3, 7, 42.86),
        (0, 0, 0.0),
    ],
)
def test_compute_percentage_matches_expected(score: int, total: int, expected: float) -> None:
    assert compute_percentage(score, total) == expected


@pytest.mark.parametrize(
    "percentage,expected_substring",
    [
        (100.0, "Great job"),
        (80.0, "Great job"),
        (79.99, "Good effort"),
        (60.0, "Good effort"),
        (59.99, "Keep going"),
        (0.0, "Keep going"),
    ],
)
def test_feedback_matches_tier(percentage: float, expected_substring: str) -> None:
    assert expected_substring in feedback_for_percentage(percentage)
