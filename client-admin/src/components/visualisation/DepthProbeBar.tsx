import type { DepthProbe } from '@/lib/depth-npy';
import type { DepthDisplayMode } from '@/components/visualisation/DepthMapViewer';

interface Props {
  probe: DepthProbe | null;
  mode: DepthDisplayMode;
  onModeChange: (mode: DepthDisplayMode) => void;
  overlayOpacity: number;
  onOverlayOpacityChange: (v: number) => void;
  loading?: boolean;
  error?: string | null;
}

export function DepthProbeBar({
  probe,
  mode,
  onModeChange,
  overlayOpacity,
  onOverlayOpacityChange,
  loading,
  error,
}: Props) {
  return (
    <div className="depth-probe-bar">
      <div className="depth-probe-bar__modes" role="group" aria-label="Режим глубины">
        <button
          type="button"
          className={`depth-mode-btn ${mode === 'split' ? 'depth-mode-btn--on' : ''}`}
          onClick={() => onModeChange('split')}
        >
          Рядом
        </button>
        <button
          type="button"
          className={`depth-mode-btn ${mode === 'overlay' ? 'depth-mode-btn--on' : ''}`}
          onClick={() => onModeChange('overlay')}
        >
          Наложение
        </button>
      </div>

      {mode === 'overlay' && (
        <label className="depth-probe-bar__opacity">
          <span>Прозрачность</span>
          <input
            type="range"
            min={15}
            max={85}
            value={Math.round(overlayOpacity * 100)}
            onChange={e => onOverlayOpacityChange(Number(e.target.value) / 100)}
            className="depth-range"
          />
          <span className="tabular-nums text-gray-400">{Math.round(overlayOpacity * 100)}%</span>
        </label>
      )}

      <div className="depth-probe-bar__readout">
        {loading && <span className="text-gray-500">Загрузка…</span>}
        {error && <span className="text-red-400">{error}</span>}
        {!loading && !error && probe && (
          <>
            <span className="text-gray-500">Пиксель</span>
            <span className="font-mono tabular-nums text-gray-300">
              {probe.x}, {probe.y}
            </span>
            <span className="depth-probe-bar__depth">{probe.depthCm.toFixed(1)} см</span>
          </>
        )}
        {!loading && !error && !probe && (
          <span className="text-gray-600">Наведите курсор на карту или фото</span>
        )}
      </div>
    </div>
  );
}
