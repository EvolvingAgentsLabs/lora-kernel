# `video/` — the demo video, as source

`demo-escuela/index.html` is a [HyperFrames](https://github.com/heygen-com/hyperframes) composition: HTML, CSS and one paused
GSAP timeline, rendered frame by frame to `docs/video/demo-escuela.mp4` (1920×1080, 30 fps, 76 s). **Nothing on screen is
re-enacted:** every request, tool call, reply, latency and count is copied from
[`results/DEMO-school-diagram-20260926/demo_school.json`](../results/DEMO-school-diagram-20260926/BRIEF.md) — 15/15 on Gemma 4
E4B + `school-s0`. Rendering runs no model; it runs headless Chrome and ffmpeg, so it is fine on the user's machine.

```bash
cd video/demo-escuela
npx --yes hyperframes@0.8.79 lint                      # 0 errors
npx --yes hyperframes@0.8.79 snapshot --at 5,24.5,34,52,67
npx --yes hyperframes@0.8.79 render --fps 30 --crf 28 -o ../../docs/video/demo-escuela.mp4
# the README preview: five moments, 960 px, 8 fps
ffmpeg -y -i ../../docs/video/demo-escuela.mp4 -filter_complex "[0:v]trim=4:6.5,setpts=PTS-STARTPTS[a];[0:v]trim=22.5:25,setpts=PTS-STARTPTS[b];[0:v]trim=32:34.5,setpts=PTS-STARTPTS[c];[0:v]trim=49:51.5,setpts=PTS-STARTPTS[d];[0:v]trim=63:66,setpts=PTS-STARTPTS[e];[a][b][c][d][e]concat=n=5:v=1,fps=8,scale=960:-1:flags=lanczos,split[x][y];[x]palettegen=max_colors=96[p];[y][p]paletteuse=dither=bayer:bayer_scale=4" ../../docs/img/demo-escuela-preview.gif
```

When the demo is re-run, the numbers in `index.html` are re-copied from the new record — they are not computed at render
time, on purpose: a render must be reproducible from the file alone.

## `demo-tracker/` — the team tracker, multi-turn, on a laptop

`demo-tracker/index.html` is the same kind of composition in the same house style, rendered to
`docs/video/demo-tracker.mp4` (1920×1080, 30 fps, 76 s, in Spanish). It shows the team tracker (Jira + Confluence-like,
synthetic) served by Gemma 4 E4B Q8_0 + `tr-s1` on llama.cpp on the user's Mac, driven by OpenClaw, with the operational
memory on and the tool block off — three sessions, one per role, each turn with its request, the calls the gateway ran
(the `get`/`put` on the memory included) and the reply. **Nothing on screen is re-enacted:** every request, call, reply,
latency, token count and state is copied from
[`results/LIVE-tracker-openclaw-20260930/`](../results/LIVE-tracker-openclaw-20260930/BRIEF.md) (`live.json`,
`events.jsonl`: 14/14, dependent 8/8); long results and replies are cut at a word and marked `…`, never reworded. The
counters are the BRIEF's Result (gateway latency median 3.7 s, prompt tokens median 371); the closing card's rate is H3's
([`results/H3-tracker-corpus-v2-20260929/`](../results/H3-tracker-corpus-v2-20260929/BRIEF.md): 158/160 with the block,
156/160 block-less). The events do not log the memory line itself, so the video shows only its shape
(`state: … · keys: …`, `examples/common/opmemory.context_line`) and the `get`/`put` calls that ran.

```bash
cd video/demo-tracker
npx --yes hyperframes@0.8.79 lint                      # 0 errors
npx --yes hyperframes@0.8.79 snapshot --at 5,14,29,43,74
npx --yes hyperframes@0.8.79 render --fps 30 --crf 28 -o ../../docs/video/demo-tracker.mp4
# the preview: five moments, 960 px, 8 fps; the poster: the developer session at 43 s, 1280 px
ffmpeg -y -i ../../docs/video/demo-tracker.mp4 -filter_complex "[0:v]trim=4:6.5,setpts=PTS-STARTPTS[a];[0:v]trim=12:14.5,setpts=PTS-STARTPTS[b];[0:v]trim=27:29.5,setpts=PTS-STARTPTS[c];[0:v]trim=41:43.5,setpts=PTS-STARTPTS[d];[0:v]trim=60:63,setpts=PTS-STARTPTS[e];[a][b][c][d][e]concat=n=5:v=1,fps=8,scale=960:-1:flags=lanczos,split[x][y];[x]palettegen=max_colors=96[p];[y][p]paletteuse=dither=bayer:bayer_scale=4" ../../docs/img/demo-tracker-preview.gif
ffmpeg -y -ss 43 -i ../../docs/video/demo-tracker.mp4 -frames:v 1 -vf scale=1280:-1:flags=lanczos ../../docs/img/demo-tracker-poster.png
```
