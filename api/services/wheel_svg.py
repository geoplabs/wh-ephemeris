"""Utilities for generating simple SVG chart wheels."""


def simple_wheel_svg(title: str = "Chart Wheel") -> str:
    """Return a very basic SVG wheel with 12 sectors and a title.

    The wheel is intentionally minimal; it's only a placeholder for tests and
    development environments where a full wheel renderer would be overkill.
    """

    return (
        "<svg xmlns='http://www.w3.org/2000/svg' width='800' height='800'>"
        "  <circle cx='400' cy='400' r='360' fill='white' stroke='black' stroke-width='2'/>"
        + "".join(
            [
                f"<line x1='400' y1='400' x2='{400+360*cos:.0f}' y2='{400+360*sin:.0f}' stroke='gray'/>"
                for cos, sin in [
                    (1, 0),
                    (0.866, 0.5),
                    (0.5, 0.866),
                    (0, 1),
                    (-0.5, 0.866),
                    (-0.866, 0.5),
                    (-1, 0),
                    (-0.866, -0.5),
                    (-0.5, -0.866),
                    (0, -1),
                    (0.5, -0.866),
                    (0.866, -0.5),
                ]
            ]
        )
        + f"  <text x='400' y='60' font-family='sans-serif' font-size='24' text-anchor='middle'>{title}</text>"
        "</svg>"
    )

