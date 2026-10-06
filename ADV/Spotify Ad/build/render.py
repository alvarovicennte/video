import numpy as np, math, sys, subprocess, os
from functools import lru_cache
from multiprocessing import Pool
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PH = f"{BASE}/assets_in/photos"
BR = f"{BASE}/assets_in/brand"
FD = "/usr/share/fonts/opentype/inter"

ASPECT = os.environ.get("ASPECT", "16x9")
if ASPECT == "9x16":
    W, H = 720, 1280
else:
    W, H = 1280, 720
PORTRAIT = H > W
FPS = 60
DUR = 20.0
GREEN = (30, 215, 96)
BG = (11, 11, 12)
SUB = 4
SHUTTER = 0.9
CX, CY = W // 2, H // 2
BEAT = 0.5


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def eo3(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def eo5(x):
    x = clamp(x)
    return 1 - (1 - x) ** 5


def eio(x):
    x = clamp(x)
    return 3 * x * x - 2 * x ** 3


def ob(x, s=1.4):
    x = clamp(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


@lru_cache(None)
def font(size, w="Bold"):
    return ImageFont.truetype(f"{FD}/InterDisplay-{w}.otf", size)


@lru_cache(None)
def text_mask(txt, size, w="Bold"):
    f = font(size, w)
    l, t, r, b = f.getbbox(txt)
    pad = 24
    im = Image.new("L", (r - l + 2 * pad, b - t + 2 * pad), 0)
    ImageDraw.Draw(im).text((pad - l, pad - t), txt, font=f, fill=255)
    return im


def sweep_text(base, txt, size, xy, t_rel, color=(255, 255, 255), weight="Bold",
               dur=0.55, anchor="l", opacity=1.0, rise=14):
    """Light-sweep reveal: a bright band wipes across and writes the text."""
    if t_rel <= 0 or opacity <= 0:
        return
    m = text_mask(txt, size, weight)
    p = clamp(t_rel / dur)
    a = np.asarray(m, dtype=np.float32) / 255
    h, w = a.shape
    edge = eo3(p) * (w + 140) - 70
    xs = np.arange(w, dtype=np.float32)[None, :]
    reveal = np.clip((edge - xs) / 60, 0, 1)
    band = np.exp(-((xs - edge) / 22) ** 2)
    alpha = np.clip(a * reveal, 0, 1) * opacity
    glow = np.clip(a * band * 0.9, 0, 1) * opacity * (1 - p * 0.6)
    img = Image.fromarray((alpha * 255).astype(np.uint8))
    gm = Image.fromarray((glow * 255).astype(np.uint8))
    x, y = xy
    if anchor == "c":
        x -= w // 2
    elif anchor == "r":
        x -= w
    y = y - h // 2 + int((1 - eo3(p)) * rise)
    base.paste(Image.new("RGB", (w, h), color), (x, y), img)
    base.paste(Image.new("RGB", (w, h), (170, 255, 200)), (x, y), gm)


def rounded_mask(w, h, r):
    s = 3
    m = Image.new("L", (w * s, h * s), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * s - 1, h * s - 1), r * s, fill=255)
    return m.resize((w, h), Image.LANCZOS)


# ---------- assets ----------
PHOTOS = {}
for k, fn in (("01", "01_sunrise_window"), ("02", "02_runner_sunrise"),
              ("03", "03_desk_lamp_night"), ("04", "04_night_ride")):
    im = Image.open(f"{PH}/{fn}.jpg").convert("RGB")
    s = 1500 / max(im.size)
    PHOTOS[k] = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)

