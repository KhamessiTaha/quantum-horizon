import { useEffect, useState } from "react";
import { DETECTORS, FOV_LIMITS, type ViewState } from "../../lib/viewState.ts";
import Timeline, { type TimelinePass } from "./Timeline.tsx";
import styles from "./Player.module.css";

const PLACEHOLDER_PASSES: TimelinePass[] = [
  { label: "Pass 1", start: 0.05, width: 0.03, frames: null },
  { label: "Pass 2", start: 0.47, width: 0.03, frames: null },
  { label: "Pass 3", start: 0.86, width: 0.05, frames: null },
];

const FRAME_MS = 900;
const FOV_OPTIONS = [0.03, 0.06, 0.1, 0.2].filter((v) => v >= FOV_LIMITS.min && v <= FOV_LIMITS.max);

interface PlayerProps {
  view: ViewState;
  onChange: (patch: Partial<ViewState>) => void;
}

export default function Player({ view, onChange }: PlayerProps) {
  const passes = PLACEHOLDER_PASSES;
  const [current, setCurrent] = useState(0);
  const [playing, setPlaying] = useState(true);
  const blink = view.mode === "blink";
  const isPlaying = playing && blink;

  useEffect(() => {
    if (!isPlaying) return;
    const timer = window.setInterval(() => setCurrent((i) => (i + 1) % passes.length), FRAME_MS);
    return () => window.clearInterval(timer);
  }, [isPlaying, passes.length]);

  const detector = DETECTORS.find((d) => d.id === view.detector) ?? DETECTORS[1];
  const frameLabel = blink ? `${passes[current].label} · date pending` : `${passes.at(-1)?.label} − ${passes[0].label}`;

  return (
    <section aria-label="Image player" className={styles.player}>
      <div className={styles.toolbar}>
        <div role="group" aria-label="View mode" className={styles.segmented}>
          <button type="button" aria-pressed={blink} onClick={() => onChange({ mode: "blink" })}>
            Blink
          </button>
          <button
            type="button"
            aria-pressed={!blink}
            onClick={() => {
              setPlaying(false);
              onChange({ mode: "difference" });
            }}
          >
            Difference
          </button>
        </div>
        <div role="group" aria-label="Detector" className={styles.chips}>
          {DETECTORS.map((d) => (
            <button
              key={d.id}
              type="button"
              className={`btn toggle mono ${styles.chip}`}
              aria-pressed={d.id === view.detector}
              title={d.rangeMicron}
              onClick={() => onChange({ detector: d.id })}
            >
              {d.id}
            </button>
          ))}
        </div>
        <label className={`mono ${styles.fov}`}>
          FOV
          <select value={view.fovDeg} onChange={(e) => onChange({ fovDeg: Number(e.target.value) })}>
            {FOV_OPTIONS.map((v) => (
              <option key={v} value={v}>
                {v}°
              </option>
            ))}
          </select>
          <span>· {detector.rangeMicron}</span>
        </label>
      </div>

      <div className={styles.stage}>
        <div className={styles.frame} role="img" aria-label={`${frameLabel}, image placeholder`}>
          <span className={`mono ${styles.frameLabel}`}>{frameLabel}</span>
          <span className={`mono ${styles.compass}`} aria-hidden="true">
            N ↑ E ←
          </span>
          <span className={styles.empty}>Frames appear here once the backend is connected</span>
        </div>
        <div className={styles.legend}>
          {blink ? (
            <>
              <span className={styles.legendItem}>
                <span className={styles.crossMark} aria-hidden="true" />
                Predicted from catalog motion
              </span>
              <span className={styles.legendItem}>
                <span className={styles.ringMark} aria-hidden="true" />
                Measured in this pass
              </span>
              <span>Each frame is the median of one detector's exposures in a pass, aligned to a common grid.</span>
            </>
          ) : (
            <>
              <span className={styles.legendItem}>
                <span className={styles.swatch} style={{ background: "var(--predicted)" }} aria-hidden="true" />
                Brighter now: where a source arrived
              </span>
              <span className={styles.legendItem}>
                <span className={styles.swatch} style={{ background: "var(--accent)" }} aria-hidden="true" />
                Fainter now: where it left
              </span>
              <span>Sources that did not move cancel out; a two-colour pair means motion.</span>
            </>
          )}
        </div>
      </div>

      <div className={styles.controls}>
        <button
          type="button"
          className={styles.play}
          aria-label={isPlaying ? "Pause" : "Play"}
          onClick={() => {
            if (!blink) onChange({ mode: "blink" });
            setPlaying(!isPlaying);
          }}
        >
          {isPlaying ? (
            <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
              <path d="M4 2V14M12 2V14" stroke="currentColor" strokeWidth="2.5" />
            </svg>
          ) : (
            <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
              <path d="M4 2L14 8L4 14Z" fill="currentColor" />
            </svg>
          )}
        </button>
        {passes.map((p, i) => (
          <button
            key={p.label}
            type="button"
            className="btn toggle mono"
            aria-pressed={blink && i === current}
            onClick={() => {
              setPlaying(false);
              setCurrent(i);
              if (!blink) onChange({ mode: "blink" });
            }}
          >
            {p.label}
          </button>
        ))}
        <span className={styles.speed}>{(FRAME_MS / 1000).toFixed(1)} s per pass</span>
      </div>

      <Timeline passes={passes} current={blink ? current : null} />
    </section>
  );
}
