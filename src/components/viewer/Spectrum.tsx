import { useState } from "react";
import Badge from "../Badge.tsx";
import { BOX, compact, extent, linear, passColour, path, ticks } from "../charts/chartKit.ts";
import type { SpectrumResponse } from "../../lib/api.ts";
import styles from "./Chart.module.css";

interface SpectrumProps {
  data: SpectrumResponse | null;
  loading: boolean;
  error: string | null;
  picked: boolean;
  onClear: () => void;
}

interface Hover {
  label: string;
  wavelength: number;
  flux: number;
  error: number;
  frames: number;
  suspect: boolean;
  x: number;
  y: number;
}

export default function Spectrum({ data, loading, error, picked, onClear }: SpectrumProps) {
  const [hover, setHover] = useState<Hover | null>(null);
  const series = (data?.series ?? []).filter((s) => s.points.length > 0);
  const wavelengths = series.flatMap((s) => s.points.map((p) => p.wavelength_um));
  const fluxes = series.flatMap((s) => s.points.map((p) => p.flux));
  const x = linear(extent(wavelengths, 0.04), [BOX.left, BOX.width - BOX.right]);
  const y = linear(extent(fluxes, 0.12), [BOX.height - BOX.bottom, BOX.top]);

  return (
    <section className={`panel ${styles.card}`} aria-label="Spectrum">
      <div className={styles.head}>
        <div>
          <h2>Spectrum per pass</h2>
          <p className={styles.sub}>
            {data
              ? `${data.detector} · ${data.aperture_arcsec}″ aperture at ${data.ra.toFixed(4)}°, ${data.dec >= 0 ? "+" : ""}${data.dec.toFixed(4)}°`
              : "Click a source in the image to measure its spectrum."}
          </p>
        </div>
        {picked ? (
          <button type="button" className="btn" onClick={onClear}>
            Back to the target
          </button>
        ) : null}
      </div>

      {error ? <p className={styles.note}>{error}</p> : null}
      {!error && !series.length ? (
        <p className={styles.note}>
          {loading ? "Measuring every frame at this position…" : "No usable flux at this position on this detector."}
        </p>
      ) : null}

      {series.length ? (
        <>
          <div className={styles.plotWrap}>
            <svg viewBox={`0 0 ${BOX.width} ${BOX.height}`} className={styles.plot} role="img" aria-label="Flux against wavelength, one line per pass">
              {ticks(y.domain, 4).map((value) => (
                <g key={`y${value}`}>
                  <line x1={BOX.left} x2={BOX.width - BOX.right} y1={y(value)} y2={y(value)} className={styles.grid} />
                  <text x={BOX.left - 8} y={y(value) + 3.5} className={styles.tick} textAnchor="end">
                    {compact(value)}
                  </text>
                </g>
              ))}
              {ticks(x.domain, 4).map((value) => (
                <text key={`x${value}`} x={x(value)} y={BOX.height - 12} className={styles.tick} textAnchor="middle">
                  {value.toFixed(2)}
                </text>
              ))}
              <text x={BOX.left - 38} y={BOX.top + 6} className={styles.axisLabel}>
                MJy/sr
              </text>
              <text x={(BOX.left + BOX.width - BOX.right) / 2} y={BOX.height - 1} className={styles.axisLabel} textAnchor="middle">
                wavelength, µm
              </text>

              {series.map((s, index) => {
                const colour = passColour(index, series.length);
                const points = s.points.map((p) => ({ x: x(p.wavelength_um), y: y(p.flux) }));
                const last = points.at(-1);
                return (
                  <g key={s.pass_index}>
                    <path d={path(points)} fill="none" stroke={colour} className={styles.line} />
                    {s.points.map((p, i) => (
                      <g key={p.wavelength_um}>
                        <line
                          x1={points[i].x}
                          x2={points[i].x}
                          y1={y(p.flux - p.flux_err)}
                          y2={y(p.flux + p.flux_err)}
                          stroke={colour}
                          className={styles.errorBar}
                        />
                        <circle
                          cx={points[i].x}
                          cy={points[i].y}
                          r={2.6}
                          fill={p.suspect ? "var(--surface)" : colour}
                          stroke={colour}
                          className={styles.marker}
                        />
                        <circle
                          cx={points[i].x}
                          cy={points[i].y}
                          r={7}
                          fill="transparent"
                          onMouseEnter={() =>
                            setHover({
                              label: s.label,
                              wavelength: p.wavelength_um,
                              flux: p.flux,
                              error: p.flux_err,
                              frames: p.frames,
                              suspect: p.suspect,
                              x: points[i].x,
                              y: points[i].y,
                            })
                          }
                          onMouseLeave={() => setHover(null)}
                        />
                      </g>
                    ))}
                    {last ? (
                      <text x={last.x + 8} y={last.y + 3.5} className={styles.directLabel}>
                        Pass {s.pass_index}
                      </text>
                    ) : null}
                  </g>
                );
              })}

              {hover ? (
                <g pointerEvents="none">
                  <line x1={hover.x} x2={hover.x} y1={BOX.top} y2={BOX.height - BOX.bottom} className={styles.crosshair} />
                  <rect
                    x={Math.min(hover.x + 10, BOX.width - 150)}
                    y={Math.max(hover.y - 34, BOX.top)}
                    width={142}
                    height={hover.suspect ? 46 : 34}
                    rx={5}
                    className={styles.tooltip}
                  />
                  <text x={Math.min(hover.x + 18, BOX.width - 142)} y={Math.max(hover.y - 20, BOX.top + 14)} className={styles.tooltipText}>
                    {hover.wavelength.toFixed(3)} µm · {compact(hover.flux)} ± {compact(hover.error)}
                  </text>
                  <text x={Math.min(hover.x + 18, BOX.width - 142)} y={Math.max(hover.y - 8, BOX.top + 26)} className={styles.tooltipMuted}>
                    {hover.label} · {hover.frames} frame{hover.frames === 1 ? "" : "s"}
                  </text>
                  {hover.suspect ? (
                    <text x={Math.min(hover.x + 18, BOX.width - 142)} y={Math.max(hover.y + 4, BOX.top + 38)} className={styles.tooltipMuted}>
                      part of the aperture blanked
                    </text>
                  ) : null}
                </g>
              ) : null}
            </svg>
          </div>

          <div className={styles.legend}>
            {series.map((s, index) => (
              <span key={s.pass_index} className={styles.legendItem}>
                <span className={styles.dot} style={{ background: passColour(index, series.length) }} aria-hidden="true" />
                {s.label}
              </span>
            ))}
            <span className={styles.legendItem}>
              <span className={styles.hollow} aria-hidden="true" />
              suspect: part of the aperture blanked
            </span>
          </div>

          <details className={styles.table}>
            <summary className={styles.summary}>Table of values</summary>
            <table>
              <thead>
                <tr>
                  <th>Pass</th>
                  <th>µm</th>
                  <th>MJy/sr</th>
                  <th>±</th>
                  <th>Frames</th>
                </tr>
              </thead>
              <tbody>
                {series.flatMap((s) =>
                  s.points.map((p) => (
                    <tr key={`${s.pass_index}-${p.wavelength_um}`}>
                      <td className="mono">{s.pass_index}</td>
                      <td className="mono">{p.wavelength_um.toFixed(3)}</td>
                      <td className="mono">{compact(p.flux)}</td>
                      <td className="mono">{compact(p.flux_err)}</td>
                      <td className="mono">{p.frames}</td>
                    </tr>
                  )),
                )}
              </tbody>
            </table>
          </details>

          {data?.notes.length ? (
            <ul className={styles.notes}>
              {data.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          ) : null}
          {series.some((s) => s.points.some((p) => p.suspect)) ? <Badge confidence="indicative" /> : null}
        </>
      ) : null}
    </section>
  );
}
