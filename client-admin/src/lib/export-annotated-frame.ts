import type { BlobInfo } from '@/types/manifest';
import type { CowInferenceRecord, CowKeypointAnnotationRecord } from '@/types/datapipe';
import { downloadBlob } from '@/lib/export-viz-frame';
import { depthMapUrlForRecord, loadDepthMap, type DepthMapData } from '@/lib/depth-npy';
import { getInferencePipelineExport } from '@/lib/inference-pipeline-export';
import { blobFileName } from '@/lib/format';

export interface FrameAnnotationExportDocument {
  format_version: 1;
  exported_at: string;
  /** Имя файла изображения в этой паре (рядом с JSON). */
  image_file: string;
  manifest_blob: BlobInfo;
  cow_keypoint_annotation: CowKeypointAnnotationRecord | null;
  cow_inference_result: CowInferenceRecord | null;
  /** Полный JSON экспорта пайплайна (`source_export`), если есть в бандле. */
  inference_pipeline_export: unknown | null;
  depth_map_values?: {
    unit: 'm' | 'cm';
    grid_width: number;
    grid_height: number;
    encoding: 'base64_float32_le_row_major';
    invalid_from_m: number;
    data_base64: string;
    range: { min: number; max: number };
    valid_pixel_ratio: number;
  };
}

export interface AnnotatedFrameSlide {
  blob: BlobInfo;
  gt?: CowKeypointAnnotationRecord;
  inference?: CowInferenceRecord;
}

function float32ToBase64(values: Float32Array): string {
  const bytes = new Uint8Array(values.buffer, values.byteOffset, values.byteLength);
  let binary = '';
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

function serializeDepth(
  data: DepthMapData,
  meta: NonNullable<CowInferenceRecord['depth_map']>,
): FrameAnnotationExportDocument['depth_map_values'] {
  return {
    unit: meta.unit ?? 'm',
    grid_width: data.gridWidth,
    grid_height: data.gridHeight,
    encoding: 'base64_float32_le_row_major',
    invalid_from_m: 120,
    data_base64: float32ToBase64(data.values),
    range: data.range,
    valid_pixel_ratio: data.validPixelRatio,
  };
}

async function fetchImageBlob(url: string): Promise<Blob> {
  const res = await fetch(url);
  if (!res.ok) throw new Error('Не удалось загрузить изображение');
  return res.blob();
}

function extensionFromPath(path: string): string {
  const m = path.match(/(\.[a-z0-9]+)$/i);
  return m?.[1]?.toLowerCase() ?? '.jpg';
}

function mimeForExtension(ext: string): string {
  switch (ext) {
    case '.png':
      return 'image/png';
    case '.webp':
      return 'image/webp';
    case '.jpeg':
    case '.jpg':
    default:
      return 'image/jpeg';
  }
}

export function buildFrameAnnotationExport(
  slide: AnnotatedFrameSlide,
  depthData?: DepthMapData | null,
): FrameAnnotationExportDocument {
  const { blob, gt, inference } = slide;
  const imageFile = blobFileName(blob.logical_path);

  const doc: FrameAnnotationExportDocument = {
    format_version: 1,
    exported_at: new Date().toISOString(),
    image_file: imageFile,
    manifest_blob: { ...blob },
    cow_keypoint_annotation: gt ?? null,
    cow_inference_result: inference ?? null,
    inference_pipeline_export: inference?.source_export
      ? getInferencePipelineExport(inference.source_export)
      : null,
  };

  if (depthData && inference?.depth_map) {
    doc.depth_map_values = serializeDepth(depthData, inference.depth_map);
  }

  return doc;
}

function triggerDownload(blob: Blob, filename: string): void {
  downloadBlob(blob, filename);
}

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/** Скачивает оригинальное изображение и JSON со всей разметкой кадра. */
export async function downloadAnnotatedFrame(
  slide: AnnotatedFrameSlide,
  cachedDepth?: DepthMapData | null,
): Promise<void> {
  const { blob, inference } = slide;
  const imageFile = blobFileName(blob.logical_path);
  const baseName = imageFile.replace(/\.[^.]+$/i, '') || 'frame';
  const ext = extensionFromPath(blob.logical_path);

  let depthData = cachedDepth ?? null;
  if (!depthData && inference?.depth_map) {
    const depthUrl = depthMapUrlForRecord(inference);
    if (depthUrl) {
      try {
        depthData = await loadDepthMap(depthUrl);
      } catch {
        /* глубина опциональна */
      }
    }
  }

  const imageBlob = await fetchImageBlob(blob.preview_url);
  const typedImage =
    imageBlob.type && imageBlob.type !== 'application/octet-stream'
      ? imageBlob
      : new Blob([imageBlob], { type: mimeForExtension(ext) });

  const jsonDoc = buildFrameAnnotationExport(slide, depthData);
  const jsonBlob = new Blob([JSON.stringify(jsonDoc, null, 2)], {
    type: 'application/json;charset=utf-8',
  });

  triggerDownload(typedImage, imageFile);
  await delay(250);
  triggerDownload(jsonBlob, `${baseName}.annotation.json`);
}
