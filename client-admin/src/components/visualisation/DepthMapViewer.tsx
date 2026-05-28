import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { DepthMapData, DepthProbe } from '@/lib/depth-npy';
import { clientToImageCoords, sampleDepth } from '@/lib/depth-npy';
import { depthToRgb, rasterizeDepthMap, type DepthRasterMode } from '@/lib/depth-colormap';

export type DepthDisplayMode = 'split' | 'overlay';

interface Props {
  data: DepthMapData;
  imageWidth: number;
  imageHeight: number;
  vmin: number;
  vmax: number;
  mode: DepthDisplayMode;
  overlayOpacity: number;
  probe: DepthProbe | null;
  onProbe: (probe: DepthProbe | null) => void;
  /** Только canvas (наложение на фото). */
  compact?: boolean;
  className?: string;
}

export function DepthMapViewer({
  data,
  imageWidth,
  imageHeight,
  vmin,
  vmax,
  mode,
  overlayOpacity,
  probe,
  onProbe,
  compact = false,
  className = '',
}: Props) {
  const frameRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [renderKey, setRenderKey] = useState(0);

  const rasterMode: DepthRasterMode = mode === 'overlay' ? 'overlay' : 'opaque';
  const colorBitmap = useMemo(
    () =>
      rasterizeDepthMap(
        data.values,
        data.gridWidth,
        data.gridHeight,
        vmin,
        vmax,
        rasterMode,
      ),
    [data, vmin, vmax, rasterMode],
  );

  const paint = useCallback(() => {
    const canvas = canvasRef.current;
    const frame = frameRef.current;
    if (!canvas || !frame) return;

    const w = Math.max(1, Math.round(frame.clientWidth));
    const h = Math.max(1, Math.round(frame.clientHeight));
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const off = document.createElement('canvas');
    off.width = data.gridWidth;
    off.height = data.gridHeight;
    const offCtx = off.getContext('2d');
    if (!offCtx) return;
    offCtx.putImageData(colorBitmap, 0, 0);

    ctx.clearRect(0, 0, w, h);
    if (mode === 'split') {
      ctx.fillStyle = '#0a0c10';
      ctx.fillRect(0, 0, w, h);
    }

    const scale = Math.min(w / imageWidth, h / imageHeight);
    const drawW = imageWidth * scale;
    const drawH = imageHeight * scale;
    const ox = (w - drawW) / 2;
    const oy = (h - drawH) / 2;

    ctx.imageSmoothingEnabled = true;
    ctx.globalAlpha = mode === 'overlay' ? overlayOpacity : 1;
    ctx.drawImage(off, 0, 0, data.gridWidth, data.gridHeight, ox, oy, drawW, drawH);
    ctx.globalAlpha = 1;

    if (probe) {
      const px = ox + (probe.x / imageWidth) * drawW;
      const py = oy + (probe.y / imageHeight) * drawH;
      ctx.strokeStyle = 'rgba(255,255,255,0.95)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(px, py, 10, 0, Math.PI * 2);
      ctx.stroke();
      ctx.strokeStyle = 'rgba(251,146,60,0.9)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(px - 14, py);
      ctx.lineTo(px + 14, py);
      ctx.moveTo(px, py - 14);
      ctx.lineTo(px, py + 14);
      ctx.stroke();
    }
  }, [
    colorBitmap,
    data.gridWidth,
    data.gridHeight,
    imageWidth,
    imageHeight,
    mode,
    overlayOpacity,
    probe,
  ]);

  useEffect(() => {
    paint();
  }, [paint, renderKey]);

  useEffect(() => {
    const frame = frameRef.current;
    if (!frame) return;
    const ro = new ResizeObserver(() => setRenderKey(k => k + 1));
    ro.observe(frame);
    return () => ro.disconnect();
  }, []);

  const handlePointer = (e: React.PointerEvent) => {
    const frame = frameRef.current;
    if (!frame) return;
    const coords = clientToImageCoords(
      e.clientX,
      e.clientY,
      frame.getBoundingClientRect(),
      imageWidth,
      imageHeight,
    );
    if (!coords) {
      onProbe(null);
      return;
    }
    const depthCm = sampleDepth(data, coords.x, coords.y);
    if (depthCm == null) {
      onProbe(null);
      return;
    }
    onProbe({ x: coords.x, y: coords.y, depthCm });
  };

  const legendSteps = 24;
  const validPct = Math.round(data.validPixelRatio * 100);

  return (
    <div className={`depth-view ${compact ? 'depth-view--compact' : ''} ${className}`}>
      {mode === 'split' && !compact && (
        <div className="depth-view__head">
          <span className="depth-view__title">Карта глубины</span>
          <span className="depth-view__subtitle">расстояние до камеры, см</span>
        </div>
      )}

      <div
        ref={frameRef}
        className={`depth-view__frame ${mode === 'split' ? 'depth-view__frame--split' : 'depth-view__frame--overlay'}`}
        onPointerMove={handlePointer}
        onPointerLeave={() => onProbe(null)}
      >
        <canvas ref={canvasRef} className="depth-view__canvas" />
        {probe && (
          <div
            className="depth-view__tooltip"
            style={{
              left: `${(probe.x / imageWidth) * 100}%`,
              top: `${(probe.y / imageHeight) * 100}%`,
            }}
          >
            {probe.depthCm.toFixed(1)} см
          </div>
        )}
      </div>

      {mode === 'split' && !compact && (
        <div className="depth-view__footer">
          <div className="depth-view__legend" aria-hidden>
            <span className="depth-view__legend-word">ближе</span>
            <div className="depth-view__legend-bar">
              {Array.from({ length: legendSteps }, (_, i) => {
                const [r, g, b] = depthToRgb(i / (legendSteps - 1));
                return (
                  <span
                    key={i}
                    className="depth-view__legend-step"
                    style={{ background: `rgb(${r},${g},${b})` }}
                  />
                );
              })}
            </div>
            <span className="depth-view__legend-word">дальше</span>
          </div>
          <p className="depth-view__range font-mono tabular-nums">
            {vmin.toFixed(1)} – {vmax.toFixed(1)} см
            <span className="depth-view__range-sep">·</span>
            <span className="text-gray-500">объект ~{validPct}% кадра</span>
          </p>
          <p className="depth-view__hint">
            Серый фон — нет измерения (126.72). Наведите на цветную область.
          </p>
        </div>
      )}
    </div>
  );
}
