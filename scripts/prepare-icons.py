from pathlib import Path
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "desktop" / "assets"
RESOURCE_ASSETS = ROOT / "resources" / "app" / "assets"
PUBLIC = ROOT / "frontend" / "public"


def rounded_icon(
    source: Path,
    output: Path,
    crop_box: tuple[int, int, int, int],
    radius_ratio: float = 0.17,
    inset_ratio: float = 0.012,
) -> Image.Image:
    image = Image.open(source).convert("RGBA").crop(crop_box)
    size = max(image.size)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(image, ((size - image.width) // 2, (size - image.height) // 2))

    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    inset = max(1, round(size * inset_ratio))
    radius = round(size * radius_ratio)
    draw.rounded_rectangle((inset, inset, size - inset, size - inset), radius=radius, fill=255)
    canvas.putalpha(mask)

    icon = canvas.resize((1024, 1024), Image.Resampling.LANCZOS)
    output.parent.mkdir(parents=True, exist_ok=True)
    icon.save(output)
    return icon


def main() -> None:
    dark_source = ASSETS / "icon-dark-source.png"
    light_source = ASSETS / "icon-light-source.png"

    # The generated files include a checkerboard preview background.
    # These crop boxes isolate the actual rounded-square icon before applying a real alpha mask.
    dark = rounded_icon(dark_source, ASSETS / "icon-dark.png", (38, 30, 1218, 1222))
    light = rounded_icon(light_source, ASSETS / "icon-light.png", (108, 88, 1148, 1164), radius_ratio=0.25, inset_ratio=0.018)

    # Dark is the static Windows identity: stronger contrast for taskbar, setup, and shortcuts.
    dark.save(ASSETS / "icon.png")
    dark.save(ASSETS / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

    RESOURCE_ASSETS.mkdir(parents=True, exist_ok=True)
    for name in ["icon.png", "icon-dark.png", "icon-light.png"]:
        Image.open(ASSETS / name).save(RESOURCE_ASSETS / name)

    PUBLIC.mkdir(parents=True, exist_ok=True)
    dark.resize((512, 512), Image.Resampling.LANCZOS).save(PUBLIC / "icon-dark.png")
    light.resize((512, 512), Image.Resampling.LANCZOS).save(PUBLIC / "icon-light.png")
    dark.resize((256, 256), Image.Resampling.LANCZOS).save(PUBLIC / "favicon.png")


if __name__ == "__main__":
    main()
