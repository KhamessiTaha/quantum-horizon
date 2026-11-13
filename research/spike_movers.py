import argparse
import json
import time
import warnings
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, maximum_filter
from scipy.optimize import curve_fit, OptimizeWarning

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.simplefilter("ignore", OptimizeWarning)
warnings.simplefilter("ignore", RuntimeWarning)

PIXEL_ARCSEC = 6.15
PSF_SIGMA = 1.0
FIELD_PX = 117
EPOCHS_YR = np.array([0.0, 0.52, 0.99])
DETECT_SNR = 5.0
LINK_RADIUS_PX = 4.0
PREDICT_RADIUS_PX = 1.5
MOTION_SIGMA = 5.0
CATALOG_MATCH_PX = 1.5
CATALOG_PM_TOLERANCE = 0.35
POSITION_FLOOR_PX = 0.1
STATIC_PX_PER_YR = 0.1
ISOLATION_PX = 2.5


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=6)
    parser.add_argument("--seed", type=int, default=7)
    return parser.parse_args()


def psf_image(shape, x, y, flux):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    return flux / (2 * np.pi * PSF_SIGMA ** 2) * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * PSF_SIGMA ** 2))


def make_field(rng, mover=None, n_stars=150, noise=1.0, jitter_px=0.15, variable=True):
    flux_per_snr = noise * np.sqrt(4 * np.pi) * PSF_SIGMA
    snr = 6 * (1 - rng.random(n_stars)) ** (-1 / 1.2)
    stars = {
        "x": rng.uniform(4, FIELD_PX - 5, n_stars),
        "y": rng.uniform(4, FIELD_PX - 5, n_stars),
        "flux": np.minimum(snr, 2000) * flux_per_snr,
        "vx": np.zeros(n_stars),
        "vy": np.zeros(n_stars),
        "in_catalog": rng.random(n_stars) < 0.97,
    }
    known = {"x": 30.0, "y": 40.0, "flux": 80 * flux_per_snr, "vx": -0.13, "vy": 1.68}
    for key in ("x", "y", "flux", "vx", "vy"):
        stars[key] = np.append(stars[key], known[key])
    stars["in_catalog"] = np.append(stars["in_catalog"], True)
    truth = {"known_index": len(stars["x"]) - 1, "mover_index": None, "variable_index": None}
    if variable:
        truth["variable_index"] = 0
        stars["x"][0], stars["y"][0], stars["flux"][0] = 85.0, 75.0, 60 * flux_per_snr
    if mover is not None:
        speed, snr_mover, angle = mover
        for key, value in (("x", 70.0), ("y", 30.0), ("flux", snr_mover * flux_per_snr),
                           ("vx", speed * np.cos(angle)), ("vy", speed * np.sin(angle))):
            stars[key] = np.append(stars[key], value)
        stars["in_catalog"] = np.append(stars["in_catalog"], False)
        truth["mover_index"] = len(stars["x"]) - 1

    passes = []
    offsets = rng.normal(0, jitter_px, (len(EPOCHS_YR), 2))
    for k, t in enumerate(EPOCHS_YR):
        image = rng.normal(0, noise, (FIELD_PX, FIELD_PX))
        for i in range(len(stars["x"])):
            flux = stars["flux"][i]
            if truth["variable_index"] == i:
                flux *= (1.0, 2.2, 0.6)[k]
            image += psf_image(image.shape, stars["x"][i] + stars["vx"][i] * t + offsets[k, 0],
                               stars["y"][i] + stars["vy"][i] * t + offsets[k, 1], flux)
        passes.append(image)

    catalog = [
        {"x": stars["x"][i], "y": stars["y"][i], "vx": stars["vx"][i], "vy": stars["vy"][i]}
        for i in range(len(stars["x"])) if stars["in_catalog"][i]
    ]
    return passes, stars, catalog, truth


def gaussian(coords, amplitude, xc, yc, offset):
    x, y = coords
    return amplitude * np.exp(-((x - xc) ** 2 + (y - yc) ** 2) / (2 * PSF_SIGMA ** 2)) + offset


