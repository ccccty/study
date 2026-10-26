"""生成 drill 页面的手机直达二维码。改 URL 后重跑一次即可。

用法：python tools/make_qr.py（在仓库根目录执行）
输出：qr.png
"""
import os

import qrcode
from PIL import Image, ImageDraw, ImageFont

URL = "https://ccccty.github.io/study/"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "qr.png")

qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=12, border=2)
qr.add_data(URL)
qr.make(fit=True)
img = qr.make_image(fill_color="#1b1f2a", back_color="white").convert("RGB")

W, H = img.size
pad = 70
canvas = Image.new("RGB", (W, H + pad), "white")
canvas.paste(img, (0, 0))

d = ImageDraw.Draw(canvas)
font = font2 = None
for p in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"]:
    try:
        font = ImageFont.truetype(p, 26)
        break
    except Exception:
        pass
try:
    font2 = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 17)
except Exception:
    pass

title = "工程概念 · 每日一推"
sub = "ccccty.github.io/study"
if font:
    d.text(((W - d.textlength(title, font=font)) / 2, H + 18), title, fill="#1b1f2a", font=font)
if font2:
    d.text(((W - d.textlength(sub, font=font2)) / 2, H + 46), sub, fill="#8b93a5", font=font2)

canvas.save(OUT)
print("saved", OUT, canvas.size)
