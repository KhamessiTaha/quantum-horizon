import styles from "./Timeline.module.css";

export interface TimelinePass {
  label: string;
  start: number;
  width: number;
  frames: number | null;
}

export default function Timeline({ passes, current }: { passes: TimelinePass[]; current: number | null }) {
  const totalFrames = passes.every((p) => p.frames !== null) ? passes.reduce((s, p) => s + (p.frames ?? 0), 0) : null;
  return (
    <div className={`panel ${styles.timeline}`}>
      <div className={styles.head}>
        <span>Observations over time</span>
        <span className="mono">{totalFrames === null ? "frames pending" : `${totalFrames} frames`}</span>
      </div>
      <div className={styles.track}>
        {passes.map((p, i) => (
          <div
            key={p.label}
            className={styles.pass}
            data-active={i === current}
            style={{ left: `${p.start * 100}%`, width: `${Math.max(p.width * 100, 1.5)}%` }}
          >
            <span className={`mono ${styles.passLabel}`}>{p.frames === null ? p.label : `${p.frames} frames`}</span>
          </div>
        ))}
      </div>
      <div className={`mono ${styles.axis}`}>
        <span>start</span>
        <span>dates appear once frames load</span>
        <span>latest</span>
      </div>
    </div>
  );
}