def detect(image):
    noise = 1.4826 * np.median(np.abs(image - np.median(image)))
    smooth = gaussian_filter(image, PSF_SIGMA)
    smooth_noise = noise / (2 * np.sqrt(np.pi) * PSF_SIGMA)
    snr_map = smooth / smooth_noise
    peaks = (snr_map == maximum_filter(snr_map, size=3)) & (snr_map > DETECT_SNR)
    sources = []
    half = 3
    for yi, xi in zip(*np.nonzero(peaks)):
        if xi < half or yi < half or xi >= image.shape[1] - half or yi >= image.shape[0] - half:
            continue
        box = image[yi - half:yi + half + 1, xi - half:xi + half + 1]
        yy, xx = np.mgrid[yi - half:yi + half + 1, xi - half:xi + half + 1]
        try:
            params, cov = curve_fit(
                gaussian, (xx.ravel(), yy.ravel()), box.ravel(),
                p0=[box.max(), xi, yi, 0.0], sigma=np.full(box.size, noise), absolute_sigma=True,
                bounds=([0, xi - 1.5, yi - 1.5, -np.inf], [np.inf, xi + 1.5, yi + 1.5, np.inf]), maxfev=2000,
            )
        except Exception:
            continue
        errors = np.sqrt(np.clip(np.diag(cov), 0, None))
        sources.append({
            "x": params[1], "y": params[2], "ex": float(np.hypot(errors[1], POSITION_FLOOR_PX)), "ey": float(np.hypot(errors[2], POSITION_FLOOR_PX)),
            "flux": params[0] * 2 * np.pi * PSF_SIGMA ** 2, "snr": float(snr_map[yi, xi]),
        })
    return sources, noise


def register(detections):
    reference = np.array([[s["x"], s["y"]] for s in detections[0]])
    offsets = [np.zeros(2)]
    for sources in detections[1:]:
        points = np.array([[s["x"], s["y"]] for s in sources])
        shifts = []
        for p in points:
            d = np.hypot(*(reference - p).T)
            j = int(np.argmin(d))
            if d[j] < 1.0:
                shifts.append(p - reference[j])
        offsets.append(np.median(shifts, axis=0) if len(shifts) >= 10 else np.zeros(2))
    for sources, offset in zip(detections, offsets):
        for s in sources:
            s["x"] -= offset[0]
            s["y"] -= offset[1]
    return offsets


def nearest(sources, x, y, radius, used):
    best, best_d = None, radius
    for j, s in enumerate(sources):
        if j in used:
            continue
        d = np.hypot(s["x"] - x, s["y"] - y)
        if d < best_d:
            best, best_d = j, d
    return best


def fit_motion(points):
    t = np.array([p[0] for p in points])
    result = {}
    chi2 = 0.0
    for axis, value_key, error_key in (("x", 1, 3), ("y", 2, 4)):
        v = np.array([p[value_key] for p in points])
        w = 1 / np.array([p[error_key] for p in points]) ** 2
        design = np.vstack([np.ones_like(t), t]).T
        normal = design.T @ (design * w[:, None])
        cov = np.linalg.inv(normal)
        coef = cov @ (design.T @ (w * v))
        chi2 += float(np.sum(w * (v - design @ coef) ** 2))
        result[axis] = coef[0]
        result[f"v{axis}"] = coef[1]
        result[f"ev{axis}"] = float(np.sqrt(cov[1, 1]))
    speed = float(np.hypot(result["vx"], result["vy"]))
    speed_error = float(np.hypot(result["vx"] * result["evx"], result["vy"] * result["evy"]) / max(speed, 1e-9))
    result.update({"speed": speed, "speed_error": speed_error, "significance": speed / max(speed_error, 1e-9),
                   "chi2_dof": chi2 / max(2 * len(points) - 4, 1)})
    return result


def link(detections):
    tracks = []
    used = [set() for _ in detections]
    for i, s0 in enumerate(detections[0]):
        j = nearest(detections[1], s0["x"], s0["y"], LINK_RADIUS_PX, used[1])
        if j is None:
            continue
        s1 = detections[1][j]
        dt1, dt2 = EPOCHS_YR[1] - EPOCHS_YR[0], EPOCHS_YR[2] - EPOCHS_YR[0]
        px = s0["x"] + (s1["x"] - s0["x"]) * dt2 / dt1
        py = s0["y"] + (s1["y"] - s0["y"]) * dt2 / dt1
        k = nearest(detections[2], px, py, PREDICT_RADIUS_PX, used[2])
        if k is None:
            continue
        used[1].add(j)
        used[2].add(k)
        chain = [s0, s1, detections[2][k]]
        crowded = False
        for n, s in enumerate(chain):
            for other in detections[n]:
                if other is not s and np.hypot(other["x"] - s["x"], other["y"] - s["y"]) < ISOLATION_PX:
                    crowded = True
        points = [(EPOCHS_YR[n], s["x"], s["y"], s["ex"], s["ey"]) for n, s in enumerate(chain)]
        motion = fit_motion(points)
        motion["fluxes"] = [s["flux"] for s in chain]
        motion["snr"] = float(np.median([s["snr"] for s in chain]))
        motion["crowded"] = crowded
        tracks.append(motion)
    return tracks