LOGO_FULL = Image.open(f"{BR}/Spotify_Full_Logo_RGB_Green.png").convert("RGBA")
LOGO_FULL_W = Image.open(f"{BR}/Spotify_Full_Logo_RGB_White.png").convert("RGBA")
LW = int(W * (0.62 if PORTRAIT else 0.40))
LOGO_FULL = LOGO_FULL.resize((LW, int(LW * LOGO_FULL.height / LOGO_FULL.width)), Image.LANCZOS)
LOGO_FULL_W = LOGO_FULL_W.resize(LOGO_FULL.size, Image.LANCZOS)
LOGO_ICON_D = int(LW * 940 / 3432)
LOGO_X0 = CX - LW // 2
ICON_C = (LOGO_X0 + LOGO_ICON_D // 2, CY)

if PORTRAIT:
    CARD_W, CARD_H = 600, 640
    CARD_C = (CX, 400)
    TXT_X, TXT_Y = 60, 820
    NP_POS = (60, 1030)
    NP_W = 600
else:
    CARD_W, CARD_H = 620, 400
    CARD_C = (885, 350)
    TXT_X, TXT_Y = 64, 300
    NP_POS = (64, 470)
    NP_W = 420
CARD_MASK = rounded_mask(CARD_W, CARD_H, 28)

SCENES = [
    dict(t0=3.5, t1=6.0, k="01", big="6 a.m.", small="THE ALARM", label="Wake up", fx=.5, fy=.55, move="flip", dark=.0),
    dict(t0=6.0, t1=8.5, k="02", big="The long run", small="KEEP MOVING", label="Run", fx=.62, fy=.6, move="whip", dark=.0),
    dict(t0=8.5, t1=11.0, k="03", big="One more hour", small="LATE NIGHT", label="Late night", fx=.60, fy=.47, move="push", dark=.25, zoom=1.9),
    dict(t0=11.0, t1=13.5, k="04", big="The ride home", small="NEARLY THERE", label="Drive home", fx=.5, fy=.5, move="rise", dark=.0),
]


def cover(im, cw, ch, scale, fx, fy):
    s0 = max(cw / im.width, ch / im.height) * scale
    rw, rh = int(im.width * s0), int(im.height * s0)
    r = im.resize((rw, rh), Image.BILINEAR)
    x = int(clamp(fx * rw - cw / 2, 0, rw - cw))
    y = int(clamp(fy * rh - ch / 2, 0, rh - ch))
    return r.crop((x, y, x + cw, y + ch))


def vignette_arr():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W * .75)) ** 2 + ((yy - H / 2) / (H * .75)) ** 2)
    return (1 - 0.45 * np.clip(d, 0, 1) ** 2)[..., None]


VIG = vignette_arr()
GW, GH = 160, int(160 * H / W)
gy, gx = np.mgrid[0:GH, 0:GW].astype(np.float32)
gx /= GW
gy /= GH


def background(t, warm=0.0, boost=0.0):
    g = np.zeros((GH, GW), np.float32)
    for i, (ax, ay, sp, rad, amp) in enumerate(((.25, .35, .31, .38, 1.0), (.75, .65, .23, .42, .9), (.5, .5, .17, .5, .5))):
        px = ax + .18 * math.sin(t * sp * 2 + i * 2)
        py = ay + .15 * math.cos(t * sp * 1.7 + i)
        g += amp * np.exp(-(((gx - px) * (W / H)) ** 2 + (gy - py) ** 2) / (2 * (rad * .5) ** 2))
    g = np.asarray(Image.fromarray(g).resize((W, H), Image.BICUBIC))[..., None]
    base = np.array(BG, np.float32)[None, None, :]
    col = np.array(GREEN, np.float32) * (1 - warm) + np.array((255, 150, 60), np.float32) * warm
    return base + g * col[None, None, :] * (0.20 + 0.20 * boost)


def paste_rgba(img, layer, xy, opacity=1.0):
    if opacity <= 0:
        return
    a = layer.getchannel("A")
    if opacity < 1:
        a = a.point(lambda v: int(v * opacity))
    img.paste(layer.convert("RGB"), xy, a)


def pulse(t):
    return math.exp(-((t / BEAT) % 1) * 5.5)


