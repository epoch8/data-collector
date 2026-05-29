import { useCallback, useEffect, useMemo, useState } from 'react';
import type { BlobInfo } from '@/types/manifest';
import type {
  AnnotationLayer,
  CowInferenceRecord,
  CowKeypointAnnotationRecord,
} from '@/types/datapipe';
import { AnnotationCanvas } from '@/components/visualisation/AnnotationCanvas';
import { DepthMapViewer, type DepthDisplayMode } from '@/components/visualisation/DepthMapViewer';
import { DepthProbeBar } from '@/components/visualisation/DepthProbeBar';
import { VizFilmstrip } from '@/components/visualisation/VizFilmstrip';
import { EmptyState } from '@/components/ui/EmptyState';
import { blobFileName } from '@/lib/format';
import {
  clientToImageCoords,
  depthMapUrlForRecord,
  loadDepthMap,
  sampleDepth,
  type DepthMapData,
  type DepthProbe,
} from '@/lib/depth-npy';

interface VizSlide {
  blob: BlobInfo;
  gt?: CowKeypointAnnotationRecord;
  inference?: CowInferenceRecord;
}

interface Props {
  blobs: BlobInfo[];
  gtRecords: CowKeypointAnnotationRecord[];
  inferenceRecords: CowInferenceRecord[];
}

