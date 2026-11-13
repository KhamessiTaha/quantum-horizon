import { fetchFlagReference, type FlagReference } from "../lib/api.ts";
import { useAsync } from "../lib/useAsync.ts";
import styles from "./Methods.module.css";

const TREATMENT_ORDER = ["pixel excluded", "kept, brightness indicative only", "kept, reported as possible contamination", "informational"];

const CONFIDENCE = [
  ["Measured", "At least three frames fitted, signal-to-noise above 5, frames agreeing within two pixels, and a shift larger than three times its own uncertainty."],
  ["Marginal", "A detection, but too faint or too scattered for a position to be trusted. No motion is claimed."],
  ["Below the noise", "Both passes measured well, but the shift between them is smaller than three times its uncertainty. The star may still be moving; this baseline cannot show it."],
  ["Not measurable yet", "No usable detection on this detector. Try another detector, or wait for more SPHEREx passes."],
  ["Indicative", "The source saturates the detector, so brightness is a lower limit. Positions can still be measured from the unsaturated wings."],
];

export default function Methods() {
  const flags = useAsync<FlagReference>((signal) => fetchFlagReference(signal), "flags");
  const grouped = TREATMENT_ORDER.map((treatment) => ({
    treatment,
    bits: (flags.data?.bits ?? []).filter((b) => b.treatment === treatment),
  })).filter((group) => group.bits.length);

  return (
    <main className={`container ${styles.page}`}>
      <header className={styles.head}>
        <h1>How a blink becomes a measurement</h1>
        <p className={styles.lead}>
          Every number this tool shows comes from SPHEREx pixels, carries an uncertainty, and is labelled with how far
          it can be trusted. This page is the method behind that, and the places where it stops.
        </p>
      </header>

      <section className={styles.section}>
        <h2>From archive to frame</h2>
        <ol className={styles.steps}>
          <li>
            <strong>Find.</strong> IRSA's table access service is asked which SPHEREx spectral images contain the
            position. The list is stored, so a position that has been seen once still works when the archive is down.
          </li>
          <li>
            <strong>Read.</strong> Only the pixels around the target are read, straight from the SPHEREx mirror on AWS
            Open Data, in parallel, with IRSA's cutout service as fallback. A full image is about 70 MB; what we need
            is a few kilobytes.
          </li>
          <li>
            <strong>Clean.</strong> Unusable pixels are masked by their quality flags, and the modelled zodiacal light
            is subtracted. It is not subtracted in the delivered images, so this step is ours.
          </li>
          <li>
            <strong>Align.</strong> Every frame is reprojected onto one tangent-plane grid. Without this, differences
            between each frame's own astrometry would look exactly like motion.
          </li>
          <li>
            <strong>Stack.</strong> Exposures are median-stacked per detector, per pass. SPHEREx images a position many
            times in a pass, each at a different wavelength, so frames are never mixed across detectors.
          </li>
        </ol>
      </section>

      <section className={styles.section}>
        <h2>From frame to number</h2>
        <p className={styles.body}>
          A position is fitted on every frame inside a seven-pixel box, and again on the stack of the pass, which
          reaches a higher signal-to-noise and fills in pixels that saturation blanked. Frames below signal-to-noise 3,
          or disagreeing with the rest of their pass by more than three times the scatter, are rejected and counted in
          the per-pass table. The uncertainty on each pass position comes from leaving each frame out in turn and
          seeing how far the answer moves.
        </p>
        <p className={styles.body}>
          Motion is the distance between the first and last pass that produced a position, compared with the same two
          dates propagated from the catalog. Brightness is aperture photometry inside narrow wavelength bands, because
          SPHEREx changes wavelength between exposures and a wider band would show the filter moving rather than the
          star.
        </p>
        <dl className={styles.confidence}>
          {CONFIDENCE.map(([label, meaning]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{meaning}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className={styles.section}>
        <h2>Quality flags, and what we do with each</h2>
        <p className={styles.body}>
          A bright star's own pixels carry TRANSIENT, OVERFLOW, SUR_ERROR, SOURCE and BLOOM together. Rejecting those
          deletes the star: in our first run, every QR3 frame of Barnard's Star lost it and the fit landed on noise, 27
          arcseconds against a predicted 10.3. So flags are split by what they actually mean.
        </p>
        {flags.error ? <p className={styles.body}>The flag reference could not be loaded: {flags.error}</p> : null}
        <div className={styles.flagGroups}>
          {grouped.map((group) => (
            <div key={group.treatment} className={`panel ${styles.flagGroup}`}>
              <h3>{group.treatment}</h3>
              <ul>
                {group.bits.map((bit) => (
                  <li key={bit.name}>
                    <code>{bit.name}</code>
                    <span className={`mono ${styles.bit}`}>bit {bit.bit}</span>
                    {bit.meaning ? <span className={styles.meaning}>{bit.meaning}</span> : null}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        {flags.data ? (
          <p className={styles.fine}>
            {flags.data.transient_rule} {flags.data.source}
          </p>
        ) : null}
      </section>

      <section className={styles.section}>
        <h2>Where this stops</h2>
        <ul className={styles.limits}>
          <li>
            <strong>Slow movers.</strong> One year of SPHEREx finds objects moving faster than roughly 6 arcseconds a
            year when bright. Below that, the motion is smaller than the measurement can resolve, and the tool says so
            rather than drawing an arrow.
          </li>
          <li>
            <strong>Distant Solar System bodies.</strong> They would not appear in the mover search. The Earth's own
            orbit swings a far object hundreds of arcseconds between passes, far outside the search field.
          </li>
          <li>
            <strong>Saturated stars.</strong> Their cores carry no usable values, so no brightness is reported for
            them. Positions still work, measured from the wings.
          </li>
          <li>
            <strong>Close pairs.</strong> Epsilon Indi B is two brown dwarfs under an arcsecond apart; SPHEREx sees one
            source. RW Aurigae is a binary about 1.4 arcseconds apart, also seen as one.
          </li>
          <li>
            <strong>Across releases.</strong> QR2 and QR3 do not overlap. Brightness compared across that boundary
            carries the flux-correction caveat from the release notes.
          </li>
        </ul>
      </section>

      <section className={styles.section}>
        <h2>Data</h2>
        <p className={styles.body}>
          SPHEREx Quick Release spectral images: NASA/JPL-Caltech/IPAC, via the NASA/IPAC Infrared Science Archive and
          the SPHEREx mirror on AWS Open Data. Positions and proper motions: SIMBAD (CDS) and Gaia DR3 (ESA). Context
          imagery: Aladin Lite (CDS) serving WISE, 2MASS and DSS2. Flag definitions: the SPHEREx Explanatory Supplement
          and the IRSA Spectrophotometry Tool documentation.
        </p>
        <p className={styles.fine}>Results are labelled measurements or candidates, never discoveries.</p>
      </section>
    </main>
  );
}
