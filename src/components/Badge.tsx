import styles from "./Badge.module.css";

export type Confidence = "measured" | "marginal" | "not-measurable" | "indicative" | "candidate" | "pending";

const LABELS: Record<Confidence, string> = {
  measured: "Measured",
  marginal: "Marginal",
  "not-measurable": "Not measurable yet",
  indicative: "Indicative",
  candidate: "Unexplained candidate",
  pending: "Awaiting data",
};

export default function Badge({ confidence }: { confidence: Confidence }) {
  return (
    <span className={`${styles.badge} ${styles[confidence]}`}>
      <span className={styles.dot} aria-hidden="true" />
      {LABELS[confidence]}
    </span>
  );
}