def classify(tracks, catalog):
    movers, rejected = [], {"blended": 0, "catalogued static star": 0}
    for track in tracks:
        if track["significance"] < MOTION_SIGMA or track["chi2_dof"] > 9:
            continue
        if track["crowded"]:
            rejected["blended"] += 1
            continue
        mid_t = EPOCHS_YR.mean()
        mx, my = track["x"] + track["vx"] * mid_t, track["y"] + track["vy"] * mid_t
        if any(np.hypot(c["vx"], c["vy"]) < STATIC_PX_PER_YR and np.hypot(c["x"] - mx, c["y"] - my) < CATALOG_MATCH_PX for c in catalog):
            rejected["catalogued static star"] += 1
            continue
        label, match = "Unexplained candidate", None
        for c in catalog:
            close = all(np.hypot(c["x"] + c["vx"] * t - (track["x"] + track["vx"] * t),
                                 c["y"] + c["vy"] * t - (track["y"] + track["vy"] * t)) < CATALOG_MATCH_PX for t in EPOCHS_YR)
            catalog_speed = np.hypot(c["vx"], c["vy"])
            if close and abs(catalog_speed - track["speed"]) < CATALOG_PM_TOLERANCE * max(catalog_speed, 0.5):
                label, match = "Known moving star", c
                break
        movers.append({**track, "label": label, "catalog_speed": None if match is None else float(np.hypot(match["vx"], match["vy"]))})
    return movers, rejected


def run_field(passes, catalog):
    detections = [detect(image)[0] for image in passes]
    offsets = register(detections)
    tracks = link(detections)
    movers, rejected = classify(tracks, catalog)
    return movers, detections, offsets, tracks, rejected


def recovered(movers, stars, index):
    if index is None:
        return None
    for m in movers:
        if np.hypot(m["x"] - stars["x"][index], m["y"] - stars["y"][index]) < 1.5:
            return m
    return None


