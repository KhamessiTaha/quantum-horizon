import argparse
import concurrent.futures as futures
import json
import time
import warnings
from collections import Counter
from pathlib import Path

import numpy as np
import astropy.units as u
from astropy import log as astropy_log
from astropy.io import fits
from astropy.time import Time
from astropy.timeseries import LombScargle
from astropy.utils.exceptions import AstropyWarning
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import spike_motion as motion
from spike_aws import s3_url

warnings.simplefilter("ignore", AstropyWarning)
warnings.simplefilter("ignore", RuntimeWarning)
astropy_log.setLevel("WARNING")

FLAG_NAMES = {
    0: "TRANSIENT", 1: "OVERFLOW", 2: "SUR_ERROR", 4: "PHANTOM", 5: "REFERENCE", 6: "NONFUNC",
    7: "DICHROIC", 9: "MISSING_DATA", 10: "HOT", 11: "COLD", 12: "FULLSAMPLE", 14: "PHANMISS",
    15: "NONLINEAR", 17: "PERSIST", 19: "OUTLIER", 21: "SOURCE",
}
SUSPECT_BITS = (1, 2, 6, 9, 15)
APERTURE_PX = 3.0
WING_PX = (3.5, 7.0)
ANNULUS_PX = (9.0, 13.0)
MIN_WING_FINITE = 0.9


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="r_dra")
    parser.add_argument("--detector", default="1")
    parser.add_argument("--size", type=float, default=0.05)
    parser.add_argument("--max-frames", type=int, default=240)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--bins", type=int, default=6)
    return parser.parse_args()


def bit_names(mask):
    return [FLAG_NAMES.get(bit, f"BIT{bit}") for bit in range(32) if mask >> bit & 1]


def flag_definitions(header):
    return [(card.keyword, card.value, card.comment) for card in header.cards if card.keyword.startswith("MSK")]


