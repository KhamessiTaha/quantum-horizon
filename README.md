# Quantum Horizon

**Blink the infrared sky. Measure what moved.**

In 1930 Pluto was found by comparing two photographs of the same patch of sky. Quantum Horizon does that with SPHEREx:
give it a target name, a pair of coordinates, or a click on the sky map, and it finds every SPHEREx exposure covering
that position, aligns them onto one grid, plays them in time order, and then measures what moved or changed — with an
uncertainty on every number and a plain label saying how far it can be trusted.

Built for NASA Space Apps 2026, challenge *Planet X and SPHEREx*.

| | |
|---|---|
| **Live tool** | <https://quantum-horizon-web.vercel.app> |
| **Live API** | <https://quantum-horizon-api.vercel.app/api/health> |
| **Demo video (30 s)** | <https://www.youtube.com/watch?v=UU21SZwQQ0I> |
| **Slides (7)** | [docs/quantum-horizon-slides.pdf](docs/quantum-horizon-slides.pdf) |
| **Source** | this repository — the whole project, its history and the research |

Barnard's Star, detector 2, three passes between August 2025 and September 2026:

> measured **9.71 ± 1.57″** of motion over 0.99 years, against a catalog prediction of **10.28″** — a 6.2σ detection of
> a shift of 1.6 pixels.

## Measured results

Every figure below came out of this tool on real SPHEREx data. How each one is measured, and where the method stops,
is on the app's [Methods page](https://quantum-horizon-web.vercel.app/methods).

| Target | Detector | Frames | Passes | Measured motion | Catalog | Verdict |
|---|---|---|---|---|---|---|
| Barnard's Star | D2 | 61 | 3 | 9.71 ± 1.57″ | 10.28″ | measured, agrees |
| Barnard's Star | D1 | 60 | 3 | 10.31 ± 1.08″ | 10.08″ | measured, agrees — an independent detector |
| Epsilon Indi B | D5 | 84 | 5 | 6.57 ± 0.62″ | 6.69″ | measured, agrees to 0.1″ |
| WISE 0855−0714 | D6 | 45 | 3 | 11.27 ± 2.97″ | 7.97″ | marginal: the faint-source limit |
| RW Aurigae | D1 | 56 | 3 | 0.36 ± 0.62″ | 0.02″ | correctly finds no motion |
| R Draconis | D1 | 53 | 7 | 6.50 ± 8.95″ | 0.03″ | saturated: the uncertainty says so |

Two of these matter more than the headline. **Barnard's Star measured independently on two detectors** agrees with
itself and with the catalog, which no single measurement can show. And **the tool returns no motion for the two stars
that are not moving**, with uncertainties large enough to cover the answer — a method that only ever finds motion is
not measuring anything.

The sky map shows the same motion across a quarter of a century: SIMBAD's catalog label for Barnard's Star sits at its
year-2000 position, WISE caught it about 2010 a little to the north, and the SPHEREx field being blinked today is
further north again — about 10.3″ a year, 4.5′ since 2000.

## What it does

| The challenge asks for | Where it is |
|---|---|
| Enter RA/Dec, and through the URL | The search box takes a name, decimal degrees (`269.4463 4.7682`) or sexagesimal (`17 57 48.5 +04 41 36`), with suggestions as you type; every setting lives in the URL (`/view?target=…&det=D2&fov=0.06&mode=difference&pair=1-3`) |
| Fetch every SPHEREx image covering that spot | IRSA TAP finds them, with IRSA's SIA service as a fallback; the pixels are read straight from the SPHEREx mirror on AWS Open Data |
| Play them as a time-ordered sequence | Blink player, one frame per pass, with keyboard control |
| Choose the field of view | 0.03° to 0.2° |
| Add and subtract epochs | Every pass can be dropped from the sequence and added back |
| Per-detector stacking | D1–D6; each pass is the median of that detector's exposures, aligned first |
| Spectra on the fly | Click any source: flux against wavelength, one line per pass |
| Gaia and WISE overlays | Gaia DR3 sources propagated to each pass date; an interactive sky map on WISE, 2MASS and DSS2 imagery |
| Contamination flags | Every flag on the source, named and explained, with a stated policy for each |
| Pick up new weekly data | The archive is queried per position, so a new release appears as soon as IRSA lists it |