def main():
    args = parse_args()
    rng = np.random.default_rng(args.seed)

    passes, stars, catalog, truth = make_field(rng, mover=(1.0, 20.0, 2.4))
    started = time.perf_counter()
    movers, detections, offsets, tracks, rejected = run_field(passes, catalog)
    elapsed = time.perf_counter() - started
    print(f"Demo field: {len(stars['x'])} sources planted; detections per pass {[len(d) for d in detections]}; "
          f"{len(tracks)} linked tracks; {elapsed:.1f} s")
    print(f"Registration offsets recovered (px): {[np.round(o, 2).tolist() for o in offsets]}")
    for m in movers:
        catalog_text = f"   catalog {m['catalog_speed'] * PIXEL_ARCSEC:.2f}\"/yr" if m["catalog_speed"] is not None else ""
        print(f"  {m['label']:<22} at ({m['x']:5.1f},{m['y']:5.1f})  "
              f"{m['speed'] * PIXEL_ARCSEC:5.2f} +/- {m['speed_error'] * PIXEL_ARCSEC:4.2f}\"/yr  "
              f"({m['significance']:.0f} sigma, S/N {m['snr']:.0f}){catalog_text}")
    print(f"Rejected as not measurable: {rejected}")
    variable = recovered(movers, stars, truth["variable_index"])
    print(f"Variable star flagged as mover: {'YES (bad)' if variable else 'no (good)'}")

    speeds_px = [0.25, 0.5, 1.0, 2.0, 3.0]
    snrs = [5, 8, 12, 20, 50]
    grid = np.zeros((len(snrs), len(speeds_px)))
    false_alarms = 0
    fields = 0
    known_found = 0
    rejected_total = {"blended": 0, "catalogued static star": 0}
    started = time.perf_counter()
    for a, snr in enumerate(snrs):
        for b, speed in enumerate(speeds_px):
            hits = 0
            for _ in range(args.trials):
                field, field_stars, field_catalog, field_truth = make_field(rng, mover=(speed, snr, rng.uniform(0, 2 * np.pi)))
                field_movers, _, _, _, field_rejected = run_field(field, field_catalog)
                for key in rejected_total:
                    rejected_total[key] += field_rejected[key]
                fields += 1
                hit = recovered(field_movers, field_stars, field_truth["mover_index"])
                hits += hit is not None and hit["label"] == "Unexplained candidate"
                known = recovered(field_movers, field_stars, field_truth["known_index"])
                known_found += known is not None and known["label"] == "Known moving star"
                planted = {field_truth["mover_index"], field_truth["known_index"]}
                for m in field_movers:
                    if not any(np.hypot(m["x"] - field_stars["x"][i], m["y"] - field_stars["y"][i]) < 1.5 for i in planted):
                        false_alarms += 1
            grid[a, b] = hits / args.trials
    sweep_seconds = time.perf_counter() - started

    print(f"\nCompleteness for an uncatalogued mover ({args.trials} fields per cell, {fields} fields, {sweep_seconds:.0f} s):")
    header = "".join(f"{s * PIXEL_ARCSEC:>9.1f}\"" for s in speeds_px)
    print(f"{'S/N  /  speed per yr':<22}{header}")
    for a, snr in enumerate(snrs):
        print(f"{snr:<22}" + "".join(f"{grid[a, b]:>10.0%}" for b in range(len(speeds_px))))
    print(f"\nKnown high-motion star labelled correctly: {known_found}/{fields}")
    print(f"False alarms: {false_alarms} in {fields} fields ({false_alarms / fields:.2f} per field)")
    print(f"Apparent movers rejected and reported as not measurable: {rejected_total}")

    difference = passes[2] - passes[0]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.4), dpi=100)
    limit = np.percentile(passes[0], 99.5)
    for ax, image, title in ((axes[0], passes[0], "pass 1"), (axes[1], passes[2], "pass 3")):
        ax.imshow(np.arcsinh(image / limit * 10), origin="lower", cmap="gray")
        ax.set_title(title)
    dlim = np.percentile(np.abs(difference), 99.7)
    axes[2].imshow(difference, origin="lower", cmap="RdBu_r", vmin=-dlim, vmax=dlim)
    axes[2].set_title("pass 3 - pass 1, detected movers")
    for m in movers:
        colour = "#2ca02c" if m["label"] == "Known moving star" else "#ff7f0e"
        axes[2].add_patch(plt.Circle((m["x"] + m["vx"] * EPOCHS_YR[1], m["y"] + m["vy"] * EPOCHS_YR[1]), 4, fill=False, color=colour, lw=2))
        axes[2].annotate(m["label"], (m["x"], m["y"] - 6), color=colour, fontsize=8, ha="center")
    for ax in axes:
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle("Synthetic field: one known high-motion star, one uncatalogued mover (1 px/yr, S/N 20), one variable star")
    fig.tight_layout()
    fig.savefig("spike_movers_demo.png")

    fig, ax = plt.subplots(figsize=(7, 4.6), dpi=110)
    ax.imshow(grid, origin="lower", cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(speeds_px)), [f"{s * PIXEL_ARCSEC:.1f}" for s in speeds_px])
    ax.set_yticks(range(len(snrs)), snrs)
    for a in range(len(snrs)):
        for b in range(len(speeds_px)):
            ax.text(b, a, f"{grid[a, b]:.0%}", ha="center", va="center", color="white" if grid[a, b] > 0.6 else "black")
    ax.set_xlabel("motion (arcsec per year)")
    ax.set_ylabel("signal-to-noise per pass")
    ax.set_title("Mover search completeness, 3 passes over 0.99 yr")
    fig.tight_layout()
    fig.savefig("spike_movers_completeness.png")

    Path("spike_movers.json").write_text(json.dumps({
        "speeds_arcsec_per_yr": [s * PIXEL_ARCSEC for s in speeds_px], "snr": snrs,
        "completeness": grid.tolist(), "fields": fields, "false_alarms": false_alarms,
        "known_found": known_found, "demo_seconds": elapsed, "rejected": rejected_total,
    }, indent=2), encoding="utf-8")
    print("\nSaved spike_movers_demo.png, spike_movers_completeness.png, spike_movers.json")


if __name__ == "__main__":
    main()
