"""Generate assets/demo.gif — an animated walkthrough of the agent loop."""
from PIL import Image, ImageDraw, ImageFont

W, H = 720, 400
bg = (5, 8, 22)
emerald = (33, 233, 154)
gold = (255, 209, 102)
text_col = (207, 232, 255)
muted = (120, 140, 170)

try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 18)
    font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 26)
except Exception:
    font = ImageFont.load_default()
    font_big = font

steps = [
    ("OpenManus-Lite", "prompt> Write fib.py, run it, save output", "idle"),
    ("STEP 1 . think", "LLM decides: use python_execute", "run"),
    ("STEP 2 . act", "tool: python_execute(code=...)", "run"),
    ("OBSERVE", "output: 55", "run"),
    ("STEP 3 . think", "LLM decides: use str_replace_editor", "run"),
    ("STEP 4 . act", "tool: str_replace_editor(create)", "run"),
    ("OBSERVE", "saved -> workspace/fib.txt", "run"),
    ("STEP 5 . think", "task complete -> terminate", "run"),
    ("DONE", "terminate: fib=55, saved to fib.txt", "done"),
]


def draw_frame(title, body, state):
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 56], fill=(11, 26, 58))
    d.text((20, 16), "OpenManus-Lite", font=font_big, fill=emerald)
    pill_col = {"idle": muted, "run": gold, "done": emerald}[state]
    d.rounded_rectangle([W - 150, 14, W - 20, 42], radius=12, fill=pill_col)
    d.text((W - 138, 19), state.upper(), font=font, fill=(5, 8, 22))
    d.text((20, 80), title, font=font_big, fill=text_col)
    d.rounded_rectangle([20, 120, W - 20, H - 30], radius=10, outline=(40, 60, 90))
    y = 140
    for line in (body[i:i + 60] for i in range(0, len(body), 60)):
        d.text((40, y), line, font=font, fill=text_col)
        y += 28
    d.rectangle([40, H - 50, 58, H - 34], fill=emerald)
    return img


frames = []
for title, body, state in steps:
    f = draw_frame(title, body, state)
    frames.append(f)
    frames.append(f)

frames[0].save(
    "assets/demo.gif",
    save_all=True,
    append_images=frames[1:],
    duration=900,
    loop=0,
)
print("frames:", len(frames), "-> assets/demo.gif")