def measure(meta, star, size_deg, want_definitions):
    options = {"anon": True, "default_block_size": 512 * 1024}
    started = time.perf_counter()
    with fits.open(s3_url(meta["uri"]), use_fsspec=True, fsspec_kwargs=options, lazy_load_hdus=True) as hdul:
        header = hdul["IMAGE"].header
        sky = WCS(header).celestial
        x, y = (float(v) for v in sky.world_to_pixel(star))
        if not (np.isfinite(x) and np.isfinite(y)):
            return {"ok": False, "reason": "not on image"}
        spectral = WCS(header=header, fobj=hdul, key="W")
        spectral.sip = None
        wavelength, bandwidth = spectral.pixel_to_world(x, y)
        half = int(np.ceil(size_deg * 3600 / 6.15 / 2))
        nx, ny = header["NAXIS1"], header["NAXIS2"]
        xi, yi = int(round(x)), int(round(y))
        x0, x1, y0, y1 = xi - half, xi + half + 1, yi - half, yi + half + 1
        if x0 < 0 or y0 < 0 or x1 > nx or y1 > ny:
            return {"ok": False, "reason": "too close to detector edge"}
        image = np.asarray(hdul["IMAGE"].section[y0:y1, x0:x1], dtype=float)
        zodi = np.asarray(hdul["ZODI"].section[y0:y1, x0:x1], dtype=float)
        variance = np.asarray(hdul["VARIANCE"].section[y0:y1, x0:x1], dtype=float)
        flags = np.asarray(hdul["FLAGS"].section[y0:y1, x0:x1]).astype(np.int64)
        definitions = flag_definitions(hdul["FLAGS"].header) if want_definitions else None

    area_sr = float(np.prod(proj_plane_pixel_scales(sky))) * (np.pi / 180) ** 2
    to_jy = area_sr * 1e6
    signal = image - zodi
    yy, xx = np.mgrid[y0:y1, x0:x1]
    radius = np.hypot(xx - x, yy - y)
    aperture = radius <= APERTURE_PX
    wing = (radius >= WING_PX[0]) & (radius <= WING_PX[1])
    annulus = (radius >= ANNULUS_PX[0]) & (radius <= ANNULUS_PX[1])
    background = float(np.nanmedian(signal[annulus]))

    core_bad = ~np.isfinite(signal[aperture])
    core_flags = flags[aperture]
    nan_flag_mask = int(np.bitwise_or.reduce(core_flags[core_bad].ravel())) if core_bad.any() else 0
    core_mask = int(np.bitwise_or.reduce(core_flags.ravel()))
    core_flux = None if core_bad.any() else float((signal[aperture] - background).sum() * to_jy)
    core_error = None if core_bad.any() else float(np.sqrt(np.nansum(variance[aperture])) * to_jy)

    wing_values = signal[wing]
    wing_finite = np.isfinite(wing_values)
    wing_fraction = float(wing_finite.mean())
    wing_flux = wing_error = None
    if wing_fraction >= MIN_WING_FINITE:
        scale = wing_values.size / wing_finite.sum()
        wing_flux = float((wing_values[wing_finite] - background).sum() * scale * to_jy)
        wing_error = float(np.sqrt(np.nansum(variance[wing][wing_finite])) * scale * to_jy)
    wing_mask = int(np.bitwise_or.reduce(flags[wing].ravel()))

    if core_flux is None and wing_flux is None:
        return {
            "ok": False,
            "reason": f"core blanked and wings only {wing_fraction:.0%} finite",
            "core_nan_pixels": int(core_bad.sum()),
            "nan_flag_mask": nan_flag_mask,
            "definitions": definitions,
        }
    return {
        "ok": True,
        "mjd": meta["mjd"],
        "date": meta["date"],
        "wavelength_um": float(wavelength.to_value(u.um)),
        "bandwidth_um": float(u.Quantity(bandwidth).to_value(u.um)),
        "core_flux_jy": core_flux,
        "core_err_jy": core_error,
        "wing_flux_jy": wing_flux,
        "wing_err_jy": wing_error,
        "wing_finite_fraction": wing_fraction,
        "core_nan_pixels": int(core_bad.sum()),
        "core_pixels": int(aperture.sum()),
        "nan_flag_mask": nan_flag_mask,
        "core_flag_mask": core_mask,
        "wing_flag_mask": wing_mask,
        "background_mjy_sr": background,
        "seconds": time.perf_counter() - started,
        "definitions": definitions,
    }


