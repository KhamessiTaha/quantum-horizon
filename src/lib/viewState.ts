export type ViewMode = "blink" | "difference";

export type DetectorId = "D1" | "D2" | "D3" | "D4" | "D5" | "D6";

export interface ViewState {
  target: string | null;
  ra: number | null;
  dec: number | null;
  fovDeg: number;
  detector: DetectorId;
  mode: ViewMode;
}

export const DETECTORS: { id: DetectorId; rangeMicron: string }[] = [
  { id: "D1", rangeMicron: "0.75–1.09 µm" },
  { id: "D2", rangeMicron: "1.10–1.62 µm" },
  { id: "D3", rangeMicron: "1.63–2.41 µm" },
  { id: "D4", rangeMicron: "2.42–3.82 µm" },
  { id: "D5", rangeMicron: "3.83–4.41 µm" },
  { id: "D6", rangeMicron: "4.42–5.00 µm" },
];

export const FOV_LIMITS = { min: 0.03, max: 0.2, defaultDeg: 0.06 };

const DETECTOR_IDS = new Set<string>(DETECTORS.map((d) => d.id));

function parseNumber(value: string | null, min: number, max: number): number | null {
  if (value === null || value.trim() === "") return null;
  const n = Number(value);
  return Number.isFinite(n) && n >= min && n <= max ? n : null;
}

export function parseViewState(params: URLSearchParams): ViewState {
  const detector = params.get("det")?.toUpperCase() ?? "D2";
  const fov = parseNumber(params.get("fov"), FOV_LIMITS.min, FOV_LIMITS.max);
  return {
    target: params.get("target"),
    ra: parseNumber(params.get("ra"), 0, 360),
    dec: parseNumber(params.get("dec"), -90, 90),
    fovDeg: fov ?? FOV_LIMITS.defaultDeg,
    detector: (DETECTOR_IDS.has(detector) ? detector : "D2") as DetectorId,
    mode: params.get("mode") === "difference" ? "difference" : "blink",
  };
}

export function toSearchParams(state: ViewState): URLSearchParams {
  const params = new URLSearchParams();
  if (state.target) params.set("target", state.target);
  if (state.ra !== null) params.set("ra", state.ra.toFixed(5));
  if (state.dec !== null) params.set("dec", state.dec.toFixed(5));
  params.set("fov", String(state.fovDeg));
  params.set("det", state.detector);
  params.set("mode", state.mode);
  return params;
}

export function parseQuery(query: string): { target: string | null; ra: number | null; dec: number | null } {
  const parts = query.trim().split(/[\s,]+/);
  if (parts.length === 2) {
    const ra = parseNumber(parts[0], 0, 360);
    const dec = parseNumber(parts[1], -90, 90);
    if (ra !== null && dec !== null) return { target: null, ra, dec };
  }
  return { target: query.trim() || null, ra: null, dec: null };
}
