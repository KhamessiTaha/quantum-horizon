# Handoff

Everything the local session needs to finish Quantum Horizon. Read `CLAUDE.md` first for the project's rules; this
file is the current state and the remaining work, in order.

## Where it stands, 14 November

The tool is built, tested and measuring real data. 27 backend tests pass. All five challenge targets have been run
against live IRSA, S3, SIMBAD and Gaia:

| Target | Detector | Frames | Passes | Measured | Catalog |
|---|---|---|---|---|---|
| Barnard's Star | D2 | 61 | 3 | 9.71 ± 1.57″ | 10.28″ |
| Barnard's Star | D1 | 60 | 3 | 10.31 ± 1.08″ | 10.08″ |
| Epsilon Indi B | D5 | 84 | 5 | 6.57 ± 0.62″ | 6.69″ |
| WISE 0855 | D6 | 45 | 3 | 11.27 ± 2.97″ | 7.97″ |
| RW Aurigae | D1 | 56 | 3 | 0.36 ± 0.62″ | 0.02″ |
| R Draconis | D1 | 53 | 7 | 6.50 ± 8.95″ | 0.03″ |

What remains is packaging, not building.

## 1. Commit the warm cache first

`scripts/prewarm.py` filled `backend/cache/regions` with real pixels for every target. Those are tracked on purpose:
they make the demo instant and keep it working if IRSA goes down mid-judging. The derived folders (`cubes`, `views`,
`images`) are ignored because they rebuild in under a second.

```powershell
cd C:\Users\SETUP\Desktop\quantum-horizon
git add backend/cache
git status --short | measure   # expect a few hundred region files, roughly 10-25 MB
git commit -m "Warm cache for all five challenge targets"
git push
```

If that is much larger than ~40 MB, stop and ask before pushing.

## 2. Split into deploy repositories

Keep `KhamessiTaha/quantum-horizon` as the public repository judges open: it holds the whole project, the history and
the research. The two new repositories exist only so Vercel and Fly each build from a root.

Create two empty repositories on GitHub first: `quantum-horizon-api` and `quantum-horizon-web`. Then, from the
monorepo:

```powershell
# API: backend/ becomes the root, with its history
git subtree split --prefix=backend -b backend-only
git clone . ..\quantum-horizon-api -b backend-only
cd ..\quantum-horizon-api
git checkout -b main
```

In that new folder, replace `.gitignore` with the same rules written for a root-level backend:

```
.venv/
__pycache__/
*.pyc
.DS_Store
Thumbs.db
cache/cubes/
cache/views/
cache/images/
```

Then:

```powershell
git rm -r --cached cache/cubes cache/views cache/images
git add -A
git commit -m "Backend as its own repository"
git remote set-url origin https://github.com/KhamessiTaha/quantum-horizon-api.git
git push -u origin main
```

```powershell
# Web: everything except the backend and the research spikes
cd C:\Users\SETUP\Desktop\quantum-horizon
git clone . ..\quantum-horizon-web -b main
cd ..\quantum-horizon-web
git rm -r backend research dist
git commit -m "Frontend as its own repository"
git remote set-url origin https://github.com/KhamessiTaha/quantum-horizon-web.git
git push -u origin main
```

Both halves were verified to build standalone: the backend's 27 tests pass from its own root, and the frontend builds
clean with `npm run build`.

**After this, work in the monorepo and re-split when something changes**, or pick one repository per half and keep the
monorepo as an archive. Do not try to keep three repositories edited by hand.

## 3. Deploy the backend to Fly

From the API repository root (`fly.toml` and `Dockerfile` are already there):

```powershell
fly auth login
fly launch --no-deploy --copy-config --name quantum-horizon-api --region iad
fly volumes create qh_cache --size 3 --region iad
fly deploy
fly open /api/health
```

The Dockerfile bakes `cache/` into the image and `scripts/entrypoint.sh` copies it onto the volume on first boot, so
the deployed API is warm from the first request. Watch the first boot log for `cache seeded from the image`.

Once the frontend is deployed, allow its origin:

```powershell
fly secrets set QH_ALLOWED_ORIGINS="https://<your-vercel-domain>,http://localhost:5173"
```

Region `iad` is Virginia, next to the SPHEREx bucket in AWS `us-east-1`, so uncached fetches are much faster there
than from Tunisia.

## 4. Deploy the frontend to Vercel

Import `quantum-horizon-web` at vercel.com. `vercel.json` already sets the build and the SPA rewrite. Set one
environment variable for Production, Preview and Development:

```
VITE_API_BASE = https://quantum-horizon-api.fly.dev
```

Redeploy after setting it — Vite reads it at build time, not at run time. Then open the deployed URL and check:

- the landing page hero shows three real frames and the measured number
- `/view?target=Barnard%27s%20Star&det=D2` blinks
- `/methods` renders the flag table, which proves the browser can reach the API

## 5. Record the demo

`docs/demo.md` has the beat sheet; `docs/submission.md` has a 30-second script and a seven-slide outline. The
submission guide asks for a 30-second video **or** a seven-slide deck, so do not build a three-minute film for that
field. A longer walkthrough is still useful for a local-event pitch.

## 6. Submit

Checklist lives at the top of `docs/submission.md`. The parts that are easy to forget:

- **Make `quantum-horizon` public.** The final project link must open with no login.
- Fill the "Use of Artificial Intelligence" field; a draft is in `docs/submission.md`.
- Submission opened on 14 November at 09:00 local and closes Sunday 15 November at 23:59 local. It is final.

## Known gaps

- The mover search has only ever been run on fields around the five targets, which are small (0.06°). A wider field
  (`fov=0.2`) searches more sky and is the better demo, but costs a fresh download.
- `SkyContext` loads Aladin from CDS at runtime; if CDS is slow the panel reports it and nothing else is affected.
- The frontend has one lint warning in `SkyContext.tsx` about reassigning a cancel flag — the standard effect-cleanup
  pattern, left as is.
- Deployment has never been exercised: the Dockerfile, `fly.toml` and `vercel.json` are written but have not run.
