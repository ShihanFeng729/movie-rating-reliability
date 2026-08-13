"""Generate compact, dependency-free SVG figures from aggregate V1 reports."""

from __future__ import annotations

from html import escape
from pathlib import Path


def write_horizontal_bar_chart(
    path: Path,
    *,
    title: str,
    subtitle: str,
    rows: list[tuple[str, float]],
    maximum: float,
    accent: str,
) -> None:
    """Write an accessible horizontal bar chart with values printed on each row."""

    if not rows or maximum <= 0 or any(value < 0 for _, value in rows):
        raise ValueError("Chart rows and maximum must contain valid non-negative values.")
    width = 900
    left = 285
    plot_width = 535
    row_height = 76
    height = 155 + row_height * len(rows)
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description">',
        f'<title id="title">{escape(title)}</title>',
        f'<desc id="description">{escape(subtitle)}</desc>',
        '<rect width="100%" height="100%" fill="#ffffff" rx="18"/>',
        f'<text x="48" y="52" font-family="Arial, sans-serif" font-size="27" '
        f'font-weight="700" fill="#172033">{escape(title)}</text>',
        f'<text x="48" y="84" font-family="Arial, sans-serif" font-size="16" '
        f'fill="#566074">{escape(subtitle)}</text>',
    ]
    for index, (label, value) in enumerate(rows):
        y = 122 + index * row_height
        bar_width = plot_width * value / maximum
        elements.extend([
            f'<text x="{left - 18}" y="{y + 27}" text-anchor="end" '
            f'font-family="Arial, sans-serif" font-size="17" fill="#273246">'
            f'{escape(label)}</text>',
            f'<rect x="{left}" y="{y}" width="{plot_width}" height="34" '
            'rx="7" fill="#edf1f7"/>',
            f'<rect x="{left}" y="{y}" width="{bar_width:.1f}" height="34" '
            f'rx="7" fill="{accent}"/>',
            f'<text x="{min(left + bar_width + 10, width - 52):.1f}" y="{y + 24}" '
            f'font-family="Arial, sans-serif" font-size="16" font-weight="700" '
            f'fill="#172033">{value:.4f}</text>',
        ])
    elements.append('</svg>')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(elements) + "\n", encoding="utf-8")
