import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { DepthMapData, DepthProbe } from '@/lib/depth-npy';
import { clientToImageCoords, sampleDepth } from '@/lib/depth-npy';
import { depthToRgb, rasterizeDepthMap, type DepthRasterMode } from '@/lib/depth-colormap';
import { formatDepthMeters, formatDepthRange } from '@/lib/depth-format';

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
      const g = ctx.createLinearGradient(0, 0, 0, h);
      g.addColorStop(0, '#0c0e14');
      g.addColorStop(1, '#080a0f');
      ctx.fillStyle = g;
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

    if (mode === 'split') {
      ctx.strokeStyle = 'rgba(251, 146, 60, 0.15)';
      ctx.lineWidth = 1;
      ctx.strokeRect(ox + 0.5, oy + 0.5, drawW - 1, drawH - 1);
    }

    if (probe) {
      const px = ox + (probe.x / imageWidth) * drawW;
      const py = oy + (probe.y / imageHeight) * drawH;
      ctx.beginPath();
      ctx.arc(px, py, 11, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(15, 17, 23, 0.55)';
      ctx.fill();
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.92)';
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.strokeStyle = 'rgba(251, 146, 60, 0.95)';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(px - 16, py);
      ctx.lineTo(px + 16, py);
      ctx.moveTo(px, py - 16);
      ctx.lineTo(px, py + 16);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(px, py, 3, 0, Math.PI * 2);
      ctx.fillStyle = '#fb923c';
      ctx.fill();
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
    const depthM = sampleDepth(data, coords.x, coords.y);
    if (depthM == null) {
      onProbe(null);
      return;
    }
    onProbe({ x: coords.x, y: coords.y, depthM });
  };

  const legendSteps = 32;
  const validPct = Math.round(data.validPixelRatio * 100);

  return (
    <div className={`depth-view ${compact ? 'depth-view--compact' : ''} ${className}`}>
      {mode === 'split' && !compact && (
        <div className="depth-view__head">
          <div className="depth-view__head-text">
            <span className="depth-view__badge">Z</span>
            <div>
              <span className="depth-view__title">Карта глубины</span>
              <span className="depth-view__subtitle">расстояние до камеры · метры</span>
            </div>
          </div>
          <span className="depth-view__chip">~{validPct}% кадра</span>
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
            <span className="depth-view__tooltip-value">{formatDepthMeters(probe.depthM)}</span>
          </div>
        )}
      </div>

      {mode === 'split' && !compact && (
        <div className="depth-view__footer">
          <div className="depth-view__legend-wrap">
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
            <p className="depth-view__range">{formatDepthRange(vmin, vmax)}</p>
          </div>
          <p className="depth-view__hint">
            Шахматный фон — нет данных. Наведите на цветную область коровы.
          </p>
        </div>
      )}
    </div>
  );
}