Beyond the brief:

- **Measurements, not just pictures.** Motion, brightness and spectral change each come with an uncertainty and a
  confidence label: *measured*, *marginal*, *below the noise*, *not measurable yet*, or *indicative*.
- **A colour view of the 102 bands.** Detectors 6, 3 and 1 become red, green and blue, matched pass by pass, so a
  cold brown dwarf glows red and a hot star looks blue-white — and the colour image still blinks.
- **Data you can take away.** Every view downloads as CSV or JSON with its measurements, every frame used, the flags
  and a citation line.
- **The Sun's neighbourhood in 3D.** 163 stars and brown dwarfs within about 7 parsecs, placed by their SIMBAD
  parallaxes, coloured by spectral type and sized by catalog magnitude, against the 6,372 brightest stars of the real
  sky. Search or filter the list (brown dwarfs, red dwarfs, planet hosts, the challenge targets), fly to any object
  and blink it.
- **A result: JPL's orbits checked against SPHEREx for 120 asteroids.** The 120 largest main-belt and near-Earth
  asteroids were tracked through their SPHEREx exposures on detector 1. 117 were detected and measured; 116 of them sit
  where NASA/JPL's orbit predicts within their uncertainty or one pixel, with a typical offset of 1.0″ (0.17 of a
  SPHEREx pixel). The one exception, Fortuna, rests on three frames and is labelled marginal, not claimed as anything.
  Every asteroid is listed on the results page with its offset, uncertainty and label, and links to its blink.
- **Blink an asteroid or comet.** Any of the 7,533 bodies in the Solar System view can be tracked through every SPHEREx
  exposure that caught it; eleven, from Ceres and Vesta to Eros, are stored and open instantly. IRSA's Moving Object Search Tool lists the exposures and JPL Horizons predicts where each one should be;
  every frame is cut out around that prediction, so the asteroid holds still while the stars stream past. Its measured
  offset from the prediction tests the orbit against SPHEREx, with an uncertainty and a label (bright asteroids saturate
  SPHEREx, so most are indicative). A body only counts as seen if it stands out in the median of all frames stacked on
  it, where the stars cancel; Sedna, at magnitude 21, is reported as not seen rather than matched to a passing star.
- **The Solar System in 3D.** The eight planets from JPL's mean orbital elements and 7,533 real asteroids, comets and
  distant objects from JPL's Small-Body Database, each moved along its own orbit as time plays. Click any body to follow
  it: its card gives its orbit, where it sits in our sky on that date, how fast it crosses the sky in SPHEREx pixels,
  and a rotating impression. A "Planet Nine clues" view draws the 111 extreme trans-Neptunian orbits behind that
  hypothesis. Sky positions agree with JPL Horizons to about an arcminute and are labelled indicative.
- **A sky map you can blink from.** WISE, 2MASS and DSS2 imagery with SIMBAD's best-known objects named on top. Click
  any star or any position and blink it; the blue square marks the SPHEREx field being measured.
- **Difference imaging between any two passes**, not only first and last.
- **A mover search.** Every source in the field is linked across passes and fitted; survivors are checked against Gaia
  DR3 and labelled a known moving star or an unexplained candidate.
- **Honesty where the data runs out.** Barnard's Star saturates SPHEREx, so the tool refuses to report its brightness
  and says why, while still measuring its position from the unsaturated wings.

## Repositories

