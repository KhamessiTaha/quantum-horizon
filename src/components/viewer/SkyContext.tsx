import { useEffect, useRef, useState } from "react";
import styles from "./Chart.module.css";

const ALADIN_SCRIPT = "https://aladin.cds.unistra.fr/AladinLite/api/v3/latest/aladin.js";

interface AladinApi {
  init: Promise<void>;
  aladin: (element: HTMLElement, options: Record<string, unknown>) => AladinInstance;
}

interface AladinInstance {
  setImageSurvey: (survey: string) => void;
  addCatalog: (catalog: unknown) => void;
  catalogFromSimbad?: (target: string, radius: number, options: Record<string, unknown>) => unknown;
}

declare global {
  interface Window {
    A?: AladinApi;
  }
}

function load(): Promise<AladinApi> {
  if (window.A) return Promise.resolve(window.A);
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${ALADIN_SCRIPT}"]`);
    const script = existing ?? document.createElement("script");
    script.addEventListener("load", () => (window.A ? resolve(window.A) : reject(new Error("Aladin did not load"))));
    script.addEventListener("error", () => reject(new Error("the CDS server could not be reached")));
    if (!existing) {
      script.src = ALADIN_SCRIPT;
      script.async = true;
      document.head.append(script);
    }
  });
}

/** Where this field sits in the wider sky, on survey imagery served by CDS. */
export default function SkyContext({ ra, dec, fovDeg, name }: { ra: number; dec: number; fovDeg: number; name: string }) {
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [survey, setSurvey] = useState("CDS/P/allWISE/color");
  const holder = useRef<HTMLDivElement>(null);
  const instance = useRef<AladinInstance | null>(null);

  useEffect(() => {
    if (!open || !holder.current || instance.current) return;
    let cancelled = false;
    load()
      .then(async (api) => {
        await api.init;
        if (cancelled || !holder.current) return;
        instance.current = api.aladin(holder.current, {
          survey,
          target: `${ra} ${dec}`,
          fov: Math.max(fovDeg * 6, 0.3),
          cooFrame: "ICRS",
          showReticle: true,
          showCooGrid: false,
          showFullscreenControl: false,
          showLayersControl: false,
          showGotoControl: false,
        });
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "could not load the sky map");
      });
    return () => {
      cancelled = true;
    };
  }, [open, ra, dec, fovDeg, survey]);

  useEffect(() => {
    instance.current?.setImageSurvey(survey);
  }, [survey]);

  return (
    <section className={`panel ${styles.card}`} aria-label="Sky context">
      <div className={styles.head}>
        <div>
          <h2>Where this is in the sky</h2>
          <p className={styles.sub}>
            {name} on all-sky survey imagery, for context around the {(fovDeg * 60).toFixed(1)}′ SPHEREx field.
          </p>
        </div>
        <button type="button" className="btn" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
          {open ? "Hide map" : "Show map"}
        </button>
      </div>
      {open ? (
        <>
          <div className={styles.legend}>
            {[
              ["CDS/P/allWISE/color", "WISE (3.4–22 µm)"],
              ["CDS/P/2MASS/color", "2MASS (1.2–2.2 µm)"],
              ["CDS/P/DSS2/color", "DSS2 (visible)"],
            ].map(([id, label]) => (
              <button
                key={id}
                type="button"
                className="btn toggle mono"
                aria-pressed={survey === id}
                onClick={() => setSurvey(id)}
              >
                {label}
              </button>
            ))}
          </div>
          {error ? (
            <p className={styles.note}>
              The sky map could not load: {error}. Everything else on this page works without it, because it comes from
              IRSA and the AWS mirror rather than from CDS.
            </p>
          ) : (
            <div ref={holder} className={styles.sky} />
          )}
          <p className={styles.sub}>Imagery: CDS/Strasbourg (Aladin Lite), WISE, 2MASS and DSS2 hierarchical surveys.</p>
        </>
      ) : null}
    </section>
  );
}
