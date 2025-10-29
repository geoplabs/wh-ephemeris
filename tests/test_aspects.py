from api.services import aspects


def test_angle_diff_scorpio_to_aries_is_quincunx():
    # Scorpio begins at 210°; Aries at 0°. Ensure we recognise the 150° gap.
    diff = aspects._angle_diff(210.0, 0.0)
    assert diff == 150.0


def test_find_aspects_includes_quincunx():
    positions = {
        "Mercury": {"lon": 210.0, "speed_lon": 1.0},
        "Chiron": {"lon": 0.0, "speed_lon": 0.0},
    }
    policy = {"types": ["quincunx"], "orbs": {"default": 5.0}}

    found = aspects.find_aspects(positions, policy=policy)

    assert found, "Expected to detect a quincunx aspect"
    assert found[0]["type"] == "quincunx"
    assert found[0]["orb"] == 0.0


def test_find_aspects_accepts_inconjunct_alias():
    positions = {
        "Mercury": {"lon": 210.0, "speed_lon": 1.0},
        "Chiron": {"lon": 0.0, "speed_lon": 0.0},
    }
    policy = {"types": ["inconjunct"], "orbs": {"default": 5.0}}

    found = aspects.find_aspects(positions, policy=policy)

    assert found, "Expected to detect an inconjunct alias"
    assert found[0]["type"] == "quincunx"
