/** Типичное «пустое» значение в mock .npy. */
export const DEPTH_INVALID_SENTINEL = 126.72;

const INVALID_HIGH = 120;

export function isValidDepth(value: number): boolean {
  if (!Number.isFinite(value)) return false;
  if (value >= INVALID_HIGH) return false;
  if (Math.abs(value - DEPTH_INVALID_SENTINEL) < 0.05) return false;
  return true;
}

function clamp01(x: number): number {
  return Math.min(1, Math.max(0, x));
}

/**
 * Палитра глубины: ближе к камере — холодные тона, дальше — тёплые.
 * t ∈ [0, 1] после нормализации vmin…vmax.
 */
export function depthToRgb(t: number): [number, number, number] {
  const x = clamp01(t);
  // #2E5BFF → #00C9C9 → #F5D547 → #F04E4E
  if (x < 0.33) {
    const f = x / 0.33;
    return lerpRgb([46, 91, 255], [0, 201, 201], f);
  }
  if (x < 0.66) {
    const f = (x - 0.33) / 0.33;
    return lerpRgb([0, 201, 201], [245, 213, 71], f);
  }
  const f = (x - 0.66) / 0.34;
  return lerpRgb([245, 213, 71], [240, 78, 78], f);
}

function lerpRgb(a: [number, number, number], b: [number, number, number], t: number): [number, number, number] {
  return [
    Math.round(a[0] + (b[0] - a[0]) * t),
    Math.round(a[1] + (b[1] - a[1]) * t),
    Math.round(a[2] + (b[2] - a[2]) * t),
  ];
}

export function normalizeDepth(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return 0;
  return clamp01((value - min) / (max - min));
}

export function depthValueRange(
  values: Float32Array,
  lowPct = 5,
  highPct = 95,
): { min: number; max: number } {
  const sample: number[] = [];
  const step = Math.max(1, Math.floor(values.length / 16000));
  for (let i = 0; i < values.length; i += step) {
    const v = values[i];
    if (isValidDepth(v)) sample.push(v);
  }
  if (sample.length === 0) return { min: 0, max: 1 };
  sample.sort((a, b) => a - b);
  const lo = sample[Math.floor((sample.length * lowPct) / 100)] ?? sample[0];
  const hi =
    sample[Math.floor((sample.length * highPct) / 100)] ?? sample[sample.length - 1];
  if (hi <= lo) return { min: lo, max: lo + 0.01 };
  return { min: lo, max: hi };
}

export type DepthRasterMode = 'opaque' | 'overlay';

function invalidPixelRgb(x: number, y: number): [number, number, number] {
  const check = ((x >> 2) ^ (y >> 2)) & 1;
  return check ? [22, 26, 36] : [16, 19, 28];
}

export function rasterizeDepthMap(
  values: Float32Array,
  gridWidth: number,
  gridHeight: number,
  vmin: number,
  vmax: number,
  mode: DepthRasterMode,
): ImageData {
  const img = new ImageData(gridWidth, gridHeight);
  const d = img.data;

  for (let y = 0; y < gridHeight; y++) {
    for (let x = 0; x < gridWidth; x++) {
      const v = values[y * gridWidth + x];
      const i = (y * gridWidth + x) * 4;
      if (!isValidDepth(v)) {
        if (mode === 'overlay') {
          d[i] = 0;
          d[i + 1] = 0;
          d[i + 2] = 0;
          d[i + 3] = 0;
        } else {
          const [r, g, b] = invalidPixelRgb(x, y);
          d[i] = r;
          d[i + 1] = g;
          d[i + 2] = b;
          d[i + 3] = 255;
        }
        continue;
      }
      const t = normalizeDepth(v, vmin, vmax);
      const [r, g, b] = depthToRgb(t);
      d[i] = r;
      d[i + 1] = g;
      d[i + 2] = b;
      d[i + 3] = 255;
    }
  }
  return img;
}
