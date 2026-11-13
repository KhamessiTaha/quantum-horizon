# Quantum Horizon

**Blink the infrared sky. Measure what moved.**

In 1930 Pluto was found by comparing two photographs of the same patch of sky. Quantum Horizon does that with SPHEREx:
give it a target name or a pair of coordinates, and it finds every SPHEREx exposure covering that position, aligns them
onto one grid, plays them in time order, and then measures what moved or changed — with an uncertainty on every number
and a plain label saying how far it can be trusted.

Built for NASA Space Apps 2026, challenge *Planet X and SPHEREx*.

Barnard's Star, detector 2, three passes between August 2025 and September 2026:

> measured **9.71 ± 1.57″** of motion over 0.99 years, against a catalog prediction of **10.28″** — a 6.2σ detection of
> a shift of 1.6 pixels.

## Measured results

Every figure below came out of this tool on real SPHEREx data, with the measurement method described in
[`docs/`](docs/) and on the app's Methods page.

| Target | Detector | Frames | Passes | Measured motion | Catalog | Verdict |
|---|---|---|---|---|---|---|
| Barnard's Star | D2 | 61 | 3 | 9.71 ± 1.57″ | 10.28″ | measured, agrees |
| Barnard's Star | D1 | 60 | 3 | 10.31 ± 1.08″ | 10.08″ | measured, agrees — an independent detector |
| Epsilon Indi B | D5 | 84 | 5 | 6.57 ± 0.62″ | 6.69″ | measured, agrees to 0.1″ |
| WISE 0855−0714 | D6 | 45 | 3 | 11.27 ± 2.97″ | 7.97″ | consistent within the noise; the faint-source limit |
| RW Aurigae | D1 | 56 | 3 | 0.36 ± 0.62″ | 0.02″ | correctly finds no motion |
| R Draconis | D1 | 53 | 7 | 6.50 ± 8.95″ | 0.03″ | saturated: the uncertainty says so |

Two of these matter more than the headline. **Barnard's Star measured independently on two detectors** agrees with
itself and with the catalog, which no single measurement can show. And **the tool returns no motion for the two stars
that are not moving**, with uncertainties large enough to cover the answer — a method that only ever finds motion is
not measuring anything.

## What it does

| The challenge asks for | Where it is |
|---|---|
| Enter RA/Dec, and through the URL | Search box accepts a name or `RA Dec`; every setting lives in the URL (`/view?target=…&det=D2&fov=0.06&mode=difference&pair=1-3`) |
| Fetch every SPHEREx image covering that spot | IRSA TAP finds them, and the pixels are read straight from the SPHEREx mirror on AWS Open Data |
| Play them as a time-ordered sequence | Blink player, one frame per pass, with keyboard control |
| Choose the field of view | 0.03° to 0.2° |
| Add and subtract epochs | Every pass can be dropped from the sequence and added back |
| Per-detector stacking | D1–D6; each pass is the median of that detector's exposures, aligned first |
| Spectra on the fly | Click any source: flux against wavelength, one line per pass |
| Gaia and WISE overlays | Gaia DR3 sources propagated to each pass date; WISE, 2MASS and DSS2 imagery through Aladin Lite |
| Contamination flags | Every flag on the source, named and explained, with a stated policy for each |
| Pick up new weekly data | The archive is queried per position, so a new release appears as soon as IRSA lists it |

Beyond the brief:

- **Measurements, not just pictures.** Motion, brightness and spectral change each come with an uncertainty and a
  confidence label: *measured*, *marginal*, *below the noise*, *not measurable yet*, or *indicative*.
- **Difference imaging between any two passes**, not only first and last.
- **A mover search.** Every source in the field is linked across passes and fitted; survivors are checked against Gaia
  DR3 and labelled a known moving star or an unexplained candidate.
- **Honesty where the data runs out.** Barnard's Star saturates SPHEREx, so the tool refuses to report its brightness
  and says why, while still measuring its position from the unsaturated wings.

