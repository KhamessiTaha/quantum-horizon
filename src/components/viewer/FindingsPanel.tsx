import Badge from "../Badge.tsx";
import styles from "./FindingsPanel.module.css";

const QUALITY_ROWS = ["Releases", "Pixel scale", "Zodiacal light", "Flags at the source"];

export default function FindingsPanel() {
  return (
    <aside aria-label="Findings" className={styles.aside}>
      <section className={`panel ${styles.card}`}>
        <div className={styles.cardHead}>
          <h2>Motion</h2>
          <Badge confidence="pending" />
        </div>
        <div className={styles.headline}>
          <span className={`mono ${styles.value}`}>—</span>
          <span className={styles.sub}>measured motion, with its uncertainty</span>
        </div>
        <div className={styles.compare}>
          <div>
            <span className={styles.term}>Catalog prediction</span>
            <span className={`mono ${styles.predicted}`}>—</span>
          </div>
          <div>
            <span className={styles.term}>Difference</span>
            <span className="mono">—</span>
          </div>
        </div>
        <p className={styles.note}>
          A plain-language explanation of the result appears here, including how far the data can be trusted.
        </p>
      </section>

      <section className={`panel ${styles.card}`}>
        <h2>Per pass</h2>
        <p className={styles.note}>Dates, frame counts and measured offsets for each pass.</p>
      </section>

      <section className={`panel ${styles.card}`}>
        <h2>Data quality</h2>
        <dl className={styles.quality}>
          {QUALITY_ROWS.map((row) => (
            <div key={row} className={styles.qualityRow}>
              <dt>{row}</dt>
              <dd className="mono">—</dd>
            </div>
          ))}
        </dl>
      </section>
    </aside>
  );
}
