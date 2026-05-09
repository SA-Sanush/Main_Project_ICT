from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parents[1]
OUT_PATH = BASE_DIR / "static" / "images" / "job_catalog_add_form.png"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "timesbd.ttf" if bold else "times.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)


def rounded(draw: ImageDraw.ImageDraw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def text(draw: ImageDraw.ImageDraw, xy, value, size=22, bold=False, fill="#102a43"):
    draw.text(xy, value, font=font(size, bold), fill=fill)


def input_box(draw: ImageDraw.ImageDraw, xy, label, placeholder, multiline=False):
    x1, y1, x2, y2 = xy
    text(draw, (x1, y1 - 34), label, 22, True)
    rounded(draw, (x1, y1, x2, y2), 8, "#ffffff", "#bcccdc", 2)
    text(draw, (x1 + 20, y1 + 20), placeholder, 20, False, "#829ab1")
    if multiline:
        draw.line((x2 - 28, y2 - 15, x2 - 14, y2 - 29), fill="#d9e2ec", width=2)
        draw.line((x2 - 22, y2 - 15, x2 - 14, y2 - 23), fill="#d9e2ec", width=2)


def main() -> None:
    image = Image.new("RGB", (1200, 850), "#f5f7fb")
    draw = ImageDraw.Draw(image)

    rounded(draw, (70, 60, 1130, 790), 16, "#ffffff", "#d9e2ec", 2)

    text(draw, (115, 105), "Admin Dashboard", 34, True)
    text(draw, (115, 150), "Manage the role catalog and add new job roles for resume matching.", 21, False, "#52606d")

    cards = [
        ("Users", "4"),
        ("Reports", "18"),
        ("Catalog Roles", "5"),
    ]
    for idx, (label, value) in enumerate(cards):
        x = 115 + idx * 315
        rounded(draw, (x, 210, x + 270, 300), 12, "#f7fbff", "#1f4e79", 2)
        text(draw, (x + 24, 232), label, 20, False, "#52606d")
        text(draw, (x + 24, 258), value, 28, True)

    rounded(draw, (115, 350, 1085, 720), 12, "#fbfdff", "#d9e2ec", 2)
    text(draw, (150, 390), "Add Role", 30, True)

    input_box(draw, (150, 475, 555, 535), "Title", "Example: UX Designer")
    input_box(draw, (620, 475, 1050, 535), "Keywords", "research, figma, prototyping, usability")
    input_box(draw, (150, 620, 820, 695), "Description", "Short role description", multiline=True)

    rounded(draw, (860, 628, 1050, 695), 10, "#1f4e79", "#1f4e79", 2)
    button_label = "Add Role"
    bbox = draw.textbbox((0, 0), button_label, font=font(23, True))
    draw.text(
        (955 - (bbox[2] - bbox[0]) / 2, 648),
        button_label,
        font=font(23, True),
        fill="#ffffff",
    )

    text(draw, (150, 748), "Figure: Job catalog add form in the admin dashboard", 18, False, "#52606d")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUT_PATH)
    print(OUT_PATH)


if __name__ == "__main__":
    main()
