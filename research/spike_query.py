import json
import re
import sys
import time
from collections import Counter

import astropy.units as u
from astropy.coordinates import SkyCoord, Distance
from astropy.time import Time
from astroquery.ipac.irsa import Irsa
import pyvo

SIMBAD_TAP_URLS = [
    "https://simbad.cds.unistra.fr/simbad/sim-tap",
    "https://simbad.cfa.harvard.edu/simbad/sim-tap",
]

TARGETS = {
    "barnard": ["NAME Barnard's Star", "GJ 699"],
    "eps_indi_b": ["eps Ind B", "* eps Ind B", "2MASS J22041052-5646577"],
    "wise0855": ["WISE J085510.83-071442.5", "WISEA J085510.74-071442.5"],
    "rw_aur": ["V* RW Aur", "RW Aur"],
    "r_dra": ["V* R Dra", "R Dra"],
}

FALLBACK_J2000 = {
    "wise0855": ("08h55m10.831s", "-07d14m42.53s"),
}

REFERENCE_EPOCH = Time("2026-01-01T00:00:00", scale="utc")
PASS_GAP_DAYS = 30
RELEASE_PATTERN = re.compile(r"/(qr\d+)/", re.IGNORECASE)


def as_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if number != number else number


def query_simbad(identifiers):
    quoted = ", ".join("'" + identifier.replace("'", "''") + "'" for identifier in identifiers)
    adql = (
        "SELECT TOP 1 b.main_id, b.ra, b.dec, b.pmra, b.pmdec, b.plx_value "
        "FROM basic AS b JOIN ident AS i ON i.oidref = b.oid "
        f"WHERE i.id IN ({quoted})"
    )
    errors = []
    for url in list(SIMBAD_TAP_URLS):
        try:
            table = pyvo.dal.TAPService(url).run_sync(adql).to_table()
            SIMBAD_TAP_URLS.remove(url)
            SIMBAD_TAP_URLS.insert(0, url)
            return table, url
        except Exception as error:
            errors.append(f"{url}: {type(error).__name__}: {str(error).splitlines()[0][:160]}")
    raise RuntimeError(" | ".join(errors))


def resolve(key, identifiers):
    table, url = query_simbad(identifiers)
    if len(table) == 0:
        if key in FALLBACK_J2000:
            ra, dec = FALLBACK_J2000[key]
            base = SkyCoord(ra, dec, frame="icrs")
            return {"main_id": key, "ra": base.ra.deg, "dec": base.dec.deg, "pmra": 0.0, "pmdec": 0.0, "plx": None, "source": "fallback"}
        raise RuntimeError(f"SIMBAD found none of {identifiers}")
    row = table[0]
    return {
        "main_id": str(row["main_id"]),
        "ra": as_float(row["ra"]),
        "dec": as_float(row["dec"]),
        "pmra": as_float(row["pmra"]) or 0.0,
        "pmdec": as_float(row["pmdec"]) or 0.0,
        "plx": as_float(row["plx_value"]),
        "source": url.split("/")[2],
    }


def propagate(info, epoch):
    distance = Distance(parallax=info["plx"] * u.mas) if info["plx"] and info["plx"] > 0 else 1 * u.kpc
    start = SkyCoord(
        ra=info["ra"] * u.deg,
        dec=info["dec"] * u.deg,
        pm_ra_cosdec=info["pmra"] * u.mas / u.yr,
        pm_dec=info["pmdec"] * u.mas / u.yr,
        distance=distance,
        radial_velocity=0 * u.km / u.s,
        obstime=Time("J2000"),
        frame="icrs",
    )
    return start, start.apply_space_motion(new_obstime=epoch)


def find_images(coord):
    adql = (
        "SELECT p.planeid, p.time_bounds_lower, p.energy_bandpassname, a.uri "
        "FROM spherex.artifact a JOIN spherex.plane p ON a.planeid = p.planeid "
        f"WHERE CONTAINS(POINT('ICRS', {coord.ra.deg:.7f}, {coord.dec.deg:.7f}), p.poly) = 1"
    )
    started = time.perf_counter()
    table = Irsa.query_tap(adql).to_table()
    return table, time.perf_counter() - started


def group_passes(images):
    passes = []
    for image in sorted(images, key=lambda item: item["mjd"]):
        if passes and image["mjd"] - passes[-1][-1]["mjd"] <= PASS_GAP_DAYS:
            passes[-1].append(image)
        else:
            passes.append([image])
    return passes


def summarize(key, identifiers):
    info = resolve(key, identifiers)
    start, moved = propagate(info, REFERENCE_EPOCH)
    shift = start.separation(moved).arcsec
    table, elapsed = find_images(moved)

    suffixes = Counter()
    images = []
    for row in table:
        uri = str(row["uri"])
        suffixes[uri.rsplit(".", 1)[-1].lower()] += 1
        if not uri.lower().endswith(".fits"):
            continue
        match = RELEASE_PATTERN.search(uri)
        mjd = float(row["time_bounds_lower"])
        images.append({
            "mjd": mjd,
            "date": Time(mjd, format="mjd").iso[:19],
            "detector": str(row["energy_bandpassname"]),
            "release": match.group(1).lower() if match else "unknown",
            "uri": uri,
        })

    passes = group_passes(images)

    print(f"\n=== {key}: {info['main_id']} (via {info['source']}) ===")
    print(f"J2000: RA {info['ra']:.6f}  Dec {info['dec']:.6f}")
    print(f"proper motion: pmRA {info['pmra']:.1f}  pmDec {info['pmdec']:.1f} mas/yr   parallax {info['plx']} mas")
    print(f"at {REFERENCE_EPOCH.iso[:10]}: RA {moved.ra.deg:.6f}  Dec {moved.dec.deg:.6f}  (moved {shift:.1f} arcsec since J2000)")
    print(f"TAP: {len(table)} rows in {elapsed:.1f} s   file types: {dict(suffixes)}")
    print(f"FITS images: {len(images)}   releases: {dict(Counter(i['release'] for i in images))}")
    print(f"detectors: {dict(sorted(Counter(i['detector'] for i in images).items()))}")
    for index, group in enumerate(passes, 1):
        detectors = dict(sorted(Counter(i["detector"] for i in group).items()))
        print(f"  pass {index}: {group[0]['date'][:10]} -> {group[-1]['date'][:10]}  {len(group)} images  {detectors}")

    return {
        "resolved": info,
        "epoch": REFERENCE_EPOCH.iso,
        "position_at_epoch": {"ra": moved.ra.deg, "dec": moved.dec.deg},
        "shift_since_j2000_arcsec": shift,
        "tap_seconds": elapsed,
        "images": images,
    }


def main():
    keys = sys.argv[1:] or list(TARGETS)
    results = {}
    for key in keys:
        try:
            results[key] = summarize(key, TARGETS[key])
        except Exception as error:
            print(f"\n=== {key} FAILED: {type(error).__name__}: {error}")
            results[key] = {"error": f"{type(error).__name__}: {error}"}
    with open("spike_results.json", "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)
    print("\nSaved spike_results.json")


if __name__ == "__main__":
    main()
