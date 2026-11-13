import Badge, { type Confidence } from "../Badge.tsx";
import type { MoverCandidate, MoversResponse } from "../../lib/api.ts";
import styles from "./Chart.module.css";

const BADGE: Record<MoverCandidate["label"], Confidence> = {
  unexplained: "candidate",
  known: "measured",
  unchecked: "marginal",
};

const HEADING: Record<MoverCandidate["label"], string> = {
  unexplained: "Unexplained candidate",
  known: "Known moving star",
  unchecked: "Moving, catalogue not checked",
};

export default function Movers({
  data,
  loading,
  error,
  selected,
  onSelect,
}: {
  data: MoversResponse | null;
  loading: boolean;
  error: string | null;
  selected: string | null;
  onSelect: (id: string | null) => void;
}) {
  const candidates = data?.candidates ?? [];

  return (
    <section className={`panel ${styles.card}`} aria-label="Mover search">
      <div className={styles.head}>
        <div>
          <h2>What moved in this field</h2>
          <p className={styles.sub}>
            Every source is linked across the passes and fitted with a straight line in time. Tracks are kept only when
            the motion is at least five times its own uncertainty.
          </p>
        </div>
        {data ? (
          <span className={`mono ${styles.sub}`}>
            {data.searched} detections · {candidates.length} moving
          </span>
        ) : null}
      </div>

      {error ? <p className={styles.note}>{error}</p> : null}
      {loading ? <p className={styles.note}>Searching every pass for sources, then linking them into tracks…</p> : null}

      {!loading && !error && !candidates.length ? (
        <p className={styles.note}>
          Nothing in this field moved fast enough to measure
          {data?.limit_arcsec_per_year ? ` — the limit here is about ${data.limit_arcsec_per_year}″ per year` : ""}. That
          is the expected result for most fields: a blank search is a result, not a failure.
        </p>
      ) : null}

      {candidates.length ? (
        <ul className={styles.movers}>
          {candidates.map((candidate) => {
            const id = `${candidate.ra.toFixed(5)},${candidate.dec.toFixed(5)}`;
            const active = selected === id;
            return (
              <li key={id}>
                <button
                  type="button"
                  className={styles.mover}
                  data-active={active}
                  aria-pressed={active}
                  onClick={() => onSelect(active ? null : id)}
                >
                  <span className={styles.moverHead}>
                    <Badge confidence={BADGE[candidate.label]} />
                    <span className={styles.moverTitle}>{HEADING[candidate.label]}</span>
                  </span>
                  <span className={`mono ${styles.moverSpeed}`}>
                    {candidate.speed_arcsec_per_year.toFixed(2)} ± {candidate.speed_error_arcsec_per_year.toFixed(2)}″/yr
                    <span className={styles.moverQuiet}> at {candidate.position_angle_deg.toFixed(0)}° PA</span>
                  </span>
                  <span className={`mono ${styles.moverQuiet}`}>
                    {candidate.ra.toFixed(5)}°, {candidate.dec >= 0 ? "+" : ""}
                    {candidate.dec.toFixed(5)}° · {candidate.significance.toFixed(0)}σ · S/N{" "}
                    {candidate.snr.toFixed(0)}
                  </span>
                  <span className={styles.moverWhy}>
                    {candidate.explanation}
                    {candidate.catalogue_speed_arcsec_per_year
                      ? ` It moves ${candidate.catalogue_speed_arcsec_per_year.toFixed(2)}″ per year in the catalogue.`
                      : ""}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}

      {data?.rejected && Object.keys(data.rejected).length ? (
        <p className={`mono ${styles.sub}`}>
          Set aside: {Object.entries(data.rejected).map(([reason, count]) => `${count} ${reason}`).join(" · ")}
        </p>
      ) : null}

      {data?.notes.length ? (
        <ul className={styles.notes}>
          {data.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
