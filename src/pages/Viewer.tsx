import { useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import FindingsPanel from "../components/viewer/FindingsPanel.tsx";
import LightCurve from "../components/viewer/LightCurve.tsx";
import Player from "../components/viewer/Player.tsx";
import ShareButtons from "../components/viewer/ShareButtons.tsx";
import Spectrum from "../components/viewer/Spectrum.tsx";
import {
  fetchDifference,
  fetchFrames,
  fetchLightCurve,
  fetchSpectrum,
  type FramesResponse,
  type LightCurveResponse,
  type SpectrumResponse,
} from "../lib/api.ts";
import { useAsync } from "../lib/useAsync.ts";
import { parseViewState, queryKey, targetQuery, toSearchParams, type Panel, type ViewState } from "../lib/viewState.ts";
import styles from "./Viewer.module.css";

const PANELS: { id: Panel; label: string }[] = [
  { id: "findings", label: "Image only" },
  { id: "spectrum", label: "Spectrum" },
  { id: "brightness", label: "Brightness" },
];

export default function Viewer() {
  const [params, setParams] = useSearchParams();
  const view = parseViewState(params);
  const query = targetQuery(view);
  const key = queryKey(view);
  const hasTarget = Boolean(view.target || (view.ra !== null && view.dec !== null));

  const update = useCallback(
    (patch: Partial<ViewState>) => {
      setParams(toSearchParams({ ...parseViewState(params), ...patch }), { replace: true });
    },
    [params, setParams],
  );

  const frames = useAsync<FramesResponse>((signal) => fetchFrames(query, signal), key, hasTarget);
  const passCount = frames.data?.passes.length ?? 0;
  const pair = view.pair ?? [1, Math.max(passCount, 1)];
  const wantDifference = view.mode === "difference" && passCount >= 2;
  const difference = useAsync<{ image: string }>(
    (signal) => fetchDifference(query, Math.min(...pair), Math.max(...pair), signal),
    `${key}|diff|${pair.join("-")}`,
    wantDifference,
  );

  const pickKey = view.pick ? `${view.pick.x.toFixed(2)},${view.pick.y.toFixed(2)}` : "target";
  const spectrum = useAsync<SpectrumResponse>(
    (signal) => fetchSpectrum(query, view.pick, signal),
    `${key}|spec|${pickKey}`,
    hasTarget && view.panel === "spectrum" && !frames.loading,
  );
  const brightness = useAsync<LightCurveResponse>(
    (signal) => fetchLightCurve(query, signal),
    `${key}|lc`,
    hasTarget && view.panel === "brightness" && !frames.loading,
  );

  const target = frames.data?.target;
  const heading = target?.name ?? view.target ?? (hasTarget ? "Custom position" : "No target selected");
  const position = target
    ? `RA ${target.ra.toFixed(4)}° · Dec ${target.dec >= 0 ? "+" : ""}${target.dec.toFixed(4)}° · ${target.epoch}`
    : view.ra !== null && view.dec !== null
      ? `RA ${view.ra.toFixed(4)}° · Dec ${view.dec >= 0 ? "+" : ""}${view.dec.toFixed(4)}°`
      : "Search for a name, or paste coordinates";

  return (
    <main className={`container ${styles.page}`}>
      <div className={styles.titleRow}>
        <div className={styles.titleText}>
          <h1>{heading}</h1>
          <p className="mono">{position}</p>
        </div>
        <ShareButtons />
      </div>

      {target && target.source !== "user coordinates" ? (
        <div className={`panel ${styles.banner}`}>
          <span>
            Proper motion <span className={`mono ${styles.bannerStrong}`}>{target.pmra.toFixed(1)}</span>,{" "}
            <span className={`mono ${styles.bannerStrong}`}>{target.pmdec.toFixed(1)}</span> mas/yr
          </span>
          {target.parallax ? (
            <span>
              Distance <span className={`mono ${styles.bannerStrong}`}>{(1000 / target.parallax).toFixed(2)} pc</span>
            </span>
          ) : null}
          <span>
            Astrometry from <span className={styles.bannerStrong}>{target.source}</span>
          </span>
          {frames.data ? (
            <span>
              {frames.data.frames.filter((f) => f.status === "used").length} exposures ·{" "}
              {frames.data.releases.join(", ").toUpperCase()}
            </span>
          ) : null}
        </div>
      ) : null}

      <div className={styles.layout}>
        <Player
          view={view}
          onChange={update}
          frames={frames.data}
          loading={frames.loading}
          error={frames.error}
          status={frames.status}
          elapsedMs={frames.elapsedMs}
          differenceImage={difference.data?.image ?? frames.data?.difference_image ?? null}
        />
        <FindingsPanel frames={frames.data} />
      </div>

      <section className={styles.analysis}>
        <div className={styles.panelTabs} role="tablist" aria-label="Analysis">
          {PANELS.map((panel) => (
            <button
              key={panel.id}
              type="button"
              role="tab"
              aria-selected={view.panel === panel.id}
              className="btn toggle"
              onClick={() => update({ panel: panel.id })}
            >
              {panel.label}
            </button>
          ))}
        </div>
        {view.panel === "spectrum" ? (
          <Spectrum
            data={spectrum.data}
            loading={spectrum.loading}
            error={spectrum.error}
            picked={Boolean(view.pick)}
            onClear={() => update({ pick: null })}
          />
        ) : null}
        {view.panel === "brightness" ? (
          <LightCurve data={brightness.data} loading={brightness.loading} error={brightness.error} />
        ) : null}
        {view.panel === "findings" ? (
          <p className={styles.analysisHint}>
            The findings panel is beside the image. Open <strong>Spectrum</strong> to measure flux against wavelength in
            each pass, or <strong>Brightness</strong> to follow one wavelength band over time.
          </p>
        ) : null}
      </section>

      <footer className={styles.footer}>
        Images: NASA/JPL-Caltech/IPAC, SPHEREx Quick Release via IRSA. Positions and proper motions: SIMBAD and Gaia
        DR3. Pixels read from the SPHEREx public mirror on AWS Open Data.
      </footer>
    </main>
  );
}
