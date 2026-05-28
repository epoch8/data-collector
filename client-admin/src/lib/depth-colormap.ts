/** Типичное «пустое» значение в mock .npy (далеко за пределами коровы). */
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

/** Google Turbo (полиномиальная аппроксимация). */
export function depthToRgb(t: number): [number, number, number] {
  const x = clamp01(t);
  const r =
    255 *
    clamp01(
      0.13572138 +
        x *
          (4.6153926 +
            x * (-42.66032258 + x * (132.13108234 + x * (-152.94239396 + x * 59.28637943)))),
    );
  const g =
    255 *
    clamp01(
      0.09140261 +
        x *
          (2.19418839 +
            x * (4.84296658 + x * (-14.18503333 + x * (4.27729857 + x * 2.82956604)))),
    );
  const b =
    255 *
    clamp01(
      0.1066733 +
        x *
          (12.64194608 +
            x * (-60.58204836 + x * (110.36276771 + x * (-89.90310912 + x * 27.34824973)))),
    );
  return [Math.round(r), Math.round(g), Math.round(b)];
}

export function normalizeDepth(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return 0;
  return clamp01((value - min) / (max - min));
}

/** Диапазон только по валидным пикселям (без 126.72 и фона). */
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
  if (hi <= lo) return { min: lo, max: lo + 1 };
  return { min: lo, max: hi };
}

export type DepthRasterMode = 'opaque' | 'overlay';

/** Растеризация карты: валидные — turbo, невалидные — прозрачные или серые. */
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
  const invalidRgb: [number, number, number] = [22, 24, 32];

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
          d[i] = invalidRgb[0];
          d[i + 1] = invalidRgb[1];
          d[i + 2] = invalidRgb[2];
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
