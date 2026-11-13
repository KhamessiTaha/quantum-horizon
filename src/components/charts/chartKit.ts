/** Shared geometry for the small SVG charts. Passes are ordered in time, so their colours are one sequential ramp. */

export const PASS_RAMP = ["#2f6d8c", "#3b88ad", "#4aa3cf", "#63bfe8", "#7fd4ff"];

export function passColour(index: number, total: number): string {
  if (total <= 1) return PASS_RAMP.at(-1) as string;
  const position = (index / (total - 1)) * (PASS_RAMP.length - 1);
  return PASS_RAMP[Math.round(position)];
}

export interface Box {
  width: number;
  height: number;
  left: number;
  right: number;
  top: number;
  bottom: number;
}

export const BOX: Box = { width: 900, height: 280, left: 60, right: 92, top: 18, bottom: 38 };

export interface Scale {
  (value: number): number;
  domain: [number, number];
}

export function linear(domain: [number, number], range: [number, number]): Scale {
  const [d0, d1] = domain[0] === domain[1] ? [domain[0] - 1, domain[1] + 1] : domain;
  const span = d1 - d0;
  const scale = ((value: number) => range[0] + ((value - d0) / span) * (range[1] - range[0])) as Scale;
  scale.domain = [d0, d1];
  return scale;
}

export function extent(values: number[], pad = 0.08): [number, number] {
  if (!values.length) return [0, 1];
  const low = Math.min(...values);
  const high = Math.max(...values);
  const margin = (high - low || Math.abs(high) || 1) * pad;
  return [low - margin, high + margin];
}

export function ticks(domain: [number, number], count = 4): number[] {
  const [low, high] = domain;
  const raw = (high - low) / count;
  const magnitude = 10 ** Math.floor(Math.log10(Math.abs(raw) || 1));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((s) => s >= raw) ?? magnitude * 10;
  const first = Math.ceil(low / step) * step;
  const out: number[] = [];
  for (let value = first; value <= high + step * 0.001; value += step) out.push(Number(value.toPrecision(12)));
  return out;
}

export function compact(value: number): string {
  const size = Math.abs(value);
  if (size >= 1000) return `${(value / 1000).toFixed(size >= 10000 ? 0 : 1)}k`;
  if (size >= 10) return value.toFixed(0);
  if (size >= 1) return value.toFixed(1);
  if (size === 0) return "0";
  return value.toPrecision(2);
}

export function path(points: { x: number; y: number }[]): string {
  return points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ");
}
