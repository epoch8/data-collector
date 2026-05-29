import { useMemo, useState, type ReactNode } from 'react';
import type { AnnotationLayer } from '@/types/datapipe';
import { layoutSegmentLabels, pointLabelAnchor } from '@/components/visualisation/annotation-label-layout';
import { SegmentLineLabel, YoloLabel } from '@/components/visualisation/YoloLabel';

const PALETTE = {
  gt: {
    box: '#22c55e',
    boxFill: 'rgba(34, 197, 94, 0.08)',
    point: '#f59e0b',
    segment: '#c084fc',
    label: 'GT',
  },
  inference: {
    box: '#06b6d4',
    boxFill: 'rgba(6, 182, 212, 0.08)',
    point: '#3b82f6',
    segment: '#8b5cf6',
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
  overlay?: ReactNode;
  onFramePointerMove?: (e: React.PointerEvent<HTMLDivElement>) => void;
  onFramePointerLeave?: () => void;
  depthProbe?: { x: number; y: number } | null;
}

function labelColor(label: string, palette: keyof typeof PALETTE): string {
  if (palette === 'gt') {
    let h = 0;
    for (let i = 0; i < label.length; i++) h = (h * 31 + label.charCodeAt(i)) >>> 0;
    return `hsl(${h % 360} 70% 52%)`;
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

  const segmentLayouts = useMemo(() => {
    const map = new Map<string, ReturnType<typeof layoutSegmentLabels>>();
    for (const layer of visibleLayers) {
      if (layer.segments?.length) {
        map.set(layer.id, layoutSegmentLabels(layer.segments));
      }
    }
    return map;
  }, [visibleLayers]);

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
            const segLayout = segmentLayouts.get(layer.id);

            return (
              <g key={layer.id}>
                {showBoxes &&
                  layer.boxes.map((box, idx) => {
                    const w = Math.max(0, box.xbr - box.xtl);
                    const h = Math.max(0, box.ybr - box.ytl);
                    const boxLabel = box.label || p.label;
                    return (
                      <g key={`${layer.id}-b-${idx}`}>
                        <rect
                          x={box.xtl}
                          y={box.ytl}
                          width={w}
                          height={h}
                          fill={p.boxFill}
                          stroke={p.box}
                          strokeWidth={2}
                          vectorEffect="non-scaling-stroke"
                        />
                        {showLabels && (
                          <YoloLabel
                            x={box.xtl}
                            y={box.ytl}
                            text={boxLabel}
                            color={p.box}
                            anchor="start"
                            valign="above"
                          />
                        )}
                      </g>
                    );
                  })}

                {layer.segments?.map((seg, idx) => {
                  const layout = segLayout?.[idx];
                  return (
                    <g key={`${layer.id}-s-${idx}`}>
                      <line
                        x1={seg.x1}
                        y1={seg.y1}
                        x2={seg.x2}
                        y2={seg.y2}
                        stroke={p.segment}
                        strokeWidth={2.5}
                        strokeDasharray="8 5"
                        vectorEffect="non-scaling-stroke"
                        opacity={0.9}
                      />
                      {showLabels && layout && (
                        <SegmentLineLabel
                          midX={layout.midX}
                          midY={layout.midY}
                          angleDeg={layout.angleDeg}
                          normalOffset={layout.normalOffset}
                          text={layout.text}
                          boxW={layout.boxW}
                          boxH={layout.boxH}
                          color={p.segment}
                        />
                      )}
                    </g>
                  );
                })}

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
                  const anchor = pointLabelAnchor(point.x, point.y, idx, width, height);

                  return (
                    <g
                      key={`${layer.id}-p-${idx}`}
                      className="annotation-keypoint"
                      opacity={dimmed && !isActive ? 0.35 : 1}
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
                        r={isActive ? 8 : 6}
                        fill="rgba(15, 17, 23, 0.8)"
                        stroke={color}
                        strokeWidth={isActive ? 2.5 : 2}
                        vectorEffect="non-scaling-stroke"
                      />
                      <circle cx={point.x} cy={point.y} r={isActive ? 3 : 2.5} fill={color} />
                      {showPointLabel && (
                        <YoloLabel
                          x={point.x + anchor.dx}
                          y={point.y + anchor.dy}
                          text={point.label}
                          color={color}
                          anchor={anchor.anchor}
                          valign="on"
                        />
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
