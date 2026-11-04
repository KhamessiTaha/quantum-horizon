import argparse
import concurrent.futures as futures
import hashlib
import json
import time
import warnings
from pathlib import Path

import numpy as np
import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.utils.exceptions import AstropyWarning
from astropy.wcs import WCS

import spike_motion as motion

warnings.simplefilter("ignore", AstropyWarning)
warnings.simplefilter("ignore", RuntimeWarning)

BUCKET = "nasa-irsa-spherex"
PIXEL_ARCSEC = 6.15


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="barnard")
    parser.add_argument("--detector", default="2")
    parser.add_argument("--size", type=float, default=0.06)
    parser.add_argument("--frames", type=int, default=8)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--block-kb", type=int, default=512)
    return parser.parse_args()


def s3_url(uri):
    marker = "/spherex/"
    index = uri.find(marker)
    if index < 0:
        raise ValueError(f"cannot map {uri} to an S3 key")
    return f"s3://{BUCKET}/{uri[index + len(marker):]}"


def read_region(url, center, size_deg, block_bytes, options=None):
    kwargs = {"anon": True, "default_block_size": block_bytes} if options is None else options
    started = time.perf_counter()
    with fits.open(url, use_fsspec=True, fsspec_kwargs=kwargs, lazy_load_hdus=True) as hdul:
        image_hdu = hdul["IMAGE"]
        header = image_hdu.header
        wcs = WCS(header).celestial
        header_seconds = time.perf_counter() - started
        x, y = wcs.world_to_pixel(center)
        if not (np.isfinite(x) and np.isfinite(y)):
            return {"ok": False, "error": "position not on this image"}
        half = int(np.ceil(size_deg * 3600 / PIXEL_ARCSEC / 2))
        nx, ny = header["NAXIS1"], header["NAXIS2"]
        x0, x1 = max(int(round(float(x))) - half, 0), min(int(round(float(x))) + half + 1, nx)
        y0, y1 = max(int(round(float(y))) - half, 0), min(int(round(float(y))) + half + 1, ny)
        if x0 >= x1 or y0 >= y1:
            return {"ok": False, "error": "region off detector"}
        image = np.asarray(image_hdu.section[y0:y1, x0:x1], dtype=float)
        flags = np.asarray(hdul["FLAGS"].section[y0:y1, x0:x1])
        zodi = np.asarray(hdul["ZODI"].section[y0:y1, x0:x1], dtype=float)
        compressed = isinstance(image_hdu, fits.CompImageHDU)
    return {
        "ok": True,
        "seconds": time.perf_counter() - started,
        "header_seconds": header_seconds,
        "box": [x0, x1, y0, y1],
        "shape": list(image.shape),
        "star_px": [float(x) - x0, float(y) - y0],
        "image": image,
        "flags": flags,
        "zodi": zodi,
        "compressed": compressed,
    }


def star_peak(image, x, y):
    peak = motion.brightest_near(image, x, y, radius=2)
    return None if peak is None else float(image[peak[1], peak[0]])


def cached_cutout_peak(entry, image_meta, center, size, detector, target):
    url = motion.cutout_url(image_meta["uri"], center, size)
    path = Path("cutouts") / target / detector / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".fits")
    if not path.exists():
        return None
    with fits.open(path) as hdul:
        data = hdul["IMAGE"].data.astype(float)
        wcs = WCS(hdul["IMAGE"].header).celestial
    star = motion.predicted_at(motion.star_at_j2000(entry["resolved"]), image_meta["mjd"])
    x, y = wcs.world_to_pixel(star)
    return star_peak(data, float(x), float(y))


def run(images, center, args, workers):
    block = args.block_kb * 1024
    started = time.perf_counter()
    outcomes = []
    with futures.ThreadPoolExecutor(max_workers=workers) as pool:
        pending = {pool.submit(read_region, s3_url(i["uri"]), center, args.size, block): i for i in images}
        for future in futures.as_completed(pending):
            meta = pending[future]
            try:
                outcomes.append((meta, future.result()))
            except Exception as error:
                outcomes.append((meta, {"ok": False, "error": f"{type(error).__name__}: {str(error)[:160]}"}))
    return outcomes, time.perf_counter() - started


def main():
    args = parse_args()
    detector = "SPHEREx-D" + args.detector.upper().lstrip("D")
    entry = motion.load_target(args.target)
    center = SkyCoord(entry["position_at_epoch"]["ra"] * u.deg, entry["position_at_epoch"]["dec"] * u.deg, frame="icrs")
    images = sorted((i for i in entry["images"] if i["detector"] == detector), key=lambda item: item["mjd"])
    if not images:
        raise SystemExit(f"No {detector} images for {args.target}")
    picks = [images[int(k)] for k in np.linspace(0, len(images) - 1, min(args.frames, len(images)))]

    print(f"Example S3 object: {s3_url(picks[0]['uri'])}")
    print(f"\nSequential read of {len(picks)} {detector} frames ({args.size} deg box, {args.block_kb} KB blocks):")
    sequential, sequential_wall = run(picks, center, args, workers=1)
    for meta, outcome in sorted(sequential, key=lambda item: item[0]["mjd"]):
        if not outcome["ok"]:
            print(f"  {meta['date'][:10]}  FAILED  {outcome['error']}")
            continue
        aws_peak = star_peak(outcome["image"], *outcome["star_px"])
        cut_peak = cached_cutout_peak(entry, meta, center, args.size, detector, args.target)
        match = "n/a" if cut_peak is None or aws_peak is None else ("identical" if np.isclose(aws_peak, cut_peak, rtol=1e-5) else f"DIFFERS ({aws_peak:.4g} vs {cut_peak:.4g})")
        print(f"  {meta['date'][:10]}  {outcome['seconds']:5.2f} s  (header {outcome['header_seconds']:.2f} s)  "
              f"box {outcome['shape'][0]}x{outcome['shape'][1]}  compressed={outcome['compressed']}  vs cutout: {match}")

    ok_times = [o["seconds"] for _, o in sequential if o["ok"]]
    print(f"Sequential: {len(ok_times)}/{len(picks)} ok, median {np.median(ok_times) if ok_times else float('nan'):.2f} s per frame, wall {sequential_wall:.1f} s")

    print(f"\nParallel read of the same {len(picks)} frames with {args.workers} workers:")
    parallel, parallel_wall = run(picks, center, args, workers=args.workers)
    failed = [o for _, o in parallel if not o["ok"]]
    print(f"Parallel: {len(picks) - len(failed)}/{len(picks)} ok, wall {parallel_wall:.1f} s "
          f"({parallel_wall / len(picks):.2f} s per frame effective)")
    for outcome in failed[:3]:
        print(f"  failed: {outcome['error']}")

    report = {
        "detector": detector,
        "frames": len(picks),
        "block_kb": args.block_kb,
        "sequential_median_s": float(np.median(ok_times)) if ok_times else None,
        "sequential_wall_s": sequential_wall,
        "parallel_workers": args.workers,
        "parallel_wall_s": parallel_wall,
        "parallel_failed": len(failed),
    }
    Path("spike_aws.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\nSaved spike_aws.json  (cutout service baseline from part 2: median 10.3 s per frame, 4 workers)")


if __name__ == "__main__":
    main()