def main():
    args = parse_args()
    detector = "SPHEREx-D" + args.detector.upper().lstrip("D")
    entry = motion.load_target(args.target)
    start = motion.star_at_j2000(entry["resolved"])
    images = sorted((i for i in entry["images"] if i["detector"] == detector), key=lambda item: item["mjd"])
    if not images:
        raise SystemExit(f"No {detector} images for {args.target}")
    available = Counter(Time(i["mjd"], format="mjd").iso[:7] for i in images)
    print(f"{detector} frames available per month ({len(images)} total):")
    print("  " + "  ".join(f"{month}:{count}" for month, count in sorted(available.items())))
    if args.max_frames and len(images) > args.max_frames:
        all_mjd = np.array([i["mjd"] for i in images])
        targets = np.linspace(all_mjd.min(), all_mjd.max(), args.max_frames)
        picks = np.unique(np.abs(all_mjd[None, :] - targets[:, None]).argmin(axis=1))
        images = [images[k] for k in picks]

    cache_path = Path(f"lightcurve_cache_{args.target}_{detector.split('-')[-1]}.json")
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    todo = [i for i in images if not cache.get(i["uri"], {}).get("ok") or "wing_flux_jy" not in cache[i["uri"]]]
    print(f"{len(images)} {detector} frames selected, {len(images) - len(todo)} cached, reading {len(todo)} from AWS with {args.workers} workers...")

    definitions = None
    started = time.perf_counter()
    with futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {}
        for meta in todo:
            star = motion.predicted_at(start, meta["mjd"])
            pending[pool.submit(measure, meta, star, args.size, True)] = meta
        for done, future in enumerate(futures.as_completed(pending), 1):
            meta = pending[future]
            try:
                result = future.result()
            except Exception as error:
                result = {"ok": False, "reason": f"{type(error).__name__}: {str(error)[:140]}"}
            if result.get("definitions"):
                definitions = result["definitions"]
            result.pop("definitions", None)
            cache[meta["uri"]] = result
            if done % 20 == 0 or done == len(todo):
                print(f"  {done}/{len(todo)}  ({time.perf_counter() - started:.0f} s)")
    cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")

    if definitions:
        print("\nFLAGS header MSK* cards (from the file itself):")
        for keyword, value, comment in definitions:
            print(f"  {keyword:<10} = {str(value):<22} / {comment}")

    entries = [cache[i["uri"]] for i in images if i["uri"] in cache]
    ok_rows = [r for r in entries if r.get("ok")]
    failures = [r.get("reason", "?") for r in entries if not r.get("ok")]
    print(f"\nRead {len(ok_rows)}/{len(images)} frames; skipped {len(failures)}")
    for reason in sorted(set(failures)):
        print(f"  skipped ({failures.count(reason)}): {reason}")

    blanked = [r for r in entries if r.get("core_nan_pixels")]
    if blanked:
        nan_union = int(np.bitwise_or.reduce([r.get("nan_flag_mask", 0) for r in blanked]))
        nan_counts = [r["core_nan_pixels"] for r in blanked]
        print(f"Core blanked (NaN) in {len(blanked)}/{len(entries)} frames; NaN pixels per core: median {int(np.median(nan_counts))}, max {max(nan_counts)}")
        print(f"Flag bits on the NaN core pixels: {bit_names(nan_union)}")

    core_ok = [r for r in ok_rows if r.get("core_flux_jy") is not None]
    metric = "core" if len(core_ok) >= 0.8 * max(len(ok_rows), 1) else "wing"
    rows = [r for r in ok_rows if r.get(f"{metric}_flux_jy") is not None]
    print(f"Photometry used: {metric.upper()} ({'3 px aperture' if metric == 'core' else f'ring {WING_PX[0]}-{WING_PX[1]} px around a blanked core'}) on {len(rows)} frames")
    if len(rows) < 10:
        raise SystemExit("Too few measurements for a light curve")

    mjd = np.array([r["mjd"] for r in rows])
    wave = np.array([r["wavelength_um"] for r in rows])
    flux = np.array([r[f"{metric}_flux_jy"] for r in rows])
    error = np.array([r[f"{metric}_err_jy"] for r in rows])
    masks = [r[f"{metric}_flag_mask"] for r in rows]
    suspect = np.array([any(m >> bit & 1 for bit in SUSPECT_BITS) for m in masks])
    union = int(np.bitwise_or.reduce(masks))
    print(f"Wavelength at star: {wave.min():.3f} - {wave.max():.3f} um")
    print(f"Flux: {np.nanmin(flux):.3g} - {np.nanmax(flux):.3g} Jy   median S/N {np.nanmedian(flux / error):.0f}")
    print(f"Flag bits in the {metric} region: {bit_names(union)}")
    print(f"Frames with suspect flags {[FLAG_NAMES[b] for b in SUSPECT_BITS]}: {int(suspect.sum())}/{len(rows)}")

    exclude_suspect = suspect.mean() < 0.5
    if not exclude_suspect:
        print("Most frames carry suspect flags; keeping them in the light curve and treating results as indicative only")
    edges = np.quantile(wave, np.linspace(0, 1, args.bins + 1))
    bin_index = np.clip(np.searchsorted(edges, wave, side="right") - 1, 0, args.bins - 1)
    normalized = np.full(len(rows), np.nan)
    for b in range(args.bins):
        members = (bin_index == b) & (flux > 0) & (~suspect if exclude_suspect else True)
        if members.sum() >= 3:
            normalized[members] = 2.5 * np.log10(np.median(flux[members]) / flux[members])
    usable = np.isfinite(normalized)

    print(f"\n{'month':<9}{'frames':>7}{'lambda (um)':>16}{'delta mag vs bin median':>26}")
    months = np.array([Time(m, format="mjd").iso[:7] for m in mjd])
    for month in sorted(set(months)):
        sel = (months == month) & usable
        if sel.any():
            print(f"{month:<9}{sel.sum():>7}{wave[sel].min():>8.3f}-{wave[sel].max():<7.3f}{np.median(normalized[sel]):>+20.2f}")

    summary = {"frames": len(rows), "metric": metric, "suspect": int(suspect.sum()), "flag_bits": bit_names(union)}
    if usable.sum() >= 10:
        span = mjd[usable].max() - mjd[usable].min()
        frequency = np.linspace(1 / min(span, 800), 1 / 50, 5000)
        periodogram = LombScargle(mjd[usable], normalized[usable])
        power = periodogram.power(frequency)
        best = 1 / frequency[np.argmax(power)]
        amplitude = np.nanpercentile(normalized[usable], 95) - np.nanpercentile(normalized[usable], 5)
        summary.update({"baseline_days": float(span), "best_period_days": float(best), "peak_power": float(power.max()), "amplitude_mag_5_95": float(amplitude)})
        print(f"\nBaseline {span:.0f} days; Lomb-Scargle best period {best:.0f} days (power {power.max():.2f}); "
              f"5-95% amplitude {amplitude:.2f} mag")
    else:
        frequency = power = None

    stem = f"spike3_{args.target}_{detector.split('-')[-1]}"
    dates = Time(mjd, format="mjd").datetime
    fig, axes = plt.subplots(3, 1, figsize=(10, 11), dpi=110)
    scatter = axes[0].scatter(dates[~suspect], flux[~suspect], c=wave[~suspect], cmap="viridis", s=14)
    axes[0].scatter(dates[suspect], flux[suspect], facecolors="none", edgecolors="#d62728", s=18, label="suspect flags")
    axes[0].set_yscale("log")
    axes[0].set_ylabel(f"{metric} flux (Jy, approx.)")
    axes[0].set_title(f"{entry['resolved']['main_id']} · {detector} · {metric} photometry (colour = wavelength)")
    fig.colorbar(scatter, ax=axes[0], label="wavelength (µm)")
    if suspect.any():
        axes[0].legend(loc="best", fontsize=8)
    colours = plt.cm.viridis(np.linspace(0, 1, args.bins))
    for b in range(args.bins):
        sel = usable & (bin_index == b)
        if sel.any():
            axes[1].plot(dates[sel], normalized[sel], "o", ms=3.5, color=colours[b], label=f"{edges[b]:.3f}-{edges[b + 1]:.3f} µm")
    axes[1].invert_yaxis()
    axes[1].set_ylabel("Δmag vs bin median (brighter ↑)")
    axes[1].set_title("Light curve within narrow wavelength bins (spectral shape removed)")
    axes[1].legend(fontsize=7, ncol=3)
    if power is not None:
        axes[2].plot(1 / frequency, power, color="#333")
        axes[2].axvline(summary["best_period_days"], color="#d62728", ls="--", lw=1)
        axes[2].set_xlabel("period (days)")
        axes[2].set_ylabel("Lomb-Scargle power")
        axes[2].set_title(f"Periodogram · best {summary['best_period_days']:.0f} d")
    fig.tight_layout()
    fig.savefig(f"{stem}_lightcurve.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5), dpi=110)
    sc = ax.scatter(wave, flux, c=mjd, cmap="plasma", s=12)
    ax.set_yscale("log")
    ax.set_xlabel("wavelength (µm)")
    ax.set_ylabel(f"{metric} flux (Jy, approx.)")
    ax.set_title(f"{entry['resolved']['main_id']} · {detector} · spectrum at each epoch (colour = date)")
    bar = fig.colorbar(sc, ax=ax)
    ticks = np.linspace(mjd.min(), mjd.max(), 5)
    bar.set_ticks(ticks)
    bar.set_ticklabels([Time(t, format="mjd").iso[:10] for t in ticks])
    fig.tight_layout()
    fig.savefig(f"{stem}_spectrum.png")
    plt.close(fig)

    Path(f"{stem}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nSaved {stem}_lightcurve.png, {stem}_spectrum.png, {stem}.json")


if __name__ == "__main__":
    main()
