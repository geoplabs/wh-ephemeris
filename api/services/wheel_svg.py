import math
from typing import List, Dict, Any

SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]

def render_wheel(bodies: List[Dict[str, Any]], size: int = 300) -> str:
    """Return a very small SVG wheel with bodies marked."""
    r = size / 2 - 10
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="{-size/2} {-size/2} {size} {size}">']
    svg.append(f'<circle cx="0" cy="0" r="{r}" fill="none" stroke="black"/>')
    # sign sectors and labels
    for i, sign in enumerate(SIGNS):
        angle = i * 30
        rad = math.radians(angle)
        x = r * math.cos(rad)
        y = r * math.sin(rad)
        svg.append(f'<line x1="0" y1="0" x2="{x:.2f}" y2="{y:.2f}" stroke="#999"/>')
        t_angle = angle + 15
        tx = (r - 25) * math.cos(math.radians(t_angle))
        ty = (r - 25) * math.sin(math.radians(t_angle))
        svg.append(f'<text x="{tx:.2f}" y="{ty:.2f}" font-size="10" text-anchor="middle" dominant-baseline="middle">{sign[:3]}</text>')
    # body markers
    for body in bodies:
        angle = body.get("lon", 0)
        rad = math.radians(angle)
        bx = (r - 10) * math.cos(rad)
        by = (r - 10) * math.sin(rad)
        svg.append(f'<circle cx="{bx:.2f}" cy="{by:.2f}" r="3" fill="black"/>')
        tx = (r - 2) * math.cos(rad)
        ty = (r - 2) * math.sin(rad)
        svg.append(f'<text x="{tx:.2f}" y="{ty:.2f}" font-size="8" text-anchor="middle">{body["name"][:2]}</text>')
    svg.append("</svg>")
    return "".join(svg)
