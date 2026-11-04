import argparse
import concurrent.futures as futures
import hashlib
import json
import time
import warnings
from pathlib import Path

import numpy as np
import requests
import astropy.units as u
from astropy.coordinates import SkyCoord, Distance
from astropy.io import fits
from astropy.time import Time
from astropy.utils.exceptions import AstropyWarning
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
from reproject import reproject_interp
from scipy.optimize import curve_fit

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

warnings.simplefilter("ignore", AstropyWarning)
warnings.simplefilter("ignore", RuntimeWarning)

IRSA_ROOT = "https://irsa.ipac.caltech.edu/"
PASS_GAP_DAYS = 30


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="barnard")
    parser.add_argument("--detector", default="2")
    parser.add_argument("--size", type=float, default=0.06)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-frames", type=int, default=0)
    return parser.parse_args()


def load_target(key):
    data = json.loads(Path("spike_results.json").read_text(encoding="utf-8"))
    entry = data.get(key)
    if not entry or "error" in entry:
        raise SystemExit(f"No usable entry for {key} in spike_results.json; rerun spike_query.py")
    return entry


def star_at_j2000(resolved):
    plx = resolved.get("plx")
    distance = Distance(parallax=plx * u.mas) if plx and plx > 0 else 1 * u.kpc
    return SkyCoord(
        ra=resolved["ra"] * u.deg,
        dec=resolved["dec"] * u.deg,
        pm_ra_cosdec=resolved["pmra"] * u.mas / u.yr,
        pm_dec=resolved["pmdec"] * u.mas / u.yr,
        distance=distance,
        radial_velocity=0 * u.km / u.s,
        obstime=Time("J2000"),
        frame="icrs",
    )


def predicted_at(start, mjd):
    moved = start.apply_space_motion(new_obstime=Time(mjd, format="mjd"))
    return SkyCoord(moved.ra, moved.dec, frame="icrs")


def cutout_url(uri, center, size):
    base = uri if uri.startswith("http") else IRSA_ROOT + uri.lstrip("/")
    return f"{base}?center={center.ra.deg:.7f},{center.dec.deg:.7f}&size={size}"


def fetch(url, path, attempts=4):
    if path.exists() and path.stat().st_size >= 2880:
        return {"ok": True, "seconds": 0.0, "cached": True, "attempts": 0}
    started = time.perf_counter()
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, timeout=120)
            if response.status_code == 200 and response.content[:6] == b"SIMPLE":
                path.write_bytes(response.content)
                return {"ok": True, "seconds": time.perf_counter() - started, "cached": False, "attempts": attempt}
            last_error = f"HTTP {response.status_code}: {response.content[:80]!r}"
        except requests.RequestException as error:
            last_error = f"{type(error).__name__}: {str(error)[:120]}"
        time.sleep(2 * attempt)
    return {"ok": False, "seconds": time.perf_counter() - started, "cached": False, "attempts": attempts, "error": last_error}


def named_hdu(hdul, name):
    try:
        return hdul[name]
    except KeyError:
        return None


def read_frame(path):
    with fits.open(path) as hdul:
        names = [hdu.name for hdu in hdul]
        image = named_hdu(hdul, "IMAGE")
        if image is None:
            image = next(hdu for hdu in hdul if hdu.data is not None and getattr(hdu.data, "ndim", 0) == 2)
        data = image.data.astype(float)
        wcs = WCS(image.header, fobj=hdul)
        zodi = named_hdu(hdul, "ZODI")
        zodi_applied = zodi is not None and zodi.data is not None and zodi.data.shape == data.shape
        if zodi_applied:
            data = data - zodi.data
        flags_hdu = named_hdu(hdul, "FLAGS")
        flags = None
        if flags_hdu is not None and flags_hdu.data is not None and flags_hdu.data.shape == data.shape:
            flags = flags_hdu.data.astype(np.int64)
    return data, wcs, flags, names, zodi_applied


