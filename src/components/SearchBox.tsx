import { useId, useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { FOV_LIMITS, parseQuery, parseViewState, toSearchParams } from "../lib/viewState.ts";
import styles from "./SearchBox.module.css";

export default function SearchBox({ compact = false }: { compact?: boolean }) {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const current = parseViewState(params);
  const initial = current.target ?? (current.ra !== null && current.dec !== null ? `${current.ra} ${current.dec}` : "");
  const [query, setQuery] = useState(initial);
  const inputId = useId();
  const hintId = useId();

  function submit(event: FormEvent) {
    event.preventDefault();
    const parsed = parseQuery(query);
    if (!parsed.target && parsed.ra === null) return;
    const next = toSearchParams({
      ...parsed,
      fovDeg: compact ? current.fovDeg : FOV_LIMITS.defaultDeg,
      detector: compact ? current.detector : "D2",
      mode: "blink",
    });
    navigate(`/view?${next.toString()}`);
  }

  return (
    <form role="search" onSubmit={submit} className={compact ? styles.compact : styles.form}>
      <label htmlFor={inputId} className={compact ? "visually-hidden" : styles.label}>
        Target name or coordinates (RA, Dec in degrees)
      </label>
      <div className={styles.row}>
        <input
          id={inputId}
          className={`mono ${styles.input}`}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Barnard's Star, or 269.4463 4.7682"
          aria-describedby={compact ? undefined : hintId}
          autoComplete="off"
          spellCheck={false}
        />
        <button type="submit" className="btn btn-primary">
          {compact ? "Go" : "Blink it"}
        </button>
      </div>
      {!compact && (
        <p id={hintId} className={styles.hint}>
          Coordinates also work in the URL, so any page can link to or embed a view.
        </p>
      )}
    </form>
  );
}
