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
