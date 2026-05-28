import { useMemo, useState, type ReactNode } from 'react';
import type { AnnotationLayer } from '@/types/datapipe';

const PALETTE = {
  gt: {
    box: '#22c55e',
    boxFill: 'rgba(34, 197, 94, 0.08)',
    point: '#f59e0b',
    segment: '#fbbf24',
    label: 'GT',
  },
  inference: {
    box: '#22d3ee',
    boxFill: 'rgba(34, 211, 238, 0.08)',
    point: '#60a5fa',
    segment: '#a78bfa',
    label: 'Inference',
  },
} as const;

interface Props {
  src: string;
  alt: string;
  width: number;
  height: number;
  layers: AnnotationLayer[];
  showBoxes: boolean;
  showLabels: boolean;
  selectedPoint: { layerId: string; index: number } | null;
  onSelectPoint: (sel: { layerId: string; index: number } | null) => void;
  /** Слой поверх кадра (например карта глубины). */
  overlay?: ReactNode;
  onFramePointerMove?: (e: React.PointerEvent<HTMLDivElement>) => void;
  onFramePointerLeave?: () => void;
  depthProbe?: { x: number; y: number } | null;
}

function labelColor(label: string, palette: keyof typeof PALETTE): string {
  if (palette === 'gt') {
    let h = 0;
    for (let i = 0; i < label.length; i++) h = (h * 31 + label.charCodeAt(i)) >>> 0;
    return `hsl(${h % 360} 75% 58%)`;
  }
  return PALETTE.inference.point;
}

export function AnnotationCanvas({
  src,
  alt,
  width,
  height,
  layers,
  showBoxes,
  showLabels,
  selectedPoint,
  onSelectPoint,
  overlay,
  onFramePointerMove,
  onFramePointerLeave,
  depthProbe,
}: Props) {
  const [hovered, setHovered] = useState<{ layerId: string; index: number } | null>(null);
  const active = selectedPoint ?? hovered;

  const visibleLayers = useMemo(() => layers.filter(l => l.visible), [layers]);

  return (
    <div className="annotation-stage">
      <div
        className="annotation-stage__frame"
        onPointerMove={onFramePointerMove}
        onPointerLeave={onFramePointerLeave}
      >
        <img src={src} alt={alt} className="annotation-stage__img" draggable={false} />
        <svg
          className="annotation-stage__svg"
          viewBox={`0 0 ${width} ${height}`}
          preserveAspectRatio="xMidYMid meet"
        >
          {visibleLayers.map(layer => {
            const p = PALETTE[layer.palette];
            return (
              <g key={layer.id}>
                {showBoxes &&
                  layer.boxes.map((box, idx) => {
                    const w = Math.max(0, box.xbr - box.xtl);
                    const h = Math.max(0, box.ybr - box.ytl);
                    return (
                      <g key={`${layer.id}-b-${idx}`}>
                        <rect
                          x={box.xtl}
                          y={box.ytl}
                          width={w}
                          height={h}
                          fill={p.boxFill}
                          stroke={p.box}
                          strokeWidth={2.5}
                          vectorEffect="non-scaling-stroke"
                        />
                        {showLabels && (
                          <text
                            x={box.xtl + 4}
                            y={Math.max(14, box.ytl - 6)}
                            fill={p.box}
                            fontSize="11"
                            fontWeight="600"
                          >
                            {p.label}
                          </text>
                        )}
                      </g>
                    );
                  })}

                {layer.segments?.map((seg, idx) => (
                  <g key={`${layer.id}-s-${idx}`}>
                    <line
                      x1={seg.x1}
                      y1={seg.y1}
                      x2={seg.x2}
                      y2={seg.y2}
                      stroke={p.segment}
                      strokeWidth={2}
                      strokeDasharray="6 4"
                      vectorEffect="non-scaling-stroke"
                    />
                    {showLabels && seg.label && (
                      <text
                        x={(seg.x1 + seg.x2) / 2}
                        y={(seg.y1 + seg.y2) / 2 - 6}
                        fill={p.segment}
                        fontSize="9"
                        textAnchor="middle"
                      >
                        {seg.value_cm != null ? `${seg.value_cm.toFixed(1)} cm` : seg.label}
                      </text>
                    )}
                  </g>
                ))}

                {layer.points.map((point, idx) => {
                  const isActive =
                    active?.layerId === layer.id && active.index === idx;
                  const dimmed =
                    selectedPoint != null &&
                    !(selectedPoint.layerId === layer.id && selectedPoint.index === idx) &&
                    hovered == null;
                  const color =
                    layer.palette === 'gt' ? labelColor(point.label, 'gt') : p.point;
                  const showPointLabel = showLabels || isActive;

                  return (
                    <g
                      key={`${layer.id}-p-${idx}`}
                      className="annotation-keypoint"
                      opacity={dimmed && !isActive ? 0.3 : 1}
                      onMouseEnter={() => setHovered({ layerId: layer.id, index: idx })}
                      onMouseLeave={() => setHovered(null)}
                      onClick={e => {
                        e.stopPropagation();
                        const sel = { layerId: layer.id, index: idx };
                        onSelectPoint(
                          selectedPoint?.layerId === sel.layerId &&
                            selectedPoint.index === sel.index
                            ? null
                            : sel,
                        );
                      }}
                    >
                      <circle cx={point.x} cy={point.y} r={14} fill="transparent" />
                      <circle
                        cx={point.x}
                        cy={point.y}
                        r={isActive ? 9 : 7}
                        fill="rgba(15, 17, 23, 0.75)"
                        stroke={color}
                        strokeWidth={isActive ? 3 : 2}
                        vectorEffect="non-scaling-stroke"
                      />
                      <circle cx={point.x} cy={point.y} r={isActive ? 3.5 : 2.5} fill={color} />
                      {showPointLabel && (
                        <text
                          x={point.x + 10}
                          y={point.y - 8}
                          fill="#f3f4f6"
                          fontSize="10"
                        >
                          {point.label}
                        </text>
                      )}
                    </g>
                  );
                })}
              </g>
            );
          })}
        </svg>
        {overlay}
        {depthProbe && (
          <svg
            className="annotation-stage__svg annotation-stage__probe"
            viewBox={`0 0 ${width} ${height}`}
            preserveAspectRatio="xMidYMid meet"
            aria-hidden
          >
            <circle
              cx={depthProbe.x}
              cy={depthProbe.y}
              r={12}
              fill="none"
              stroke="rgba(255,255,255,0.9)"
              strokeWidth={2}
              vectorEffect="non-scaling-stroke"
            />
            <circle
              cx={depthProbe.x}
              cy={depthProbe.y}
              r={3}
              fill="#fb923c"
              stroke="rgba(15,17,23,0.8)"
              strokeWidth={1}
            />
          </svg>
        )}
      </div>
      <div className="flex flex-wrap gap-3 mt-2 px-1">
        {(['gt', 'inference'] as const).map(key => {
          const on = visibleLayers.some(l => l.palette === key);
          if (!on) return null;
          const c = PALETTE[key];
          return (
            <span key={key} className="text-[10px] text-gray-500 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full" style={{ background: c.point }} />
              {c.label}
            </span>
          );
        })}
      </div>
    </div>
  );
}

