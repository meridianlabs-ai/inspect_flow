def clamp(value: int, low: int, high: int) -> int:
    """Clamp value to the inclusive range [low, high].

    Returns low if value < low, high if value > high, otherwise value.
    """
    return min(high, max(low, value))


def test_clamp_lower_bound() -> None:
    assert clamp(-5, 0, 10) == 0
    assert clamp(3, 0, 10) == 3


def test_clamp_upper_bound() -> None:
    assert clamp(15, 0, 10) == 10
    assert clamp(10, 0, 10) == 10
