import { useState } from "react";
import Badge, { type Confidence } from "../Badge.tsx";
import { BOX, compact, extent, linear, passColour, ticks } from "../charts/chartKit.ts";
import type { LightCurveResponse } from "../../lib/api.ts";
import styles from "./Chart.module.css";

const PANEL = { ...BOX, height: 150, right: 20, top: 12 };

interface Hover {
  band: string;
  date: string;
  flux: number;
  error: number;
  snr: number;
  pass: number;
  suspect: boolean;
  x: number;
  y: number;
}

export default function LightCurve({
  data,
  loading,
  error,
}: {
  data: LightCurveResponse | null;
  loading: boolean;
  error: string | null;
}) {
  const [hover, setHover] = useState<Hover | null>(null);
  const bands = data?.bands ?? [];
  const passCount = Math.max(...bands.flatMap((b) => b.points.map((p) => p.pass_index)), 1);

  return (
    <section className={`panel ${styles.card}`} aria-label="Brightness over time">
      <div className={styles.head}>
        <div>
          <h2>Brightness over time</h2>
          <p className={styles.sub}>
            One panel per wavelength band, because SPHEREx changes wavelength between exposures of the same pass.
          </p>
        </div>
        {data ? <Badge confidence={data.confidence as Confidence} /> : null}
      </div>

      {error ? <p className={styles.note}>{error}</p> : null}
      {!error && !bands.length ? (
        <p className={styles.note}>{loading ? "Measuring every exposure…" : data?.summary ?? "No light curve yet."}</p>
      ) : null}

      {bands.length ? (
        <>
          <p className={styles.headline}>{data?.summary}</p>
          <div className={styles.bands}>
            {bands.map((band) => {
              const mjds = band.points.map((p) => p.mjd);
              const x = linear(extent(mjds, 0.05), [PANEL.left, PANEL.width - PANEL.right]);
              const y = linear(extent(band.points.map((p) => p.flux), 0.15), [PANEL.height - PANEL.bottom, PANEL.top]);
              const change = band.change_percent;
              const tone =
                change === null || band.change_sigma === null || Math.abs(band.change_sigma) < 3
                  ? styles.changeFlat
                  : change > 0
                    ? styles.changeUp
                    : styles.changeDown;
              return (
                <div key={band.label} className={styles.band}>
                  <div className={styles.bandHead}>
                    <span className="mono">{band.label}</span>
                    <span className={`${styles.change} ${tone}`}>
                      {change === null
                        ? "single pass"
                        : `${change > 0 ? "+" : ""}${change.toFixed(0)}% · ${band.change_sigma?.toFixed(1)}σ`}
                    </span>
                  </div>
                  <svg
                    viewBox={`0 0 ${PANEL.width} ${PANEL.height}`}
                    className={styles.plot}
                    role="img"
                    aria-label={`Flux against date in the ${band.label} band`}
                  >
                    {ticks(y.domain, 3).map((value) => (
                      <g key={value}>
                        <line x1={PANEL.left} x2={PANEL.width - PANEL.right} y1={y(value)} y2={y(value)} className={styles.grid} />
                        <text x={PANEL.left - 8} y={y(value) + 3.5} className={styles.tick} textAnchor="end">
                          {compact(value)}
                        </text>
                      </g>
                    ))}
                    {band.points.map((p) => {
                      const cx = x(p.mjd);
                      const cy = y(p.flux);
                      const colour = passColour(p.pass_index - 1, passCount);
                      return (
                        <g key={`${p.mjd}-${p.wavelength_um}`}>
                          <line
                            x1={cx}
                            x2={cx}
                            y1={y(p.flux - p.flux_err)}
                            y2={y(p.flux + p.flux_err)}
                            stroke={colour}
                            className={styles.errorBar}
                          />
                          <circle
                            cx={cx}
                            cy={cy}
                            r={2.8}
                            fill={p.suspect ? "var(--surface)" : colour}
                            stroke={colour}
                            className={styles.marker}
                          />
                          <circle
                            cx={cx}
                            cy={cy}
                            r={8}
                            fill="transparent"
                            onMouseEnter={() =>
                              setHover({
                                band: band.label,
                                date: p.date,
                                flux: p.flux,
                                error: p.flux_err,
                                snr: p.snr,
                                pass: p.pass_index,
                                suspect: p.suspect,
                                x: cx,
                                y: cy,
                              })
                            }
                            onMouseLeave={() => setHover(null)}
                          />
                        </g>
                      );
                    })}
                    <text x={PANEL.left} y={PANEL.height - 10} className={styles.tick}>
                      {band.points[0]?.date}
                    </text>
                    <text x={PANEL.width - PANEL.right} y={PANEL.height - 10} className={styles.tick} textAnchor="end">
                      {band.points.at(-1)?.date}
                    </text>
                    {hover && hover.band === band.label ? (
                      <g pointerEvents="none">
                        <rect
                          x={Math.min(hover.x + 10, PANEL.width - 150)}
                          y={Math.max(hover.y - 30, PANEL.top)}
                          width={140}
                          height={30}
                          rx={5}
                          className={styles.tooltip}
                        />
                        <text x={Math.min(hover.x + 18, PANEL.width - 142)} y={Math.max(hover.y - 18, PANEL.top + 12)} className={styles.tooltipText}>
                          {compact(hover.flux)} ± {compact(hover.error)}
                        </text>
                        <text x={Math.min(hover.x + 18, PANEL.width - 142)} y={Math.max(hover.y - 6, PANEL.top + 24)} className={styles.tooltipMuted}>
                          {hover.date} · pass {hover.pass} · S/N {hover.snr.toFixed(0)}
                          {hover.suspect ? " · suspect" : ""}
                        </text>
                      </g>
                    ) : null}
                  </svg>
                </div>
              );
            })}
          </div>

          <div className={styles.legend}>
            <span className={styles.legendItem}>
              <span className={styles.hollow} aria-hidden="true" />
              suspect: saturation flags, or part of the aperture blanked
            </span>
            <span className={styles.legendItem}>Points are shaded by pass, oldest darkest.</span>
          </div>

          {data?.notes.length ? (
            <ul className={styles.notes}>
              {data.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
