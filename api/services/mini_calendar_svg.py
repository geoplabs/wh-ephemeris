import calendar


def mini_calendar_svg(year: int, month: int, marked_days: list[int] | set[int], primary: str = "#4A3AFF") -> str:
    """
    Render a compact monthly calendar SVG (7x6 grid) with marked days highlighted.
    - year, month: the calendar month to render
    - marked_days: 1..31 day numbers to highlight
    - primary: highlight color (defaults to brand-ish purple)
    """
    marked = set(int(d) for d in marked_days if isinstance(d, (int, str)))
    cal = calendar.Calendar(firstweekday=0)  # Monday=0 by default
    matrix = calendar.monthcalendar(year, month)  # weeks as [Mon..Sun] with 0 padding

    # Convert to Sunday-first grid
    rotated = []
    for week in matrix:
        sun_first = [week[-1]] + week[:-1]
        rotated.append(sun_first)

    W, H = 600, 420
    P = 24
    CW, CH = (W - 2 * P) / 7, (H - 2 * P) / 7.2
    r = 8

    weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    svg.append(f'<rect x="0" y="0" width="{W}" height="{H}" rx="{r}" ry="{r}" fill="white" stroke="#e6e8ee"/>')
    svg.append(
        '<style>.wk{font:600 13px system-ui, sans-serif; fill:#6a7280}'
        '.d{font:600 12px system-ui, sans-serif; fill:#1b1f23}'
        '.m{fill:%s; stroke:%s; stroke-width:0; opacity:.18}' % (primary, primary)
        + '.dot{fill:%s;}' % primary
        + '</style>'
    )

    for i, wd in enumerate(weekdays):
        x = P + i * CW + CW / 2
        y = P + CH * 0.8
        svg.append(f'<text class="wk" x="{x:.1f}" y="{y:.1f}" text-anchor="middle">{wd}</text>')

    y0 = P + CH * 1.4
    day_circle_r = min(CW, CH) * 0.36
    for row, week in enumerate(rotated):
        for col, day in enumerate(week):
            x = P + col * CW
            y = y0 + row * CH
            svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{CW:.1f}" height="{CH:.1f}" fill="none" stroke="#f0f2f7"/>')
            if day != 0:
                cx = x + CW / 2
                cy = y + CH / 2 + 2
                if day in marked:
                    svg.append(f'<circle class="m" cx="{cx:.1f}" cy="{cy:.1f}" r="{day_circle_r:.1f}"/>')
                    svg.append(f'<circle class="dot" cx="{cx:.1f}" cy="{(y + CH - 10):.1f}" r="3"/>')
                svg.append(f'<text class="d" x="{x + 8:.1f}" y="{y + 16:.1f}">{day}</text>')

    month_name = calendar.month_name[month]
    svg.append(
        f'<text x="{P:.1f}" y="{P - 6 + 12:.1f}" style="font:700 14px system-ui, sans-serif; fill:#1b1f23">'
        f'{month_name} {year}</text>'
    )

    svg.append("</svg>")
    return "".join(svg)