| Repository | What it is |
|---|---|
| [`quantum-horizon`](https://github.com/KhamessiTaha/quantum-horizon) | **This one: the project.** Frontend in `src/`, backend in `backend/`, research in `research/`, docs in `docs/`. All work happens here. |
| [`quantum-horizon-web`](https://github.com/KhamessiTaha/quantum-horizon-web) | Deploy mirror of the frontend, which Vercel builds into the live tool. |
| [`quantum-horizon-api`](https://github.com/KhamessiTaha/quantum-horizon-api) | Deploy mirror of `backend/` as its own root, which Vercel runs as the API. |

The two mirrors carry the same history as this repository and exist only so each deployment builds from a root folder.
Change code here, then bring it across: `git subtree split --prefix=backend` for the API, a merge from `main` for the
web mirror.

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

Then open <http://localhost:5173>. In development the frontend talks to `http://localhost:8000`; point it at another
backend with `VITE_API_BASE` (see `.env.example`). A production build uses the deployed API unless `VITE_API_BASE` says
otherwise.

Before any demo, warm the cache so nothing is fetched live, from `backend/`:

```
.venv\Scripts\python scripts/prewarm.py
```

## How it works

```
IRSA TAP ──► which images cover this position — IRSA SIA if TAP does not answer; the list is stored either way
AWS S3   ──► only the pixels we need from each image, in parallel, with the IRSA cutout service as fallback
             │
             ├─ mask unusable pixels, subtract the modelled zodiacal light
             ├─ reproject every frame onto one tangent-plane grid  ← this is what makes a 1.6 pixel shift visible
             └─ median-stack per detector, per pass
                   │
                   ├─ PNG frames and difference images, sent inside the response
                   ├─ positions fitted per frame and on the stack, uncertainty by leave-one-out jackknife
                   ├─ aperture photometry inside narrow wavelength bands
                   └─ source detection, track linking and a Gaia cross-match
```

Every frame read is cached, so a position is slow once and instant afterwards; every endpoint — frames, measurements,
spectrum, light curve, mover search — works from that one cached read. The five challenge targets ship with their
pixels in `backend/cache/regions`, so the demo works even when the archive does not.

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

Both halves run on Vercel's free tier.

- **API** — the `quantum-horizon-api` mirror, imported into Vercel. `pyproject.toml` names `api/index.py` as the
  entry point, which copies the shipped cache to `/tmp` on a cold start; `vercel.json` gives the function 300 s.
  Set `QH_ALLOWED_ORIGINS` to the frontend's address.
- **Frontend** — the `quantum-horizon-web` mirror, imported into Vercel; `vercel.json` sets the build and the
  single-page rewrite.

`backend/Dockerfile` and `backend/fly.toml` still build a container with a persistent cache volume, for a host that
keeps a disk between requests.

## Tests

`python -m pytest` from `backend/`. They cover the pipeline end to end on synthetic SPHEREx-like files, the flag
policy, the Gaia epoch propagation, the archive fallbacks, and the mover search against fields with a planted mover, no
mover, and a variable star that must not be mistaken for one. `npm run build` and `npm run lint` check the frontend.

## Data and credits

- SPHEREx spectral images (Quick Releases QR2 and QR3, Data Release 1): NASA/JPL-Caltech/IPAC, via the NASA/IPAC
  Infrared Science Archive (IRSA) and the SPHEREx mirror on AWS Open Data.
- Positions and proper motions: SIMBAD (CDS, Strasbourg, with the Harvard mirror) and Gaia DR3 (ESA).
- Asteroid exposures and predicted positions: IRSA Moving Object Search Tool (MOST), with JPL Horizons ephemerides.
- Asteroid, comet and trans-Neptunian orbits: NASA/JPL Small-Body Database query API. Planet orbits: JPL's
  "Keplerian Elements for Approximate Positions of the Major Planets" (E. M. Standish). The orbit code is adapted from
  [CosmoArchitects](https://github.com/KhamessiTaha/CosmoArchitects), my NASA Space Apps 2024 orrery.
- Sky-map imagery: WISE, 2MASS and DSS2 hierarchical surveys served by IRSA, shown with Aladin Lite (CDS).
- Flag definitions: SPHEREx Explanatory Supplement and the IRSA Spectrophotometry Tool documentation.

Results are labelled measurements or candidates, never discoveries.

## Provenance

`research/` holds the spike scripts written before the hackathon to establish that the data supports this idea: the
archive queries, the first motion measurement of Barnard's Star, the AWS read-speed comparison, the light-curve work
and the mover-search validation over 150 synthetic fields. They are research, not product code, and are kept so the
numbers quoted above can be traced.
