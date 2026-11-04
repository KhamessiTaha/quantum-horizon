# Quantum Horizon

A public web tool for the NASA Space Apps 2026 challenge **Planet X and SPHEREx**. Enter a position on the sky and Quantum Horizon blinks every SPHEREx image of it across time, then measures what moved or changed and says how confident that measurement is.

## Status

Research phase. `research/` holds the feasibility scripts that tested the data path and the measurements on real SPHEREx data. The application is built during the hackathon, November 14–15, 2026.

## Research scripts

Python 3.12. From the `research/` folder:

```
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

On macOS or Linux, use `python3.12 -m venv .venv` and `.venv/bin/pip`.

| Script | What it does |
| --- | --- |
| `spike_query.py` | Resolves the five test targets with SIMBAD, propagates proper motion, and lists every SPHEREx image covering each one via IRSA TAP. Writes `spike_results.json`, which the others read. |
| `spike_motion.py` | Downloads cutouts for one target and detector, aligns them on a common grid, stacks each pass, and compares measured motion with the catalog. |
| `spike_aws.py` | Reads the same pixels directly from the `nasa-irsa-spherex` S3 mirror and times it against the cutout service. |
| `spike_lightcurve.py` | Measures brightness and wavelength per frame from S3, builds light curves within wavelength bins, and flags saturation. |

Run `spike_query.py` first. Example: `.venv\Scripts\python spike_motion.py --target barnard --detector 2`.

## Data and credits

- SPHEREx Quick Release images: NASA/JPL-Caltech/IPAC, via the [NASA/IPAC Infrared Science Archive](https://irsa.ipac.caltech.edu/Missions/spherex.html) and the [AWS Open Data registry](https://registry.opendata.aws/spherex-qr/).
- Positions and proper motions: [SIMBAD](https://simbad.cds.unistra.fr/simbad/), CDS Strasbourg (Harvard mirror used as fallback).
- Built with Astropy, astroquery, PyVO and reproject.

Results are reported as measurements or candidates, never as discoveries.
