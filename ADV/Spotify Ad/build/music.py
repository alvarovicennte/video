import numpy as np, wave, sys

SR = 48000
BPM = 120
BEAT = 60 / BPM
DUR = 20.0
N = int(SR * DUR)
rng = np.random.default_rng(7)


def hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def tone(freq, dur, harm=(1, .5, .25, .12), detune=0.0):
    n = int(SR * dur)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for i, a in enumerate(harm, 1):
        y += a * np.sin(2 * np.pi * freq * i * t)
        if detune:
            y += a * 0.6 * np.sin(2 * np.pi * freq * i * (1 + detune) * t + 1.3)
    return y


mix = np.zeros((2, N))


def add(sig, t0, pan=0.0, gain=1.0):
    i = int(t0 * SR)
    if i >= N:
        return
    sig = sig[: N - i]
    l = gain * (1 - max(pan, 0))
    r = gain * (1 + min(pan, 0))
    mix[0, i:i + len(sig)] += sig * l
    mix[1, i:i + len(sig)] += sig * r


# A minor -> C major lift. MIDI notes per bar (9 ad bars + 1 end bar)
am = dict(root=45, chord=[57, 60, 64, 69], arp=[69, 72, 76, 81])
f = dict(root=41, chord=[53, 57, 60, 65], arp=[65, 69, 72, 77])
c = dict(root=48, chord=[55, 60, 64, 67], arp=[67, 72, 76, 79])
g = dict(root=43, chord=[55, 59, 62, 67], arp=[67, 71, 74, 79])
bars = [am, am, f, c, g, am, f, g, c, c]
bar_len = 4 * BEAT

for b, ch in enumerate(bars):
    t0 = b * bar_len
    last = b >= 8
    # pad
    dur = bar_len * (2.6 if b == 9 else 1.05) if last else bar_len * 1.05
    if b == 8:
        dur = bar_len * 2.2
    for k, nn in enumerate(ch["chord"]):
        pad = tone(hz(nn), dur, harm=(1, .4, .2, .1), detune=0.004)
        e = np.minimum(1, np.arange(len(pad)) / (0.5 * SR)) * np.exp(-np.arange(len(pad)) / (dur * SR) * (0.4 if last else 1.2))
        add(pad * e * 0.045, t0, pan=(-1) ** k * 0.35)
    # bass on 8ths from bar 1
    if b >= 1:
        for s in range(8):
            if b >= 9 and s > 0:
                break
            nn = ch["root"] if s % 4 != 3 else ch["root"] + 12
            sig = tone(hz(nn), BEAT * 0.5, harm=(1, .35)) * env_exp(int(SR * BEAT * .5), 0.18)
            add(sig * 0.22, t0 + s * BEAT / 2)
    elif b == 0:
        sub = tone(hz(33), bar_len, harm=(1,)) * np.minimum(1, np.arange(int(SR * bar_len)) / (SR * 2))
        add(sub * 0.25, 0)
    # arp 16ths from bar 2
    if 1 <= b <= 8:
        pat = [0, 1, 2, 3, 2, 1, 2, 3]
        for s in range(16):
            nn = ch["arp"][pat[s % 8]]
            sig = tone(hz(nn), 0.35, harm=(1, .5, .3, .15)) * env_exp(int(SR * .35), 0.09)
            vel = 0.5 + 0.5 * (s % 4 == 0)
            if b == 1:
                vel *= 0.6
            add(sig * 0.07 * vel, t0 + s * BEAT / 4, pan=0.3 * np.sin(s))
    # kick on beats from bar 2 (bars 2..8)
    if 1 <= b <= 8:
        for s in range(4):
            n = int(SR * 0.28)
            t = np.arange(n) / SR
            fr = 48 + 90 * np.exp(-t * 28)
            k = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 11)
            add(k * 0.55, t0 + s * BEAT)
    # soft clap on 2 and 4 from bar 4
    if 3 <= b <= 7:
        for s in (1, 3):
            n = int(SR * 0.18)
            nz = rng.standard_normal(n)
            nz = nz - np.convolve(nz, np.ones(24) / 24, mode="same")
            add(nz * env_exp(n, 0.035) * 0.12, t0 + s * BEAT)
    # hats from bar 3
    if 2 <= b <= 7:
        for s in range(8):
            n = int(SR * 0.05)
            nz = rng.standard_normal(n)
            nz = nz - np.convolve(nz, np.ones(8) / 8, mode="same")
            add(nz * env_exp(n, 0.012) * (0.06 if s % 2 else 0.035), t0 + s * BEAT / 2 + BEAT / 4, pan=0.4)

# riser into "Whatever's next" (bars 6-7, 12-14s) and drop before logo
rs, re = 13.5, 15.9
n = int(SR * (re - rs))
t = np.arange(n) / SR
nz = rng.standard_normal(n)
sm = np.convolve(nz, np.ones(6) / 6, mode="same")
rise = sm * (t / t[-1]) ** 2.2 * 0.16
add(rise, rs)
# gap before logo hit
gs, ge = 15.9, 16.0
mix[:, int(gs * SR):int(ge * SR)] *= np.linspace(1, 0.25, int(ge * SR) - int(gs * SR))
# logo impact + shimmer at 16.0
n = int(SR * 1.2)
t = np.arange(n) / SR
imp = np.sin(2 * np.pi * np.cumsum(40 + 80 * np.exp(-t * 20)) / SR) * np.exp(-t * 5)
add(imp * 0.5, 16.0)
for i, nn in enumerate([84, 88, 91, 95, 98]):
    sh = tone(hz(nn), 2.4, harm=(1, .3)) * env_exp(int(SR * 2.4), 0.8)
    add(sh * 0.035, 16.02 + i * 0.07, pan=(-1) ** i * 0.5)
# last chord C add9 swell at 16.0 held through end card
for k, nn in enumerate([48, 55, 60, 64, 67, 74]):
    d = DUR - 16.0
    ch = tone(hz(nn), d, harm=(1, .45, .22, .1), detune=0.003)
    e = np.minimum(1, np.arange(len(ch)) / (0.08 * SR)) * np.exp(-np.arange(len(ch)) / (SR * 7))
    add(ch * e * 0.06, 16.0, pan=(-1) ** k * 0.4)

# simple tail + fade
tail = np.zeros_like(mix)
for d, g_ in ((0.23, .28), (0.41, .2), (0.67, .12)):
    k = int(d * SR)
    tail[:, k:] += mix[:, :-k] * g_
mix += tail * 0.7
fade = np.ones(N)
fo = int(SR * 0.6)
fade[-fo:] = np.linspace(1, 0, fo)
mix *= fade
mix /= max(1e-9, np.abs(mix).max()) / 0.7

out = (mix.T * 32767).astype(np.int16)
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(out.tobytes())
print("ok", mix.shape)
