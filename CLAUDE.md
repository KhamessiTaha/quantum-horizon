# qh-practice — context

Throwaway rehearsal of the Quantum Horizon frontend for NASA Space Apps 2026. It is not the submission repo: the real app is built from scratch in `quantum-horizon` from November 14, unless the rules published on November 13 allow pre-event code.

## Rules for this folder

- Placeholders only: show "—" or "Awaiting data", never invented measurements or fake SPHEREx images.
- Keep the look from the mockup: dark ground #0A0C0F, IBM Plex Sans and Mono, cyan #5CC8FF for measured values and the accent, amber #F2A541 for catalog predictions. Tokens live in `src/index.css`.
- View state belongs in the URL (`src/lib/viewState.ts`): target or ra/dec, fov, det, mode.
- Small components with CSS modules; no new dependencies without a reason.
- Windows work laptop: if `npm` or `pip.exe` is blocked, say so instead of working around security policy.
- User preferences: short answers, one step at a time, say where to run each command, no inline comments.

## Good practice tasks

- Rehearse a deploy to Vercel from a private practice GitHub repo.
- Add an Aladin Lite v3 context map to the viewer, loaded from its CDN, to learn its API.
- Keyboard controls on the player (space to play or pause, arrows to step), scoped to the player element.
- A loading and error state for the viewer, so the real backend can drop in later.
