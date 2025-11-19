from pathlib import Path

import pytest

pytest.importorskip("reportlab")

from api.services.yearly_pdf_enhanced import ContentValidator, render_enhanced_yearly_pdf


def test_content_validator_blocks_wrong_year():
    validator = ContentValidator(target_year=2025)
    # Allowed for December 2024
    assert validator.clean_text("As we close 2024", month_label="December 2024") == "As we close 2024"
    # But reject stray 2024 mentions elsewhere
    try:
        validator.clean_text("Prepare for 2024 wins", month_label="January 2025")
    except ValueError as exc:
        assert "wrong year" in str(exc)
    else:
        raise AssertionError("Expected ValueError for wrong year reference")


def test_render_enhanced_yearly_pdf_generates_file(tmp_path):
    out = tmp_path / "yearly.pdf"
    payload = {
        "report": {
            "meta": {
                "profile_name": "John",
                "sun_sign": "Taurus",
                "target_year": 2025,
                "birth_info": {
                    "date": "15 May 1990",
                    "time": "14:30",
                    "place": "New Delhi (India)",
                },
            },
            "year_at_glance": {
                "commentary": "Absolutely focus on growth in 2025.",
                "top_events": [
                    {
                        "title": "Solar Eclipse",
                        "date": "2025-03-29",
                        "summary": "Career reset moment.",
                        "score": 0.98,
                        "tags": ["Career"],
                    }
                ],
                "heatmap": [
                    {"label": "March", "score": 5},
                    {"label": "July", "score": 1},
                ],
            },
            "eclipses_and_lunations": [
                {
                    "date": "2025-03-29",
                    "kind": "Solar Eclipse",
                    "sign": "Aries",
                    "house": "Career",
                    "guidance": "Do focus on bold leadership. Don't overextend at home.",
                }
            ],
            "months": [
                {
                    "month": "December 2024",
                    "overview": "Absolutely gather your wins.",
                    "career_and_finance": "As we step into 2025, pitch ideas.",
                    "relationships_and_family": "Stay present.",
                    "health_and_energy": "Rest intentionally.",
                    "planner_actions": ["30 Dec – Review 2025 goals"],
                    "high_score_days": [
                        {
                            "date": "2024-12-20",
                            "transit_body": "Sun",
                            "natal_body": "Jupiter",
                            "aspect": "trine",
                            "score": 4.2,
                            "raw_note": "Big confidence push.",
                        },
                        {
                            "date": "2024-12-28",
                            "transit_body": "Venus",
                            "natal_body": "Moon",
                            "aspect": "sextile",
                            "score": 3.5,
                            "raw_note": "Connect with partners.",
                        },
                    ],
                    "caution_days": [
                        {
                            "date": "2024-12-22",
                            "transit_body": "Mars",
                            "natal_body": "Saturn",
                            "aspect": "square",
                            "score": -3.8,
                            "raw_note": "Slow the pace.",
                        },
                        {
                            "date": "2024-12-30",
                            "transit_body": "Mercury",
                            "natal_body": "Neptune",
                            "aspect": "opposition",
                            "score": -2.0,
                            "raw_note": "Check the details.",
                        },
                    ],
                }
            ],
            "glossary": {"Trine": "A flow aspect."},
            "interpretation_index": {"Sun trine Jupiter": "Opens doors in career."},
        },
        "generated_at": "2024-11-30T00:00:00Z",
    }

    pdf_path = render_enhanced_yearly_pdf(payload, str(out))
    assert Path(pdf_path).exists()
    assert Path(pdf_path).read_bytes().startswith(b"%PDF")