export function VisualisationTab({ blobs, gtRecords, inferenceRecords }: Props) {
  const slides = useMemo(() => {
    const keys = new Set<string>();
    for (const r of gtRecords) keys.add(r.manifest_blob_key);
    for (const r of inferenceRecords) keys.add(r.manifest_blob_key);
    const out: VizSlide[] = [];
    for (const key of keys) {
      const blob = blobs.find(b => b.logical_path === key);
      if (!blob) continue;
      out.push({
        blob,
        gt: gtRecords.find(r => r.manifest_blob_key === key),
        inference: inferenceRecords.find(r => r.manifest_blob_key === key),
      });
    }
    return out;
  }, [blobs, gtRecords, inferenceRecords]);

  const [index, setIndex] = useState(0);
  const [showGt, setShowGt] = useState(false);
  const [showInference, setShowInference] = useState(true);
  const [showBoxes, setShowBoxes] = useState(false);
  const [showLabels, setShowLabels] = useState(false);
  const [showDepth, setShowDepth] = useState(false);
  const [depthDisplayMode, setDepthDisplayMode] = useState<DepthDisplayMode>('split');
  const [depthOpacity, setDepthOpacity] = useState(0.5);
  const [depthData, setDepthData] = useState<DepthMapData | null>(null);
  const [depthLoading, setDepthLoading] = useState(false);
  const [depthError, setDepthError] = useState<string | null>(null);
  const [depthVmin, setDepthVmin] = useState(0);
  const [depthVmax, setDepthVmax] = useState(1);
  const [depthProbe, setDepthProbe] = useState<DepthProbe | null>(null);
  const [selectedPoint, setSelectedPoint] = useState<{
    layerId: string;
    index: number;
  } | null>(null);

  const safeIndex = Math.min(index, Math.max(0, slides.length - 1));
  const current = slides[safeIndex];

  const goPrev = useCallback(() => {
    if (slides.length <= 1) return;
    setIndex(i => (i - 1 + slides.length) % slides.length);
    setSelectedPoint(null);
  }, [slides.length]);

  const goNext = useCallback(() => {
    if (slides.length <= 1) return;
    setIndex(i => (i + 1) % slides.length);
    setSelectedPoint(null);
  }, [slides.length]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') goPrev();
      if (e.key === 'ArrowRight') goNext();
      if (e.key === 'Escape') setSelectedPoint(null);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [goPrev, goNext]);

  const currentInference = slides[safeIndex]?.inference;
  const depthUrl = currentInference ? depthMapUrlForRecord(currentInference) : undefined;
  const hasDepth = Boolean(depthUrl);

  useEffect(() => {
    setDepthProbe(null);
    if (!showDepth || !depthUrl) {
      setDepthData(null);
      setDepthError(null);
      setDepthLoading(false);
      return;
    }
    let cancelled = false;
    setDepthLoading(true);
    setDepthError(null);
    loadDepthMap(depthUrl)
      .then(data => {
        if (cancelled) return;
        setDepthData(data);
        setDepthVmin(data.range.min);
        setDepthVmax(data.range.max);
        setDepthLoading(false);
      })
      .catch(err => {
        if (cancelled) return;
        setDepthData(null);
        setDepthLoading(false);
        setDepthError(err instanceof Error ? err.message : 'Не удалось загрузить карту глубины');
      });
    return () => {
      cancelled = true;
    };
  }, [showDepth, depthUrl, safeIndex]);

  const probeImageSize =
    slides[safeIndex]?.gt?.image_size ??
    slides[safeIndex]?.inference?.image_size ?? { width: 1024, height: 640 };

  const handleDepthPointer = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!showDepth || !depthData) return;
      const coords = clientToImageCoords(
        e.clientX,
        e.clientY,
        e.currentTarget.getBoundingClientRect(),
        probeImageSize.width,
        probeImageSize.height,
      );
      if (!coords) {
        setDepthProbe(null);
        return;
      }
      const depthM = sampleDepth(depthData, coords.x, coords.y);
      if (depthM == null) {
        setDepthProbe(null);
        return;
      }
      setDepthProbe({ x: coords.x, y: coords.y, depthM });
    },
    [showDepth, depthData, probeImageSize.width, probeImageSize.height],
  );

  if (gtRecords.length === 0 && inferenceRecords.length === 0) {
    return (
      <EmptyState
        title="Нет данных для визуализации"
        description="Нужны записи в cow_keypoint_annotation и/или cow_inference_result."
      />
    );
  }

  if (slides.length === 0) {
    return (
      <EmptyState
        title="Нет привязки к media"
        description="Данные есть, но blob paths не совпали с файлами пакета."
      />
    );
  }

  if (!current) return null;

  const { blob, gt, inference } = current;
  const imageSize = gt?.image_size ?? inference?.image_size ?? { width: 1024, height: 640 };

  const layers: AnnotationLayer[] = [];
  if (gt && showGt) {
    layers.push({
      id: 'gt',
      palette: 'gt',
      visible: true,
      boxes: gt.annotation.boxes,
      points: gt.annotation.points,
    });
  }
  if (inference && showInference) {
    layers.push({
      id: 'inference',
      palette: 'inference',
      visible: true,
      boxes: inference.inference.annotation.boxes,
      points: inference.inference.annotation.keypoints,
      segments: inference.inference.annotation.segments,
    });
  }

  const gtPointCount = gt?.annotation.points.length ?? 0;
  const infKpCount = inference?.inference.annotation.keypoints.length ?? 0;

  return (
    <div className="max-w-7xl mx-auto w-full">
      <div className="ui-panel overflow-hidden flex flex-col">
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-[var(--color-border)]">
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-gray-100">Визуализация</h3>
            <p className="text-[11px] text-gray-500 mt-0.5 truncate" title={blob.logical_path}>
              {blobFileName(blob.logical_path)}
              {gt && ` · GT ${gtPointCount}`}
              {inference && ` · Inf ${infKpCount}`}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <LayerToggle
              label="GT"
              checked={showGt}
              disabled={!gt}
              onChange={setShowGt}
              colorClass="viz-layer-toggle--gt"
            />
            <LayerToggle
              label="Inference"
              checked={showInference}
              disabled={!inference}
              onChange={setShowInference}
              colorClass="viz-layer-toggle--inf"
            />
            <label className="viz-toggle text-[11px]">
              <input
                type="checkbox"
                checked={showBoxes}
                onChange={e => setShowBoxes(e.target.checked)}
              />
              BBox
            </label>
            <label className="viz-toggle text-[11px]">
              <input
                type="checkbox"
                checked={showLabels}
                onChange={e => setShowLabels(e.target.checked)}
              />
              Подписи
            </label>
            <LayerToggle
              label="Глубина"
              checked={showDepth}
              disabled={!hasDepth}
              onChange={setShowDepth}
              colorClass="viz-layer-toggle--depth"
            />

            {gt?.cvat_link && (
              <a
                href={gt.cvat_link}
                target="_blank"
                rel="noopener noreferrer"
                className="viz-cvat-link"
              >
                Open in CVAT
                <span aria-hidden>↗</span>
              </a>
            )}

            <div className="viz-nav-group" role="group" aria-label="Переключение кадра">
              <button type="button" onClick={goPrev} disabled={slides.length <= 1} className="viz-nav-btn" aria-label="Предыдущий кадр">
                ‹
              </button>
              <button type="button" onClick={goNext} disabled={slides.length <= 1} className="viz-nav-btn" aria-label="Следующий кадр">
                ›
              </button>
            </div>
          </div>
        </div>

        <div className="flex flex-col lg:flex-row">
          <div className="flex-1 min-w-0 flex flex-col">
            <div className="flex flex-col">
              {showDepth && hasDepth && (
                <DepthProbeBar
                  probe={depthProbe}
                  mode={depthDisplayMode}
                  onModeChange={setDepthDisplayMode}
                  overlayOpacity={depthOpacity}
                  onOverlayOpacityChange={setDepthOpacity}
                  loading={depthLoading}
                  error={depthError}
                />
              )}

              <div
                className={
                  showDepth && depthData && depthDisplayMode === 'split'
                    ? 'viz-dual'
                    : 'viz-dual viz-dual--single'
                }
              >
                <div className="viz-dual__photo flex items-center justify-center p-4 bg-[#0a0c10] min-h-[min(42vh,380px)]">
                  <AnnotationCanvas
                    src={blob.preview_url}
                    alt={blobFileName(blob.logical_path)}
                    width={imageSize.width}
                    height={imageSize.height}
                    layers={layers}
                    showBoxes={showBoxes}
                    showLabels={showLabels}
                    selectedPoint={selectedPoint}
                    onSelectPoint={setSelectedPoint}
                    depthProbe={showDepth ? depthProbe : null}
                    onFramePointerMove={showDepth && depthData ? handleDepthPointer : undefined}
                    onFramePointerLeave={showDepth ? () => setDepthProbe(null) : undefined}
                    overlay={
                      showDepth &&
                      depthData &&
                      depthDisplayMode === 'overlay' &&
                      !depthLoading ? (
                        <DepthMapViewer
                          compact
                          data={depthData}
                          imageWidth={imageSize.width}
                          imageHeight={imageSize.height}
                          vmin={depthVmin}
                          vmax={depthVmax}
                          mode="overlay"
                          overlayOpacity={depthOpacity}
                          probe={depthProbe}
                          onProbe={setDepthProbe}
                        />
                      ) : null
                    }
                  />
                </div>

                {showDepth && depthData && depthDisplayMode === 'split' && !depthLoading && (
                  <div className="viz-dual__depth border-t lg:border-t-0 lg:border-l border-[var(--color-border)] bg-[#0a0c10] p-4 min-h-[min(42vh,380px)]">
                    <DepthMapViewer
                      data={depthData}
                      imageWidth={imageSize.width}
                      imageHeight={imageSize.height}
                      vmin={depthVmin}
                      vmax={depthVmax}
                      mode="split"
                      overlayOpacity={1}
                      probe={depthProbe}
                      onProbe={setDepthProbe}
                    />
                  </div>
                )}
              </div>
            </div>

            <VizFilmstrip
              slides={slides.map(s => ({
                key: s.blob.logical_path,
                previewUrl: s.blob.preview_url,
                caption: s.blob.logical_path,
              }))}
              activeIndex={safeIndex}
              onSelect={i => {
                setIndex(i);
                setSelectedPoint(null);
              }}
            />
          </div>

          <aside className="viz-keypoints-panel lg:w-80 xl:w-96 shrink-0 flex flex-col border-t lg:border-t-0 lg:border-l border-[var(--color-border)]">
            {gt && showGt && (
              <PointList
                title={`GT (${gtPointCount})`}
                points={gt.annotation.points}
                layerId="gt"
                selectedPoint={selectedPoint}
                onSelect={setSelectedPoint}
              />
            )}
            {inference && showInference && (
              <>
                <PointList
                  title={`Inference KP (${infKpCount})`}
                  points={inference.inference.annotation.keypoints}
                  layerId="inference"
                  selectedPoint={selectedPoint}
                  onSelect={setSelectedPoint}
                  showConfidence
                />
                {inference.inference.distances && (
                  <div className="p-3 border-t border-[var(--color-border)] text-[11px] text-gray-500 space-y-1">
                    <p className="uppercase tracking-wider text-[10px] text-gray-600 mb-1">
                      Метрики (см)
                    </p>
                    {Object.entries(inference.inference.distances).map(([k, v]) => (
                      <div key={k} className="flex justify-between gap-2">
                        <span className="text-gray-400 truncate">{k}</span>
                        <span className="font-mono text-cyan-400/90 shrink-0">{v.toFixed(1)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </aside>
        </div>
      </div>
    </div>
  );
}

function LayerToggle({
  label,
  checked,
  disabled,
  onChange,
  colorClass,
}: {
  label: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (v: boolean) => void;
  colorClass: string;
}) {
  return (
    <label
      className={`viz-layer-toggle ${colorClass} ${checked ? 'viz-layer-toggle--on' : ''} ${disabled ? 'opacity-40 pointer-events-none' : ''}`}
    >
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={e => onChange(e.target.checked)}
        className="sr-only"
      />
      {label}
    </label>
  );
}

function PointList({
  title,
  points,
  layerId,
  selectedPoint,
  onSelect,
  showConfidence,
}: {
  title: string;
  points: { label: string; x: number; y: number; confidence?: number }[];
  layerId: string;
  selectedPoint: { layerId: string; index: number } | null;
  onSelect: (sel: { layerId: string; index: number } | null) => void;
  showConfidence?: boolean;
}) {
  return (
    <>
      <p className="text-[10px] uppercase tracking-wider text-gray-500 px-4 py-3 border-b border-[var(--color-border)] shrink-0">
        {title}
      </p>
      <ul className="p-2 space-y-0.5">
        {points.map((pt, idx) => (
          <li key={`${layerId}-${pt.label}-${idx}`}>
            <button
              type="button"
              onClick={() =>
                onSelect(
                  selectedPoint?.layerId === layerId && selectedPoint.index === idx
                    ? null
                    : { layerId, index: idx },
                )
              }
              className={`viz-point-row w-full text-left ${
                selectedPoint?.layerId === layerId && selectedPoint.index === idx
                  ? 'viz-point-row--active'
                  : ''
              }`}
            >
              <span className="viz-point-row__dot" aria-hidden />
              <span className="flex-1 min-w-0 text-xs text-gray-300 truncate">{pt.label}</span>
              <span className="text-[10px] text-gray-600 font-mono tabular-nums shrink-0">
                {Math.round(pt.x)},{Math.round(pt.y)}
                {showConfidence && pt.confidence != null && (
                  <span className="text-cyan-600"> · {(pt.confidence * 100).toFixed(0)}%</span>
                )}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}
