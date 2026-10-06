# Spotify spec ad: BRIEF v1 (nothing built, no credits spent)

Format: 16:9 + 9:16, 60 fps. ~18 s ad + ~2 s end card = ~20 s. Master -14 LUFS / -1 dBTP.
Tempo: 120 BPM, 10 bars total (9 ad + 1 end card). Every cut and hit lands on the grid, then gets re-timed to the final voice.

## 1. Three ideas (my pick: A)

**A. "Every moment has a sound" (recommended).** One play button is the whole ad. It lives on a dark stage with a drifting green glow and morphs through four moments of a day (6 a.m. alarm, the run, the late-night work, the ride home). Each moment gets a real photo, a real now-playing card and a waveform that changes shape. It's the Spotify/Huel/Shopify rhythm: big kinetic type, one idea, one product.

**B. "Skip".** Comedy. Life keeps getting skipped to the next track: a bad morning, a bad meeting. Funny, but it leans on UI gags and is harder to make feel premium.

**C. "Four minutes".** A single song as a timeline, with the stage filling with the life that happened during it. Emotional, but needs more photos and it's slower, so it risks missing 18 s.

## 2. Concept (A)
Message: whatever you're doing, there's a song for it. Spotify = music for every moment.
Look: near-black stage (#0B0B0C), soft Spotify-green glow (#1DB954) drifting behind everything, SF Pro Display, heavy motion blur, a motion-graphics layer (waveform rings, EQ bars, orbiting dots, light sweeps) so no frame sits still.
New moves (not recycled): (1) the play button splits into a waveform ring that "breathes" with the VO; (2) type that is drawn by a sweeping light, not faded in; (3) photos enter as rounded cards flipping on a z-axis with a green rim light; (4) a now-playing card that scrubs its progress bar to the beat; (5) a logo reveal where the ring collapses into the Spotify mark.

## 3. Script (VO, ~30 words, English)
> Every moment has a sound.
> The 6 a.m. alarm.
> The long run.
> The one-more-hour.
> The ride home.
> Whatever's next, there's a song for it.
> Spotify.

Pronunciation: respell the brand for ElevenLabs, e.g. "Spot-ih-fye" (test on the 2 takes; pick the one that sounds natural).

## 4. Beat sheet (timings are provisional; locked to the real VO later)
| Time | Visual | VO | Sound |
|---|---|---|---|
| 0.0-1.0 | Black. Green glow drifts in. A single dot pulses once. | | sub swell, soft tick |
| 1.0-3.5 | Dot opens into the waveform ring. "Every moment has a sound." drawn by a light sweep, word by word, blur-in | "Every moment has a sound." | whoosh per word, hit on "sound" |
| 3.5-6.0 | Z-flip to photo 1 (window at sunrise). Now-playing card slides in. "6 a.m." in giant type | "The 6 a.m. alarm." | whoosh, card slide, tick on 6 |
| 6.0-8.5 | Whip-pan to photo 2 (runner). EQ bars sprint, progress bar scrubs | "The long run." | whoosh, bar riser |
| 8.5-11.0 | Photo 3 (desk lamp at night). Slow push-in, glow dims warm | "The one-more-hour." | low whoosh, soft hit |
| 11.0-13.5 | Photo 4 (night ride). Speed lines made of the glow | "The ride home." | whoosh, doppler pass |
| 13.5-16.0 | All four cards fan out and fold into the ring. "Whatever's next, there's a song for it." | "Whatever's next, there's a song for it." | riser, then silence-ish dip |
| 16.0-18.0 | Ring collapses into the Spotify logo, glow blooms | "Spotify." | impact, shimmer tail, last chord |
| 18.0-20.0 | End card v2: animated "made by / riccardo bosso" | | last chord rings under it |

## 5. Voice
ElevenLabs, voices to audition: Jessica / Lauren / Siren (or I show other options).
Credit estimate: ~190 characters x 2 takes in one call = ~380-400 credits (confirm exact figure and model before spending).
I will show the options and wait for your pick before the final take.

## 6. Music (original, made in code)
120 BPM, minor-to-major lift (A minor, resolving to C major on the logo). Soft pulse bass + plucked arp + warm pad, a build under "Whatever's next", and a held chord on the logo that rings into the end card. Sidechained under the VO, at least 15 dB below it whenever words are spoken. No limiter on the voice.

## 7. SFX plan (only from your library)
Source: `/Volumes/Extreme Pro/EDITING PACK/FOUR Editors Sound Effects`, copied into `assets_in/sfx/` early.
- Whoosh into every word/title and every photo change
- Hit on every landing (words, cards, "6 a.m.")
- UI ticks/clicks on every product move (card slide, progress scrub)
- Riser into "Whatever's next", impact + shimmer on the logo
- Placed and EQ'd per scene; nothing removed, just balanced under the voice.

## 8. Assets list (awaiting your OK before any download)
- **Logo:** official Spotify logo from the brand/press kit (SVG, green + white).
- **Product:** real now-playing card and play-button renders from the Spotify press kit; facts checked on spotify.com before use (I'll avoid numbers/claims unless verified).
- **Photos (photoreal, Unsplash/Pexels):** 1) sunrise window / bedroom, 2) runner at dawn, 3) desk lamp at night, 4) night city ride. Every source + licence logged in `assets_in/CREDITS.md`.
- **Font:** SF Pro Display.
- **End card:** "Spotify end card v2" (made by / riccardo bosso). Please tell me where the file/project lives.
- **Avoid:** no phone-in-hand clichés, no cartoon placeholders, nothing from the previous ad's moves.

## 9. Deliverables
Preview v1 (16:9) + contact sheet, then finals 16:9 + 9:16, stems (VO / music / SFX), README. Resolve project only if you ask (60 fps playback reminder included).

---
**Heads up on this environment:** I'm running in a cloud container, not your Mac. `/Volumes/Extreme Pro` (the SFX SSD) and `~/Desktop` don't exist here, so this brief lives at `ADV/Spotify Ad/brief/PROMPT.md` in the repo. Before the build step, either run this on your machine, or upload the SFX pack here.
