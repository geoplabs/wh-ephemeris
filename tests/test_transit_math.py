from api.services.transit_math import is_applying, signed_delta


def test_signed_delta_normalises_within_range():
    # 190° ahead of a 180° aspect should be reported as +10° (already past exact).
    delta = signed_delta(200.0, 10.0, 180.0)
    assert -180.0 <= delta <= 180.0
    assert round(delta, 6) == 10.0


def test_direct_motion_applying_and_separating():
    # Transit is 2° behind exact conjunction and moving forward -> applying.
    assert is_applying(28.0, 1.0, 30.0, 0.0, 0.0)
    # Transit is 2° ahead of exact conjunction and still moving forward -> separating.
    assert not is_applying(32.0, 1.0, 30.0, 0.0, 0.0)


def test_retrograde_motion_reverses_application():
    # Transit is past the aspect but moving retrograde back towards exact -> applying.
    assert is_applying(182.5, -0.8, 0.0, 0.0, 180.0)
    # Transit is approaching but turns retrograde away from exact -> separating.
    assert not is_applying(177.5, -0.8, 0.0, 0.0, 180.0)


def test_equal_speeds_considered_separating():
    # With virtually identical speeds there is no convergence toward exact.
    assert not is_applying(62.0, 1.0, 0.0, 1.0, 60.0)

