"""生成 study PWA 图标。用法：python tools/make_icons.py（在仓库根目录执行）"""
import os

from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons")
C1 = (27, 75, 143)    # --accent
C2 = (13, 148, 136)   # --teal
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
]


def gradient(size):
    img = Image.new("RGB", (size, size))
    d = ImageDraw.Draw(img)
    for y in range(size):
        t = y / max(size - 1, 1)
        d.line([(0, y), (size, y)], fill=tuple(int(C1[i] + (C2[i] - C1[i]) * t) for i in range(3)))
    return img


def make(size, path, glyph="概", radius_ratio=0.22):
    # 4x 超采样后缩小，边缘更干净
    s = size * 4
    img = gradient(s).convert("RGBA")

    # 圆角遮罩
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * radius_ratio), fill=255)
    img.putalpha(mask)

    # 字形
    f = None
    for p in FONT_CANDIDATES:
        try:
            f = ImageFont.truetype(p, int(s * 0.52))
            break
        except Exception:
            continue
    if f:
        d = ImageDraw.Draw(img)
        box = d.textbbox((0, 0), glyph, font=f)
        w, h = box[2] - box[0], box[3] - box[1]
        # 光学居中：按字框中心对齐，略微上移
        x = (s - w) / 2 - box[0]
        y = (s - h) / 2 - box[1] - s * 0.01
        d.text((x, y), glyph, font=f, fill=(255, 255, 255, 255))

    img = img.resize((size, size), Image.LANCZOS)
    img.save(path)
    print("saved", path, size)


os.makedirs(OUT_DIR, exist_ok=True)
make(512, os.path.join(OUT_DIR, "icon-512.png"))
make(192, os.path.join(OUT_DIR, "icon-192.png"))
# iOS 主屏图标：不要圆角不要透明，系统会自己裁
make(180, os.path.join(OUT_DIR, "apple-touch-icon.png"), radius_ratio=0.0001)

# maskable 版本：内容缩到安全区（80%），底色铺满
img = gradient(512).convert("RGBA")
s = 512
inner = Image.open(os.path.join(OUT_DIR, "icon-512.png")).convert("RGBA").resize((int(s * 0.8), int(s * 0.8)), Image.LANCZOS)
canvas = Image.new("RGBA", (s, s), C1 + (255,))
canvas.paste(inner, ((s - inner.width) // 2, (s - inner.height) // 2), inner)
canvas.convert("RGB").save(os.path.join(OUT_DIR, "maskable-512.png"))
print("saved maskable")
