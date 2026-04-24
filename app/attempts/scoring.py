def compute_percentage(score: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((score / total) * 100, 2)


def feedback_for_percentage(percentage: float) -> str:
    if percentage >= 80:
        return "Great job! You're getting there!"
    if percentage >= 60:
        return "Good effort — review the explanations and try again."
    return "Keep going — revisit the concepts and come back stronger."
