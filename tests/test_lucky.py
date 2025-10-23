from api.services.option_b_cleaner.lucky import lucky_from_dominant


def test_lucky_defaults():
    lucky = lucky_from_dominant("Sun", "Libra")
    assert lucky["direction"] == "East"
    assert "Rose" in lucky["color"] or "rose" in lucky["color"] or "Soft" in lucky["color"]