def flags_near(flags, wcs, coord, half=2):
    if flags is None:
        return []
    x, y = wcs.world_to_pixel(coord)
    if not (np.isfinite(x) and np.isfinite(y)):
        return []
    xi, yi = int(round(float(x))), int(round(float(y)))
    box = flags[max(yi - half, 0):yi + half + 1, max(xi - half, 0):xi + half + 1]
    return sorted(int(value) for value in np.unique(box) if value != 0)


def gaussian(coords, amplitude, xc, yc, sigma, offset):
    x, y = coords
    return amplitude * np.exp(-((x - xc) ** 2 + (y - yc) ** 2) / (2 * sigma * sigma)) + offset


def brightest_near(image, x0, y0, radius=3):
    ny, nx = image.shape
    xi, yi = int(round(x0)), int(round(y0))
    y_lo, y_hi = max(yi - radius, 0), min(yi + radius + 1, ny)
    x_lo, x_hi = max(xi - radius, 0), min(xi + radius + 1, nx)
    region = image[y_lo:y_hi, x_lo:x_hi]
    if not np.isfinite(region).any():
        return None
    iy, ix = np.unravel_index(np.nanargmax(region), region.shape)
    return x_lo + ix, y_lo + iy


def fit_star(image, x0, y0, half=4):
    peak = brightest_near(image, x0, y0)
    if peak is None:
        return None
    xi, yi = peak
    ny, nx = image.shape
    if xi - half < 0 or yi - half < 0 or xi + half >= nx or yi + half >= ny:
        return None
    box = image[yi - half:yi + half + 1, xi - half:xi + half + 1]
    good = np.isfinite(box)
    if good.sum() < 0.7 * box.size:
        return None
    border = np.concatenate([box[0], box[-1], box[1:-1, 0], box[1:-1, -1]])
    background = np.nanmedian(border)
    yy, xx = np.mgrid[yi - half:yi + half + 1, xi - half:xi + half + 1]
    values = box[good] - background
    amplitude = float(np.nanmax(values))
    if not amplitude > 0:
        return None
    try:
        params, _ = curve_fit(
            gaussian,
            (xx[good], yy[good]),
            values,
            p0=[amplitude, xi, yi, 1.0, 0.0],
            bounds=([0, xi - half, yi - half, 0.3, -np.inf], [np.inf, xi + half, yi + half, half, np.inf]),
            maxfev=5000,
        )
        return {"x": float(params[1]), "y": float(params[2]), "amplitude": float(params[0]), "sigma_px": float(params[3]), "method": "gaussian"}
    except Exception:
        weights = np.clip(values, 0, None)
        if weights.sum() <= 0:
            return None
        return {
            "x": float((xx[good] * weights).sum() / weights.sum()),
            "y": float((yy[good] * weights).sum() / weights.sum()),
            "amplitude": amplitude,
            "sigma_px": None,
            "method": "centroid",
        }


def common_grid(center, scale_arcsec, size_deg):
    npix = int(round(size_deg * 3600 / scale_arcsec))
    npix += 1 - npix % 2
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crval = [center.ra.deg, center.dec.deg]
    wcs.wcs.crpix = [(npix + 1) / 2, (npix + 1) / 2]
    wcs.wcs.cdelt = [-scale_arcsec / 3600, scale_arcsec / 3600]
    return wcs, (npix, npix)


def group_passes(frames):
    passes = []
    for frame in sorted(frames, key=lambda item: item["mjd"]):
        if passes and frame["mjd"] - passes[-1][-1]["mjd"] <= PASS_GAP_DAYS:
            passes[-1].append(frame)
        else:
            passes.append([frame])
    return passes


def offsets_arcsec(center, coord):
    dlon, dlat = center.spherical_offsets_to(coord)
    return float(dlon.to_value(u.arcsec)), float(dlat.to_value(u.arcsec))


