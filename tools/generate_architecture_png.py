from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parents[1]
OUT_PATH = BASE_DIR / "static" / "images" / "application_architecture_workflow.png"

WIDTH = 1400
HEIGHT = 900


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    font_name = "timesbd.ttf" if bold else "times.ttf"
    font_path = Path("C:/Windows/Fonts") / font_name
    return ImageFont.truetype(str(font_path), size)


TITLE = font(34, True)
BOX_TITLE = font(22, True)
BOX_TEXT = font(17)
SMALL = font(15)


def centered(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fnt, fill="#102a43") -> None:
    x, y = xy
    bbox = draw.textbbox((0, 0), text, font=fnt)
    draw.text((x - (bbox[2] - bbox[0]) / 2, y), text, font=fnt, fill=fill)


def box(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    title: str,
    lines: list[str],
    fill: str,
    outline: str,
) -> None:
    draw.rounded_rectangle(xy, radius=10, fill=fill, outline=outline, width=3)
    x1, y1, x2, _ = xy
    cx = (x1 + x2) // 2
    centered(draw, (cx, y1 + 30), title, BOX_TITLE)
    for idx, line in enumerate(lines):
        centered(draw, (cx, y1 + 66 + (idx * 25)), line, BOX_TEXT, "#243b53")


def arrow(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], fill="#1f4e79", width=3) -> None:
    draw.line(points, fill=fill, width=width, joint="curve")
    if len(points) < 2:
        return
    x1, y1 = points[-2]
    x2, y2 = points[-1]
    dx = x2 - x1
    dy = y2 - y1
    length = max((dx * dx + dy * dy) ** 0.5, 1)
    ux = dx / length
    uy = dy / length
    size = 14
    left = (x2 - ux * size - uy * size * 0.55, y2 - uy * size + ux * size * 0.55)
    right = (x2 - ux * size + uy * size * 0.55, y2 - uy * size - ux * size * 0.55)
    draw.polygon([(x2, y2), left, right], fill=fill)


def main() -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(image)

    centered(draw, (700, 30), "APPLICATION WORKFLOW AND SYSTEM ARCHITECTURE", TITLE)
    centered(
        draw,
        (700, 72),
        "Talent Acquisition System - Resume Analysis, Scoring, Recommendation and Report Storage",
        SMALL,
        "#334e68",
    )

    blue = ("#f7fbff", "#1f4e79")
    green = ("#eef7ee", "#2f6f3e")
    orange = ("#fff7e8", "#9a5b00")
    red = ("#f9eeee", "#9b2c2c")

    box(draw, (70, 145, 300, 270), "User Browser", ["Resume upload", "Target job details"], *blue)
    box(draw, (380, 145, 630, 270), "Flask Web App", ["Routes and sessions", "Jinja rendering"], *blue)
    box(draw, (710, 145, 960, 270), "Validation Layer", ["CSRF and rate limit", "File signature check"], *red)
    box(draw, (1040, 145, 1320, 270), "Temporary Upload", ["Secure filename", "Deleted after parsing"], *green)

    box(draw, (90, 365, 350, 500), "Text Extraction", ["PDF - pypdf", "DOCX - python-docx", "TXT - direct read"], *green)
    box(draw, (430, 365, 690, 500), "Resume Analysis", ["Normalize text", "Detect skills and sections", "Estimate experience"], *green)
    box(draw, (770, 365, 1030, 500), "Scoring Engine", ["Criteria-wise score", "Role-adjusted weights", "Suggestions generated"], *green)
    box(draw, (1090, 365, 1330, 500), "Job Matching", ["Target role match", "Matched keywords", "Missing keywords"], *green)

    box(draw, (120, 625, 365, 755), "Job Catalog CSV", ["Role titles", "Keywords and descriptions"], *orange)
    box(draw, (460, 625, 705, 755), "SQLite Database", ["Users and reports", "Contacts and history"], *orange)
    box(draw, (800, 625, 1045, 755), "Result Pages", ["Score breakdown", "Recommendations"], *blue)
    box(draw, (1125, 625, 1330, 755), "PDF Export", ["Saved report", "Downloadable copy"], *blue)

    arrow(draw, [(300, 207), (380, 207)])
    arrow(draw, [(630, 207), (710, 207)])
    arrow(draw, [(960, 207), (1040, 207)])
    arrow(draw, [(1180, 270), (1180, 315), (220, 315), (220, 365)])
    arrow(draw, [(350, 432), (430, 432)])
    arrow(draw, [(690, 432), (770, 432)])
    arrow(draw, [(1030, 432), (1090, 432)])
    arrow(draw, [(1210, 500), (1210, 560), (922, 560), (922, 625)])
    arrow(draw, [(900, 500), (900, 560), (582, 560), (582, 625)])
    arrow(draw, [(242, 625), (242, 555), (1185, 555), (1210, 500)])
    arrow(draw, [(705, 690), (800, 690)])
    arrow(draw, [(1045, 690), (1125, 690)])

    centered(
        draw,
        (700, 840),
        "Flow: Browser -> Flask -> Validation -> Extraction -> Analysis -> Scoring -> Matching -> Storage -> Result and PDF Export",
        SMALL,
        "#334e68",
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUT_PATH)
    print(OUT_PATH)


if __name__ == "__main__":
    main()
