export type ViewMode = "blink" | "difference";

export type DetectorId = "D1" | "D2" | "D3" | "D4" | "D5" | "D6";

export type Panel = "findings" | "spectrum" | "brightness" | "movers";

export interface ViewState {
  target: string | null;
  ra: number | null;
  dec: number | null;
  fovDeg: number;
  detector: DetectorId;
  mode: ViewMode;
  hidden: number[];
  pair: [number, number] | null;
  panel: Panel;
  pick: { x: number; y: number } | null;
  overlay: boolean;
  gaia: boolean;
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
const PANELS = new Set<string>(["findings", "spectrum", "brightness", "movers"]);

function parseNumber(value: string | null, min: number, max: number): number | null {
  if (value === null || value.trim() === "") return null;
  const n = Number(value);
  return Number.isFinite(n) && n >= min && n <= max ? n : null;
}

function parseList(value: string | null): number[] {
  if (!value) return [];
  return [...new Set(value.split(",").map((part) => Number(part)).filter((n) => Number.isInteger(n) && n > 0))].sort(
    (a, b) => a - b,
  );
}

function parsePair(value: string | null): [number, number] | null {
  if (!value) return null;
  const parts = value.split("-").map((part) => Number(part));
  if (parts.length !== 2 || parts.some((n) => !Number.isInteger(n) || n < 1) || parts[0] === parts[1]) return null;
  return [parts[0], parts[1]];
}

function parsePick(value: string | null): { x: number; y: number } | null {
  if (!value) return null;
  const parts = value.split(",").map((part) => Number(part));
  if (parts.length !== 2 || parts.some((n) => !Number.isFinite(n))) return null;
  return { x: parts[0], y: parts[1] };
}

export function parseViewState(params: URLSearchParams): ViewState {
  const detector = params.get("det")?.toUpperCase() ?? "D2";
  const fov = parseNumber(params.get("fov"), FOV_LIMITS.min, FOV_LIMITS.max);
  const panel = params.get("panel") ?? "findings";
  return {
    target: params.get("target"),
    ra: parseNumber(params.get("ra"), 0, 360),
    dec: parseNumber(params.get("dec"), -90, 90),
    fovDeg: fov ?? FOV_LIMITS.defaultDeg,
    detector: (DETECTOR_IDS.has(detector) ? detector : "D2") as DetectorId,
    mode: params.get("mode") === "difference" ? "difference" : "blink",
    hidden: parseList(params.get("hide")),
    pair: parsePair(params.get("pair")),
    panel: (PANELS.has(panel) ? panel : "findings") as Panel,
    pick: parsePick(params.get("pick")),
    overlay: params.get("overlay") !== "0",
    gaia: params.get("gaia") === "1",
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
  if (state.hidden.length) params.set("hide", state.hidden.join(","));
  if (state.pair) params.set("pair", state.pair.join("-"));
  if (state.panel !== "findings") params.set("panel", state.panel);
  if (state.pick) params.set("pick", `${state.pick.x.toFixed(2)},${state.pick.y.toFixed(2)}`);
  if (!state.overlay) params.set("overlay", "0");
  if (state.gaia) params.set("gaia", "1");
  return params;
}

/** The parts of the state the backend cares about: changing anything else must not refetch. */
export function queryKey(state: ViewState): string {
  const place = state.target ?? `${state.ra},${state.dec}`;
  return `${place}|${state.detector}|${state.fovDeg}`;
}

export function targetQuery(state: ViewState) {
  return {
    target: state.target,
    ra: state.ra,
    dec: state.dec,
    detector: state.detector,
    fovDeg: state.fovDeg,
  };
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