def ring(img, cx, cy, R, t, amp=1.0, width=5, opacity=1.0, color=GREEN):
    if R < 2 or opacity <= 0:
        return
    box = int(R * 2 + 140)
    layer = Image.new("RGBA", (box, box), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pts = []
    n = 220
    p = pulse(t)
    for i in range(n + 1):
        th = 2 * math.pi * i / n
        w = (math.sin(th * 3 + t * 3.1) * .5 + math.sin(th * 7 - t * 4.3) * .3 + math.sin(th * 13 + t * 6.7) * .2)
        r = R + amp * (8 + 22 * p) * w
        pts.append((box / 2 + r * math.cos(th), box / 2 + r * math.sin(th)))
    d.line(pts, fill=color + (255,), width=width, joint="curve")
    glow = layer.filter(ImageFilter.GaussianBlur(10))
    paste_rgba(img, glow, (int(cx - box / 2), int(cy - box / 2)), opacity * .9)
    paste_rgba(img, layer, (int(cx - box / 2), int(cy - box / 2)), opacity)


def np_card(sc, t_rel, w_card=None):
    w = w_card or NP_W
    h = 96
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    m = rounded_mask(w, h, 22)
    bg = Image.new("RGBA", (w, h), (24, 24, 26, 238))
    im.paste(bg, (0, 0), m)
    th = cover(PHOTOS[sc["k"]], 68, 68, 1.0, sc["fx"], sc["fy"])
    im.paste(th, (14, 14), rounded_mask(68, 68, 12))
    d = ImageDraw.Draw(im)
    d.text((98, 18), sc["label"], font=font(24, "Bold"), fill=(255, 255, 255, 255))
    d.text((98, 48), "Spotify", font=font(17, "Medium"), fill=(170, 170, 175, 255))
    bx0, bx1, by = 98, w - 70, 78
    d.rounded_rectangle((bx0, by, bx1, by + 4), 2, fill=(80, 80, 84, 255))
    prog = eio(clamp(t_rel / 2.4)) * 0.8 + 0.08
    d.rounded_rectangle((bx0, by, bx0 + (bx1 - bx0) * prog, by + 4), 2, fill=GREEN + (255,))
    d.ellipse((bx0 + (bx1 - bx0) * prog - 5, by - 3, bx0 + (bx1 - bx0) * prog + 5, by + 7), fill=(255, 255, 255, 255))
    cx_, cy_ = w - 36, 40
    d.ellipse((cx_ - 20, cy_ - 20, cx_ + 20, cy_ + 20), fill=GREEN + (255,))
    d.polygon([(cx_ - 6, cy_ - 10), (cx_ - 6, cy_ + 10), (cx_ + 11, cy_)], fill=(10, 10, 10, 255))
    return im


def draw_eq(img, x, y, wtot, hmax, t, opacity=1.0):
    n = 18
    bw = wtot / n
    layer = Image.new("RGBA", (int(wtot) + 4, int(hmax) + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(n):
        v = .5 + .5 * math.sin(t * (7 + i * .9) + i * 1.7) * (.6 + .4 * math.sin(t * 3 + i))
        v = clamp(v * (.55 + .45 * pulse(t)), .08, 1)
        hh = hmax * v
        d.rounded_rectangle((i * bw + 2, hmax - hh + 2, i * bw + bw - 4, hmax + 2), 4, fill=GREEN + (255,))
    paste_rgba(img, layer, (int(x), int(y)), opacity)


def draw_streaks(img, t, opacity=1.0):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rs = np.random.default_rng(3)
    for i in range(34):
        y = rs.uniform(0, H)
        L = rs.uniform(120, 420)
        sp = rs.uniform(900, 2200)
        x = ((t * sp + rs.uniform(0, W + 600)) % (W + 600)) - 300
        a = int(rs.uniform(70, 170) * opacity)
        col = GREEN if i % 3 else (255, 255, 255)
        d.line((x, y, x + L, y), fill=col + (a,), width=2)
    img.paste(layer.convert("RGB"), (0, 0), layer.getchannel("A"))


def draw_card(img, sc, t, tr, vis):
    """Photo card with the scene's own entrance move."""
    k = sc["k"]
    mv = sc["move"]
    scale_push = 1.0 + (0.18 * clamp(tr / 2.5) if mv == "push" else 0.06 * clamp(tr / 2.5))
    ph = cover(PHOTOS[k], CARD_W, CARD_H, scale_push * sc.get("zoom", 1.0), sc["fx"], sc["fy"])
    if sc["dark"]:
        ph = Image.eval(ph, lambda v: min(255, int(v * 1.25)))
    card = Image.new("RGBA", (CARD_W, CARD_H))
    card.paste(ph, (0, 0))
    card.putalpha(CARD_MASK)
    cx, cy = CARD_C
    p_in = clamp(tr / 0.5)
    sx = sy = 1.0
    op = vis
    if mv == "flip":
        ang = (1 - eo5(p_in)) * 1.3
        sx = max(0.02, math.cos(ang))
        sy = 1 - 0.07 * math.sin(ang)
    elif mv == "whip":
        cx += int((1 - eo5(p_in)) * (W * .9))
    elif mv == "push":
        sc_ = 1.1 - .1 * eo3(p_in)
        sx = sy = sc_
        op *= eo3(p_in * 1.4)
    elif mv == "rise":
        cy += int((1 - eo5(p_in)) * H * .6)
    # exit
    pe = clamp((tr - (sc["t1"] - sc["t0"] - 0.25)) / 0.25)
    op *= 1 - eio(pe)
    cx_off = -int(eio(pe) * 40)
    w2, h2 = max(2, int(CARD_W * sx)), max(2, int(CARD_H * sy))
    card = card.resize((w2, h2), Image.BILINEAR)
    # rim light
    rim = Image.new("RGBA", (w2 + 60, h2 + 60), (0, 0, 0, 0))
    ImageDraw.Draw(rim).rounded_rectangle((30, 30, 30 + w2, 30 + h2), 28, outline=GREEN + (200,), width=3)
    rim_g = rim.filter(ImageFilter.GaussianBlur(14))
    pos = (int(cx - w2 / 2 + cx_off), int(cy - h2 / 2))
    paste_rgba(img, rim_g, (pos[0] - 30, pos[1] - 30), op * .8)
    paste_rgba(img, card, pos, op)
    paste_rgba(img, rim, (pos[0] - 30, pos[1] - 30), op * .6)
    if mv == "whip":
        draw_eq(img, TXT_X, TXT_Y + 90 if not PORTRAIT else TXT_Y + 120, 300, 54, t, op * eo3((tr - .3) / .4))


def scene_layer(img, sc, t):
    tr = t - sc["t0"]
    dur = sc["t1"] - sc["t0"]
    if tr < -0.05 or t > sc["t1"] + 0.02:
        return
    vis = 1.0
    if sc["move"] == "rise":
        draw_streaks(img, t, eo3(tr / .4) * (1 - eio(clamp((tr - (dur - .25)) / .25))))
    draw_card(img, sc, t, tr, vis)
    pe = clamp((tr - (dur - 0.25)) / 0.25)
    to = 1 - eio(pe)
    big_sz = 62 if not PORTRAIT else 92
    sweep_text(img, sc["small"], 24 if not PORTRAIT else 28, (TXT_X, TXT_Y - 70),
               tr - .15, color=(150, 150, 156), weight="Medium", dur=.4, opacity=to)
    sweep_text(img, sc["big"], big_sz, (TXT_X, TXT_Y), tr - .05, dur=.6, opacity=to)
    if tr > .35:
        npc = np_card(sc, tr - .35)
        slide = eo5((tr - .35) / .45)
        pos = (NP_POS[0] - int((1 - slide) * 200), NP_POS[1] + (int(eo3(pe) * 20) if True else 0))
        paste_rgba(img, npc, pos, to * clamp(slide * 2))


def fan_scene(img, t):
    tr = t - 13.5
    if tr < 0 or t > 16.0:
        return
    p_fan = eo5(tr / 1.0)
    p_col = eio((tr - 1.7) / 0.8)
    tx_op = 1 - eio((tr - 1.7) / .4)
    sz = 34 if not PORTRAIT else 48
    ty = 235 if not PORTRAIT else 330
    sweep_text(img, "Whatever's next,", sz + 20, (CX, ty), tr - .2, anchor="c", dur=.6, opacity=tx_op)
    sweep_text(img, "there's a song for it.", sz + 20, (CX, ty + (74 if not PORTRAIT else 100)), tr - .75, anchor="c", dur=.7, opacity=tx_op)
    tw, th = (170, 220) if not PORTRAIT else (210, 280)
    fy = 500 if not PORTRAIT else 840
    for i, sc in enumerate(SCENES):
        ph = cover(PHOTOS[sc["k"]], tw, th, 1.0, sc["fx"], sc["fy"])
        c = Image.new("RGBA", (tw, th))
        c.paste(ph, (0, 0))
        c.putalpha(rounded_mask(tw, th, 20))
        off = (i - 1.5)
        ang = -off * 9 * p_fan
        x = CX + off * (200 if not PORTRAIT else 170) * p_fan
        y = fy + abs(off) * 22 * p_fan + (1 - p_fan) * 260
        # collapse to ring centre
        x = x + (CX - x) * p_col
        y = y + (CY - y) * p_col
        s = 1 - .9 * p_col
        c2 = c.resize((max(2, int(tw * s)), max(2, int(th * s))), Image.BILINEAR).rotate(ang, expand=True, resample=Image.BICUBIC)
        paste_rgba(img, c2, (int(x - c2.width / 2), int(y - c2.height / 2)), clamp(p_fan * 2) * (1 - clamp((p_col - .75) * 4)))


def logo_scene(img, t):
    tr = t - 16.0
    if tr < 0 or t > 18.0:
        return
    # ring collapses onto the icon position, then the logo is written in
    p = eo5(tr / .5)
    cx = CX + (ICON_C[0] - CX) * p
    R = (150 * (1 - p) + LOGO_ICON_D * .5 * p)
    if tr < .55:
        ring(img, cx, CY, R, t, amp=(1 - p), width=5, opacity=1 - clamp((tr - .35) / .2))
    pl = eo3((tr - .3) / .7)
    if pl > 0:
        lw, lh = LOGO_FULL.size
        k = .92 + .08 * pl
        l2 = LOGO_FULL.resize((int(lw * k), int(lh * k)), Image.LANCZOS)
        a = np.asarray(l2.getchannel("A"), dtype=np.float32)
        xs = np.arange(l2.width, dtype=np.float32)[None, :]
        edge = pl * (l2.width + 80) - 40
        wipe = np.clip((edge - xs) / 40, 0, 1)
        l2.putalpha(Image.fromarray((a * wipe).astype(np.uint8)))
        # bloom
        bl = l2.filter(ImageFilter.GaussianBlur(24))
        pos = (CX - l2.width // 2, CY - l2.height // 2)
        paste_rgba(img, bl, pos, .8 * (1 - clamp((tr - 1) / 1.0) * .5))
        paste_rgba(img, l2, pos, 1.0)


def end_card(img, t):
    tr = t - 18.0
    if tr < 0:
        return
    # logo fades out, card writes in
    sweep_text(img, "made by", 30 if not PORTRAIT else 38, (CX, CY - 40), tr - .15, color=(150, 150, 156),
               weight="Medium", anchor="c", dur=.5)
    sweep_text(img, "riccardo bosso", 76 if not PORTRAIT else 74, (CX, CY + 22), tr - .35, anchor="c", dur=.8)


def frame(t):
    # global transitions (colour)
    warm = 0.0
    if 8.5 <= t < 11.0:
        warm = eio((t - 8.5) / .6) * (1 - eio((t - 10.6) / .5))
    boost = 0.0
    if t >= 16.0:
        boost = math.exp(-(t - 16.0) * 1.1) * 1.4
    arr = background(t, warm, boost)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    # 0-1 s : dot
    if t < 1.2:
        p = clamp(t / 1.0)
        r = 4 + 6 * eo3(p) + 14 * pulse(t) * (1 if t > .4 else 0)
        glow = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((100 - r, 100 - r, 100 + r, 100 + r), fill=GREEN + (255,))
        paste_rgba(img, glow.filter(ImageFilter.GaussianBlur(14)), (CX - 100, CY - 100), eo3(p))
        paste_rgba(img, glow, (CX - 100, CY - 100), eo3(p))
    # 1-3.5 s : ring + title
    if 1.0 <= t < 3.7:
        tr = t - 1.0
        Rr = (30 + 120 * eo5(tr / .6)) if t < 3.2 else 150 * (1 - eio((t - 3.2) / .5)) + 30
        ring(img, CX, CY - (105 if not PORTRAIT else 150), Rr * .85, t, amp=1.0, opacity=1 - eio((t - 3.3) / .4))
        o = 1 - eio((t - 3.2) / .35)
        sz = 70 if not PORTRAIT else 88
        sweep_text(img, "Every moment", sz, (CX, CY + (120 if not PORTRAIT else 120)), tr - .2, anchor="c", dur=.7, opacity=o)
        sweep_text(img, "has a sound.", sz, (CX, CY + (200 if not PORTRAIT else 230)), tr - .75, anchor="c", dur=.7, opacity=o)
    for sc in SCENES:
        scene_layer(img, sc, t)
    fan_scene(img, t)
    logo_scene(img, t)
    if t >= 18.0:
        end_card(img, t)

    a = np.asarray(img, dtype=np.float32) * VIG
    # fade logo into end card: dip handled by timing; add gentle flash at 16.0
    if 16.0 <= t < 16.2:
        a += (1 - (t - 16.0) / .2) * 38
    return a


def render(i):
    t0 = i / FPS
    acc = None
    for s in range(SUB):
        t = t0 + ((s + .5) / SUB - .5) * SHUTTER / FPS
        f = frame(max(0, t))
        acc = f if acc is None else acc + f
    return np.clip(acc / SUB, 0, 255).astype(np.uint8)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "still":
        times = [float(x) for x in sys.argv[3:]]
        for t in times:
            Image.fromarray(render(int(t * FPS))).save(f"{sys.argv[2]}_{t:05.2f}.png")
    elif mode == "video":
        out = sys.argv[2]
        total = int(DUR * FPS)
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", out]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for n, fr in enumerate(pool.imap(render, range(total), chunksize=4)):
                p.stdin.write(fr.tobytes())
                if n % 120 == 0:
                    print("frame", n, flush=True)
        p.stdin.close()
        p.wait()
