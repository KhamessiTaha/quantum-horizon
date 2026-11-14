# Quantum Horizon

A blink comparator for SPHEREx. Enter a target or coordinates; the tool finds every SPHEREx exposure covering that
position, aligns them, plays them as a time sequence, and measures what moved or changed — with an uncertainty and an
honest label on every number. Built for NASA Space Apps 2026, challenge "Planet X and SPHEREx".

## Layout

- `backend/` — FastAPI + astropy. `app/view.py` prepares and caches the aligned frame cube; every endpoint works from
  it. `app/pipeline.py` builds the viewer payload and the measurements, `app/measure.py` does the astrometry and
  photometry, `app/analysis.py` the spectra and light curves, `app/movers.py` the mover search, `app/flags.py` the
  SPHEREx quality flags, `app/catalog.py` Gaia DR3.
- `src/` — React + TypeScript + Vite. `src/pages/Viewer.tsx` is the tool; `src/lib/viewState.ts` keeps every setting in
  the URL so any view can be shared or embedded.
- `research/` — the spike scripts from the research phase. Not part of the product, kept for provenance.
- `backend/cache/regions` — real SPHEREx pixels, committed on purpose: the demo works with IRSA down.

## Rules

- Never invent a measurement. Every number comes from the data, carries an uncertainty, and gets a confidence label:
  measured, marginal, below-noise, not-measurable or indicative. When the data cannot answer, the tool says so.
- Flags decide what is usable. `app/flags.py` splits them four ways and the reason is in that file's docstring: a
  bright star's own pixels carry TRANSIENT, OVERFLOW, SUR_ERROR, SOURCE and BLOOM, so rejecting those deletes the star.
- Catalog positions must be propagated to each observation date. SIMBAD coordinates are J2000, Gaia DR3 is J2016.0,
  and Barnard's Star has moved arcminutes since.
- Keep the look: dark ground `#0a0c0f`, IBM Plex Sans and Mono, cyan `#5cc8ff` for measured values, amber `#f2a541`
  for catalog predictions. Tokens live in `src/index.css`.
- Small components with CSS modules; no new dependencies without a reason.
- Windows work laptop: if `npm` or `pip.exe` is blocked, say so instead of working around security policy. Use
  `.venv\Scripts\python -m pip`.
- User preferences: short answers, one step at a time, say where to run each command, no inline comments.

## Running it

Backend, from `backend/`:

```
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

Frontend, from the repo root: `npm install` then `npm run dev`, with `VITE_API_BASE` pointing at the backend
(defaults to `http://localhost:8000`).

Warm the demo targets before any demo: `.venv\Scripts\python scripts/prewarm.py` from `backend/`.

## Open work

See `HANDOFF.md` for the current state and the remaining steps in order: commit the warm cache, split into the two
deploy repositories, deploy to Fly and Vercel, record the demo, submit.
