import sys
import time

from astroquery.gaia import Gaia

RA, DEC = 269.4463, 4.7682
RADIUS_DEG = float(sys.argv[1]) if len(sys.argv) > 1 else 0.05

QUERY = (
    "SELECT source_id, ra, dec, pmra, pmdec, parallax, phot_g_mean_mag "
    "FROM gaiadr3.gaia_source "
    f"WHERE 1 = CONTAINS(POINT(ra, dec), CIRCLE({RA}, {DEC}, {RADIUS_DEG}))"
)

started = time.perf_counter()
table = Gaia.launch_job(QUERY).get_results()
elapsed = time.perf_counter() - started

print(f"{len(table)} Gaia DR3 sources within {RADIUS_DEG} deg in {elapsed:.1f} s")
table.sort("phot_g_mean_mag")
for row in table[:3]:
    print(f"  G {row['phot_g_mean_mag']:6.2f}  pmRA {row['pmra']:9.1f}  pmDec {row['pmdec']:9.1f} mas/yr  id {row['source_id']}")
