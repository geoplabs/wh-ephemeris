"""Utilities for generating simple SVG chart wheels."""


def simple_wheel_svg(bodies):
    # very simple polar plot: 360° ring with planet labels by longitude
    items = []
    for b in bodies:
        theta = b["lon"]
        items.append(
            f'<text x="50%" y="50%" transform="rotate({theta} 256 256) translate(0,-200)" font-size="10">{b["name"]}</text>'
        )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
      <circle cx="256" cy="256" r="220" fill="none" stroke="#999" stroke-width="1" />
      {"".join(items)}
    </svg>'''
