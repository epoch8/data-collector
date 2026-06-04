import Npyjs from 'npyjs';
import type { CowInferenceRecord } from '@/types/datapipe';
import { depthValueRange, isValidDepth } from '@/lib/depth-colormap';

const npyUrls = import.meta.glob('../../../datapipe_test/*.npy', {
  eager: true,
  query: '?url',
  import: 'default',
}) as Record<string, string>;

const cache = new Map<string, Promise<DepthMapData>>();

export interface DepthMapData {
  values: Float32Array;
  gridWidth: number;
  gridHeight: number;
  range: { min: number; max: number };
  validPixelRatio: number;
}

export interface DepthProbe {
  x: number;
  y: number;
  /** Расстояние до камеры, метры (сырое значение из .npy). */
  depthM: number;
}

export function resolveDepthMapUrl(assetPath: string): string | undefined {
  const fileName = assetPath.split('/').pop();
  if (!fileName) return undefined;
  const entry = Object.entries(npyUrls).find(([path]) => path.endsWith(fileName));
  return entry?.[1];
}

export function depthMapUrlForRecord(record: CowInferenceRecord): string | undefined {
  if (record.depth_map?.asset_path) {
    return resolveDepthMapUrl(record.depth_map.asset_path);
  }
  const base = record.source_export.replace(/\.json$/i, '');
  return resolveDepthMapUrl(`datapipe_test/${base}.npy`);
}

function validPixelRatio(values: Float32Array): number {
  let valid = 0;
  const step = Math.max(1, Math.floor(values.length / 8000));
  let sampled = 0;
  for (let i = 0; i < values.length; i += step) {
    sampled++;
    if (isValidDepth(values[i])) valid++;
  }
  return sampled === 0 ? 0 : valid / sampled;
}

export function loadDepthMap(url: string): Promise<DepthMapData> {
  const hit = cache.get(url);
  if (hit) return hit;

  const promise = (async () => {
    const loader = new Npyjs();
    const parsed = await loader.load(url);
    const values = parsed.data as Float32Array;
    const shape = parsed.shape;
    let gridHeight: number;
    let gridWidth: number;
    if (shape.length === 2) {
      gridHeight = shape[0];
      gridWidth = shape[1];
    } else if (shape.length === 3 && shape[2] === 1) {
      gridHeight = shape[0];
      gridWidth = shape[1];
    } else {
      throw new Error(`Unsupported depth shape: ${shape.join('×')}`);
    }
    if (values.length !== gridWidth * gridHeight) {
      throw new Error('Depth array size does not match shape');
    }
    return {
      values,
      gridWidth,
      gridHeight,
      range: depthValueRange(values),
      validPixelRatio: validPixelRatio(values),
    };
  })();

  cache.set(url, promise);
  return promise;
}

export function clientToImageCoords(
  clientX: number,
  clientY: number,
  rect: DOMRect,
  imageWidth: number,
  imageHeight: number,
): { x: number; y: number } | null {
  const scale = Math.min(rect.width / imageWidth, rect.height / imageHeight);
  const drawW = imageWidth * scale;
  const drawH = imageHeight * scale;
  const offsetX = (rect.width - drawW) / 2;
  const offsetY = (rect.height - drawH) / 2;
  const lx = clientX - rect.left - offsetX;
  const ly = clientY - rect.top - offsetY;
  if (lx < 0 || ly < 0 || lx > drawW || ly > drawH) return null;
  return {
    x: Math.min(imageWidth - 1, Math.max(0, Math.round((lx / drawW) * imageWidth))),
    y: Math.min(imageHeight - 1, Math.max(0, Math.round((ly / drawH) * imageHeight))),
  };
}

export function sampleDepth(data: DepthMapData, x: number, y: number): number | null {
  if (x < 0 || y < 0 || x >= data.gridWidth || y >= data.gridHeight) return null;
  const v = data.values[y * data.gridWidth + x];
  return isValidDepth(v) ? v : null;
}
