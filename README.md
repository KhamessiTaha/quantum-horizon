# qh-practice

Practice scaffold for the Quantum Horizon frontend: placeholder screens only, no data. It exists to rehearse the setup before NASA Space Apps 2026. It is not the submission repo.

## Run

Requires Node 20 or newer.

```
npm install
npm run dev
```

Open the address it prints (usually http://localhost:5173).

Other scripts: `npm run build` (type-check and production build), `npm run lint`, `npm run preview`.

## What is here

- `/` landing page: pitch, search, five featured targets, how it works.
- `/view` viewer: blink and difference modes, detector chips, field of view, play controls, timeline, findings panel, copy link and embed.
- View state lives in the URL, for example `/view?target=Barnard's+Star&fov=0.06&det=D2&mode=blink` or `/view?ra=269.4463&dec=4.7682`.
- Every value shown is a placeholder ("—", "Awaiting data") until a backend supplies real frames and measurements.

## Layout

```
src/
  index.css               colour and type tokens, shared button styles
  lib/viewState.ts        URL state: parse, serialise, validate
  data/featuredTargets.ts the five challenge targets
  components/             Header, SearchBox, Badge
  components/viewer/      Player, Timeline, FindingsPanel, ShareButtons
  pages/                  Landing, Viewer
```
