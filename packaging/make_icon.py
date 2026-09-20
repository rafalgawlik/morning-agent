"""Generate the app's icons with Pillow (dev-only; NOT a runtime dependency).

Outputs:
  morning_agent/assets/sun.png       — menu bar template icon (black + alpha)
  morning_agent/assets/app_icon.png  — colored Dock / Cmd-Tab icon (sun on amber)

macOS tints template images automatically for light/dark menu bars, so the menu
bar shape is solid black on transparent. The app icon is a full-color rounded tile.

Run:  python packaging/make_icon.py
"""

import math
import os

from PIL import Image, ImageDraw

BLACK = (0, 0, 0, 255)
WHITE = (255, 255, 255, 255)


def _draw_sun_shape(d: ImageDraw.ImageDraw, s: float, color, *,
                    rd: float, r_in: float, r_out: float, w: float) -> None:
    cx = cy = s / 2
    d.ellipse([cx - rd, cy - rd, cx + rd, cy + rd], fill=color)
    for i in range(8):
        a = math.pi / 4 * i
        x1, y1 = cx + r_in * math.cos(a), cy + r_in * math.sin(a)
        x2, y2 = cx + r_out * math.cos(a), cy + r_out * math.sin(a)
        d.line([x1, y1, x2, y2], fill=color, width=max(1, int(w)))
        for (x, y) in ((x1, y1), (x2, y2)):
            d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=color)


def draw_sun(size: int) -> Image.Image:
    """Menu bar template icon: solid black sun on transparent."""
    ss = 8  # supersample for smooth edges
    s = size * ss
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    _draw_sun_shape(d, s, BLACK, rd=s * 0.205, r_in=s * 0.31, r_out=s * 0.46, w=s * 0.085)
    return img.resize((size, size), Image.LANCZOS)


def draw_sun_frame(size: int, angle: float) -> Image.Image:
    """One spin frame: the template sun rotated by `angle` degrees."""
    ss = 8
    s = size * ss
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    _draw_sun_shape(ImageDraw.Draw(img), s, BLACK,
                    rd=s * 0.205, r_in=s * 0.31, r_out=s * 0.46, w=s * 0.085)
    img = img.rotate(angle, resample=Image.BICUBIC, center=(s / 2, s / 2))
    return img.resize((size, size), Image.LANCZOS)


def draw_app_icon(size: int = 512) -> Image.Image:
    """Dock / Cmd-Tab icon: a white sun on a rounded amber tile."""
    ss = 2
    s = size * ss

    # Vertical amber gradient.
    top, bot = (255, 182, 72), (255, 138, 30)
    grad = Image.new("RGBA", (s, s))
    gd = ImageDraw.Draw(grad)
    for y in range(s):
        t = y / (s - 1)
        gd.line(
            [(0, y), (s, y)],
            fill=(
                int(top[0] + (bot[0] - top[0]) * t),
                int(top[1] + (bot[1] - top[1]) * t),
                int(top[2] + (bot[2] - top[2]) * t),
                255,
            ),
        )

    # Rounded-rectangle mask (macOS-style tile).
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.225), fill=255)

    tile = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    tile.paste(grad, (0, 0), mask)

    # White sun on top.
    _draw_sun_shape(ImageDraw.Draw(tile), s, WHITE,
                    rd=s * 0.15, r_in=s * 0.225, r_out=s * 0.34, w=s * 0.055)
    return tile.resize((size, size), Image.LANCZOS)


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(here, "..", "morning_agent", "assets")
    os.makedirs(out_dir, exist_ok=True)
    # 44px scales down crisply to the ~22px menu bar height (incl. Retina).
    draw_sun(44).save(os.path.join(out_dir, "sun.png"))
    draw_app_icon(512).save(os.path.join(out_dir, "app_icon.png"))
    print("wrote", os.path.normpath(os.path.join(out_dir, "sun.png")))
    print("wrote", os.path.normpath(os.path.join(out_dir, "app_icon.png")))

    # Spin frames for the loading animation. The sun has 8-fold symmetry, so a
    # 0–45° sweep is one seamless rotation.
    frames = 12
    for i in range(frames):
        draw_sun_frame(44, i * (45.0 / frames)).save(
            os.path.join(out_dir, f"sun_spin_{i:02d}.png"))
    print(f"wrote {frames} spin frames (sun_spin_NN.png)")


if __name__ == "__main__":
    main()