## Running it

Backend (Python 3.12), from `backend/`:

```
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

On a machine where `pip.exe` is blocked by security policy, use `.venv\Scripts\python -m pip` as above.

Frontend (Node 20+), from the repo root:

```
npm install
npm run dev
```

Then open <http://localhost:5173>. Point the frontend at another backend with `VITE_API_BASE`; see `.env.example`.

Before any demo, warm the cache so nothing is fetched live:

```
.venv\Scripts\python scripts/prewarm.py
```

## How it works

```
IRSA TAP ──► which images cover this position (stored, so it survives an IRSA outage)
AWS S3   ──► only the pixels we need from each image, in parallel, with the IRSA cutout service as fallback
             │
             ├─ mask unusable pixels, subtract the modelled zodiacal light
             ├─ reproject every frame onto one tangent-plane grid  ← this is what makes a 1.6 pixel shift visible
             └─ median-stack per detector, per pass
                   │
                   ├─ PNG frames and difference images for the browser
                   ├─ positions fitted per frame and on the stack, uncertainty by leave-one-out jackknife
                   ├─ aperture photometry inside narrow wavelength bands
                   └─ source detection, track linking and a Gaia cross-match
```

The aligned cube is cached on disk, so a position is slow once and instant afterwards; every endpoint — frames,
measurements, spectrum, light curve, mover search — works from that one cached read.

### Three things that decide whether the science is right

**Flags.** A bright star's own pixels carry `TRANSIENT`, `OVERFLOW`, `SUR_ERROR`, `SOURCE` and `BLOOM`. Treating those
as bad data deletes the star: before this was fixed, every QR3 frame of Barnard's Star lost it and the motion fit
landed on noise, 27″ against a predicted 10.3″. Flags are split four ways — unusable, saturation, contamination,
informational — and `TRANSIENT` only masks a pixel where `SOURCE` is not also set. QR2 files carry no flag names at
all, so the standard table is used for them.

**Epochs.** Catalog positions are not where the star is now. SIMBAD coordinates are J2000 and Barnard's Star has moved
about 270″ since; Gaia DR3 is J2016.0 and it has moved about 100″ since that. Every catalog position is propagated to
the date of the frame it is compared against.

**Wavelength.** SPHEREx images a position many times per pass, each time through a different part of its linear
variable filter. A naive light curve would show the filter changing, not the star, so brightness is only ever compared
inside narrow wavelength bands.

## Deploying

- Backend: `fly deploy` from `backend/` using `fly.toml` — region `iad`, a volume at `/data` so the cache survives
  restarts. Add the frontend's origin to `QH_ALLOWED_ORIGINS` first.
- Frontend: import the repo into Vercel (`vercel.json` is set up) and set `VITE_API_BASE` to the backend's URL.

## Tests

`python -m pytest` from `backend/`. They cover the pipeline end to end on synthetic SPHEREx-like files, the flag
policy, the Gaia epoch propagation, and the mover search against fields with a planted mover, no mover, and a variable
star that must not be mistaken for one.

## Data and credits

- SPHEREx Quick Release spectral images: NASA/JPL-Caltech/IPAC, via the NASA/IPAC Infrared Science Archive (IRSA) and
  the SPHEREx mirror on AWS Open Data.
- Positions and proper motions: SIMBAD (CDS, Strasbourg) and Gaia DR3 (ESA).
- Context imagery: Aladin Lite (CDS) serving WISE, 2MASS and DSS2.
- Flag definitions: SPHEREx Explanatory Supplement and the IRSA Spectrophotometry Tool documentation.

Results are labelled measurements or candidates, never discoveries.

## Provenance

`research/` holds the spike scripts written before the hackathon to establish that the data supports this idea: the
archive queries, the first motion measurement of Barnard's Star, the AWS read-speed comparison, the light-curve work
and the mover-search validation over 150 synthetic fields. They are research, not product code, and are kept so the
numbers quoted above can be traced.
