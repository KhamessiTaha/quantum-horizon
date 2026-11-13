# Demo

Everything below runs on real SPHEREx data. Warm the cache first (`scripts/prewarm.py` from `backend/`), so no shot
waits on the archive.

## Before recording

- [ ] `prewarm.py` has run for all five targets, and each URL below has been opened once.
- [ ] Backend and frontend both running, or both deployed.
- [ ] Browser at 1440 wide, dark theme, no extensions visible.
- [ ] Say the words "measured" and "predicted" exactly as the screen labels them.

## Beats

**1 · The idea (0:00–0:20)**
Open the landing page. Pluto was found in 1930 by blinking two photographic plates of the same patch of sky. SPHEREx
now images the whole sky every six months, in 102 infrared bands. The strip on the right is three real passes over
Barnard's Star, and the difference image beside them.

**2 · One target, one click (0:20–0:40)**
`/view?target=Barnard%27s%20Star&det=D2&fov=0.06&mode=blink`
Press play. Three passes, each one the median of that detector's exposures in that pass, all aligned onto a common
grid. The amber cross is where the catalog says the star should be on that date; the cyan ring is where we measured it.

**3 · The measurement (0:40–1:10)**
Point at the findings panel. *Measured 9.71 ± 1.57″ over 0.99 years; the catalog predicts 10.28″.* That is a shift of
1.6 pixels, recovered from data where one pixel is 6.15 arcseconds wide. The per-pass table shows how many frames went
into each position and how many were rejected.

**4 · Why the alignment matters (1:10–1:30)**
Switch to Difference. Everything that did not move cancels; Barnard's Star leaves an amber-and-cyan pair with the
measured track drawn between them. Change the compared pair to 1 and 2 to show the shorter baseline.

**5 · Honesty (1:30–1:55)**
Open Brightness. The tool refuses to give a light curve for this star: it saturates the detector, the core carries no
usable values, and it says so instead of quoting a number. Positions still work, because they come from the
unsaturated wings. Then open the data-quality panel and show every flag on the source, named and explained.

**6 · Why 102 bands (1:55–2:20)**
Open Spectrum, or switch to RW Aurigae on D1. A spectrum per pass, measured in the same aperture: this is what only
SPHEREx can do, and it is why brightness is compared inside narrow wavelength bands rather than across the whole
detector.

**7 · What moved (2:20–2:45)**
Open "What moved". Every source in the field is linked across passes and fitted; a track survives only at five sigma,
and is then checked against Gaia DR3 along its whole path. Known movers are labelled with their Gaia id; anything
without a match is an unexplained candidate. The panel states the search's own limit for this baseline — and that a
distant Solar System body would not appear this way, because the Earth's orbit swings it out of the field between
passes.

**8 · Anyone can use it (2:45–3:00)**
Copy link, or Embed. Every setting is in the URL, so a view can be shared, linked from a paper, or dropped into a
page. New SPHEREx releases appear as soon as IRSA lists them.

## If something fails live

- Archive down: cached targets still work, and the tool says it is serving a stored image list.
- Gaia down: the mover search labels candidates "catalogue not checked" rather than claiming anything.
- Sky map does not load: it comes from CDS and nothing else depends on it.