def stretch(image, low, high):
    scaled = np.clip((image - low) / (high - low), 0, 1)
    return np.arcsinh(10 * scaled) / np.arcsinh(10)


def save_visuals(stacks, pass_info, grid_wcs, label, stem):
    finite = np.concatenate([stack[np.isfinite(stack)] for stack in stacks])
    low, high = np.percentile(finite, [5, 99.7])
    reference = pass_info[0].get("measured_px")

    fig, ax = plt.subplots(figsize=(5, 5.4), dpi=110)

    def draw(index):
        ax.clear()
        ax.imshow(stretch(stacks[index], low, high), origin="lower", cmap="gray", interpolation="nearest")
        info = pass_info[index]
        px, py = info["predicted_px"]
        ax.plot(px, py, "+", color="#ff8c42", markersize=16, mew=1.5, label="predicted (SIMBAD PM)")
        if info.get("measured_px"):
            ax.plot(*info["measured_px"], "x", color="#4fc3f7", markersize=10, mew=1.5, label="measured")
        if reference:
            ax.add_patch(plt.Circle(reference, 1.5, fill=False, color="#ffffff", lw=0.8, ls="--"))
        ax.set_title(f"{label}\npass {index + 1} · {info['date']} · {info['frames']} frames", fontsize=10)
        ax.legend(loc="lower left", fontsize=7, framealpha=0.6)
        ax.set_xticks([])
        ax.set_yticks([])

    animation = FuncAnimation(fig, draw, frames=len(stacks), interval=900)
    animation.save(f"{stem}_blink.gif", writer=PillowWriter(fps=1.2))
    plt.close(fig)

    columns = len(stacks) + 1
    fig, axes = plt.subplots(1, columns, figsize=(3.2 * columns, 3.6), dpi=110)
    for index, stack in enumerate(stacks):
        axes[index].imshow(stretch(stack, low, high), origin="lower", cmap="gray", interpolation="nearest")
        axes[index].plot(*pass_info[index]["predicted_px"], "+", color="#ff8c42", markersize=14, mew=1.4)
        axes[index].set_title(f"pass {index + 1}\n{pass_info[index]['date']}", fontsize=9)
        axes[index].set_xticks([])
        axes[index].set_yticks([])
    difference = stacks[-1] - stacks[0]
    limit = np.nanpercentile(np.abs(difference), 99.5) or 1.0
    axes[-1].imshow(difference, origin="lower", cmap="RdBu_r", vmin=-limit, vmax=limit, interpolation="nearest")
    axes[-1].set_title(f"pass {len(stacks)} − pass 1", fontsize=9)
    axes[-1].set_xticks([])
    axes[-1].set_yticks([])
    fig.suptitle(label, fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(f"{stem}_strip.png")
    plt.close(fig)


def main():
    args = parse_args()
    detector = "SPHEREx-D" + args.detector.upper().lstrip("D")
    entry = load_target(args.target)
    start = star_at_j2000(entry["resolved"])
    center = SkyCoord(entry["position_at_epoch"]["ra"] * u.deg, entry["position_at_epoch"]["dec"] * u.deg, frame="icrs")

    images = sorted((i for i in entry["images"] if i["detector"] == detector), key=lambda item: item["mjd"])
    if args.max_frames:
        images = images[:args.max_frames]
    if not images:
        raise SystemExit(f"No {detector} images for {args.target}")

    cache = Path("cutouts") / args.target / detector
    cache.mkdir(parents=True, exist_ok=True)
    jobs = []
    for image in images:
        url = cutout_url(image["uri"], center, args.size)
        path = cache / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".fits")
        jobs.append((image, url, path))

    print(f"Downloading {len(jobs)} {detector} cutouts of {args.size} deg with {args.workers} workers...")
    started = time.perf_counter()
    results = []
    with futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {pool.submit(fetch, url, path): (image, url, path) for image, url, path in jobs}
        for done, future in enumerate(futures.as_completed(pending), 1):
            image, url, path = pending[future]
            outcome = future.result()
            results.append((image, path, outcome))
            if done % 10 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)}")
    wall = time.perf_counter() - started

    fresh = [o for _, _, o in results if o["ok"] and not o["cached"]]
    failed = [(i, o) for i, _, o in results if not o["ok"]]
    retried = [o for _, _, o in results if o["ok"] and o["attempts"] > 1]
    print(f"Downloads: {len(results) - len(failed)} ok ({len(fresh)} fresh, {len(results) - len(failed) - len(fresh)} cached), "
          f"{len(failed)} failed, {len(retried)} needed retries, wall {wall:.1f} s")
    if fresh:
        times = [o["seconds"] for o in fresh]
        print(f"Per-cutout time: median {np.median(times):.1f} s, max {max(times):.1f} s")
    for image, outcome in failed[:5]:
        print(f"  failed {image['date']}: {outcome.get('error')}")

    usable = [(image, path) for image, path, outcome in results if outcome["ok"]]
    if not usable:
        raise SystemExit("No cutouts downloaded")

    first_data, first_wcs, _, hdu_names, _ = read_frame(usable[0][1])
    scale = float(np.mean(proj_plane_pixel_scales(first_wcs.celestial)) * 3600)
    grid_wcs, shape = common_grid(center, scale, args.size)
    print(f"Cutout HDUs: {hdu_names}")
    print(f"Native pixel scale {scale:.2f} arcsec; common grid {shape[0]}x{shape[1]} px")

    frames = []
    flag_values = set()
    zodi_count = 0
    for image, path in usable:
        data, wcs, flags, _, zodi_applied = read_frame(path)
        zodi_count += zodi_applied
        predicted = predicted_at(start, image["mjd"])
        near = flags_near(flags, wcs.celestial, predicted)
        flag_values.update(near)
        reprojected, _ = reproject_interp((data, wcs.celestial), grid_wcs, shape_out=shape)
        px, py = grid_wcs.world_to_pixel(predicted)
        fit = fit_star(reprojected, float(px), float(py))
        frame = {"mjd": image["mjd"], "date": image["date"], "image": reprojected, "predicted": predicted, "flags_near_star": near, "fit": fit}
        if fit:
            measured = grid_wcs.pixel_to_world(fit["x"], fit["y"])
            frame["measured"] = measured
            frame["residual_arcsec"] = offsets_arcsec(predicted, measured)
        frames.append(frame)

    print(f"ZODI subtracted in {zodi_count}/{len(frames)} frames")
    print(f"Nonzero FLAGS values within 2 px of the star: {sorted(flag_values) or 'none'}")

    passes = group_passes(frames)
    stacks, pass_info, report_passes = [], [], []
    print(f"\n{'pass':<5}{'dates':<25}{'frames':>7}{'fits':>6}  {'measured - predicted (arcsec)':<32}{'scatter':>9}")
    for index, group in enumerate(passes, 1):
        stack = np.nanmedian(np.stack([frame["image"] for frame in group]), axis=0)
        stacks.append(stack)
        mean_mjd = float(np.mean([frame["mjd"] for frame in group]))
        predicted = predicted_at(start, mean_mjd)
        pred_px = [float(v) for v in grid_wcs.world_to_pixel(predicted)]
        fitted = [frame for frame in group if frame.get("measured")]
        info = {"date": Time(mean_mjd, format="mjd").iso[:10], "frames": len(group), "predicted_px": pred_px}
        record = {"pass": index, "mean_mjd": mean_mjd, "frames": len(group), "fitted": len(fitted)}
        if fitted:
            offsets = np.array([offsets_arcsec(center, frame["measured"]) for frame in fitted])
            mean_offset = offsets.mean(axis=0)
            error = offsets.std(axis=0, ddof=1) / np.sqrt(len(offsets)) if len(offsets) > 1 else np.array([np.nan, np.nan])
            pred_offset = np.array(offsets_arcsec(center, predicted))
            residual = mean_offset - pred_offset
            measured_px = [float(v) for v in grid_wcs.world_to_pixel(center.spherical_offsets_by(mean_offset[0] * u.arcsec, mean_offset[1] * u.arcsec))]
            info["measured_px"] = measured_px
            record.update({
                "measured_offset_arcsec": mean_offset.tolist(),
                "measured_error_arcsec": error.tolist(),
                "predicted_offset_arcsec": pred_offset.tolist(),
                "residual_arcsec": residual.tolist(),
                "frame_scatter_arcsec": offsets.std(axis=0, ddof=1).tolist() if len(offsets) > 1 else None,
            })
            scatter = np.hypot(*offsets.std(axis=0, ddof=1)) if len(offsets) > 1 else float("nan")
            dates = f"{group[0]['date'][:10]} -> {group[-1]['date'][:10]}"
            print(f"{index:<5}{dates:<25}{len(group):>7}{len(fitted):>6}  dRA* {residual[0]:+6.2f}  dDec {residual[1]:+6.2f}{'':>8}{scatter:>8.2f}\"")
        else:
            print(f"{index:<5}{group[0]['date'][:10]:<25}{len(group):>7}{0:>6}  no successful fits")
        pass_info.append(info)
        report_passes.append(record)

    usable_passes = [p for p in report_passes if "measured_offset_arcsec" in p]
    summary = {}
    if len(usable_passes) >= 2:
        first, last = usable_passes[0], usable_passes[-1]
        measured = np.subtract(last["measured_offset_arcsec"], first["measured_offset_arcsec"])
        predicted = np.subtract(last["predicted_offset_arcsec"], first["predicted_offset_arcsec"])
        error = np.hypot(np.hypot(*first["measured_error_arcsec"]), np.hypot(*last["measured_error_arcsec"]))
        years = (last["mean_mjd"] - first["mean_mjd"]) / 365.25
        pa = lambda vector: float(np.degrees(np.arctan2(vector[0], vector[1])) % 360)
        summary = {
            "baseline_years": years,
            "measured_motion_arcsec": float(np.hypot(*measured)),
            "measured_motion_error_arcsec": float(error),
            "predicted_motion_arcsec": float(np.hypot(*predicted)),
            "measured_pa_deg": pa(measured),
            "predicted_pa_deg": pa(predicted),
            "measured_vector_arcsec": measured.tolist(),
            "predicted_vector_arcsec": predicted.tolist(),
        }
        print(f"\nMotion pass {first['pass']} -> pass {last['pass']} over {years:.2f} yr:")
        print(f"  measured  {summary['measured_motion_arcsec']:.2f} +/- {error:.2f} arcsec  "
              f"({summary['measured_motion_arcsec'] / scale:.2f} px) at PA {summary['measured_pa_deg']:.0f} deg")
        print(f"  predicted {summary['predicted_motion_arcsec']:.2f} arcsec  "
              f"({summary['predicted_motion_arcsec'] / scale:.2f} px) at PA {summary['predicted_pa_deg']:.0f} deg")

    stem = f"spike2_{args.target}_{detector.split('-')[-1]}"
    label = f"{entry['resolved']['main_id']} · {detector} · {args.size} deg"
    save_visuals(stacks, pass_info, grid_wcs, label, stem)

    report = {
        "target": args.target,
        "detector": detector,
        "size_deg": args.size,
        "downloads": {"requested": len(jobs), "failed": len(failed), "retried": len(retried), "wall_seconds": wall},
        "pixel_scale_arcsec": scale,
        "hdus": hdu_names,
        "flags_near_star": sorted(flag_values),
        "passes": report_passes,
        "motion": summary,
    }
    Path(f"{stem}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nSaved {stem}_blink.gif, {stem}_strip.png, {stem}.json")


if __name__ == "__main__":
    main()
