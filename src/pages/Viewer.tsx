import { useSearchParams } from "react-router-dom";
import FindingsPanel from "../components/viewer/FindingsPanel.tsx";
import Player from "../components/viewer/Player.tsx";
import ShareButtons from "../components/viewer/ShareButtons.tsx";
import { parseViewState, toSearchParams, type ViewState } from "../lib/viewState.ts";
import styles from "./Viewer.module.css";

export default function Viewer() {
  const [params, setParams] = useSearchParams();
  const view = parseViewState(params);

  function update(patch: Partial<ViewState>) {
    setParams(toSearchParams({ ...view, ...patch }), { replace: true });
  }

  const heading = view.target ?? (view.ra !== null && view.dec !== null ? "Custom position" : "No target selected");
  const position =
    view.ra !== null && view.dec !== null
      ? `RA ${view.ra.toFixed(4)}° · Dec ${view.dec >= 0 ? "+" : ""}${view.dec.toFixed(4)}°`
      : "Position resolves when the backend is connected";

  return (
    <main className={`container ${styles.page}`}>
      <div className={styles.titleRow}>
        <div className={styles.titleText}>
          <h1>{heading}</h1>
          <p className="mono">{position}</p>
        </div>
        <ShareButtons />
      </div>
      <div className={styles.layout}>
        <Player view={view} onChange={update} />
        <FindingsPanel />
      </div>
      <footer className={styles.footer}>
        Images: NASA/JPL-Caltech/IPAC, SPHEREx Quick Release via IRSA. Positions and proper motions: SIMBAD and Gaia DR3.
      </footer>
    </main>
  );
}
