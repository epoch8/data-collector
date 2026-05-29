import type { DepthProbe } from '@/lib/depth-npy';
import { formatDepthMeters } from '@/lib/depth-format';
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
      <div className="depth-probe-bar__left">
        <span className="depth-probe-bar__label">Глубина</span>
        <div className="depth-probe-bar__modes" role="group" aria-label="Режим отображения">
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
            <span className="sr-only">Прозрачность наложения</span>
            <input
              type="range"
              min={15}
              max={85}
              value={Math.round(overlayOpacity * 100)}
              onChange={e => onOverlayOpacityChange(Number(e.target.value) / 100)}
              className="depth-range"
              title="Прозрачность"
            />
            <span className="depth-probe-bar__opacity-val">{Math.round(overlayOpacity * 100)}%</span>
          </label>
        )}
      </div>

      <div className="depth-probe-bar__readout">
        {loading && (
          <span className="depth-probe-bar__status depth-probe-bar__status--loading">
            Загрузка карты…
          </span>
        )}
        {error && <span className="depth-probe-bar__status depth-probe-bar__status--error">{error}</span>}
        {!loading && !error && probe && (
          <div className="depth-probe-bar__measure">
            <span className="depth-probe-bar__measure-label">Расстояние</span>
            <span className="depth-probe-bar__depth">{formatDepthMeters(probe.depthM)}</span>
            <span className="depth-probe-bar__coords font-mono tabular-nums">
              ({probe.x}, {probe.y})
            </span>
          </div>
        )}
        {!loading && !error && !probe && (
          <span className="depth-probe-bar__status">Наведите на фото или карту глубины</span>
        )}
      </div>
    </div>
  );
}
