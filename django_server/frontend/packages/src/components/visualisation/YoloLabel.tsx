import { approxTextWidth, YOLO_FONT_SIZE, YOLO_PAD_X, YOLO_PAD_Y } from '@/components/visualisation/annotation-label-layout';

interface Props {
  x: number;
  y: number;
  text: string;
  color: string;
  anchor?: 'start' | 'middle' | 'end';
  /** Позиция якоря: верх-лево (для bbox), центр, и т.д. */
  valign?: 'above' | 'on' | 'below';
  fontSize?: number;
}

/** Компактная подпись в стиле YOLO: заливка цветом класса, белый текст. */
export function YoloLabel({
  x,
  y,
  text,
  color,
  anchor = 'start',
  valign = 'above',
  fontSize = YOLO_FONT_SIZE,
}: Props) {
  if (!text) return null;

  const boxW = approxTextWidth(text, fontSize) + YOLO_PAD_X * 2;
  const boxH = fontSize + YOLO_PAD_Y * 2;

  let bx = x;
  if (anchor === 'middle') bx = x - boxW / 2;
  if (anchor === 'end') bx = x - boxW;

  let by = y - boxH;
  if (valign === 'on') by = y - boxH / 2;
  if (valign === 'below') by = y;

  const textX =
    anchor === 'middle' ? x : anchor === 'end' ? bx + boxW - YOLO_PAD_X : bx + YOLO_PAD_X;
  const textY = by + boxH / 2;

  return (
    <g className="yolo-label">
      <rect
        x={bx}
        y={by}
        width={boxW}
        height={boxH}
        rx={2}
        ry={2}
        fill={color}
        fillOpacity={0.92}
      />
      <text
        x={textX}
        y={textY}
        fill="#ffffff"
        fontSize={fontSize}
        fontWeight={600}
        textAnchor={anchor}
        dominantBaseline="central"
        style={{ fontFamily: 'system-ui, -apple-system, sans-serif' }}
      >
        {text}
      </text>
    </g>
  );
}

interface SegmentProps {
  midX: number;
  midY: number;
  angleDeg: number;
  normalOffset: number;
  text: string;
  boxW: number;
  boxH: number;
  color: string;
}

/** Подпись измерения на линии (повёрнута вдоль отрезка). */
export function SegmentLineLabel({
  midX,
  midY,
  angleDeg,
  normalOffset,
  text,
  boxW,
  boxH,
  color,
}: SegmentProps) {
  const fontSize = text.length > 32 ? 11 : YOLO_FONT_SIZE;
  const w = boxW || approxTextWidth(text, fontSize) + YOLO_PAD_X * 2;
  const h = boxH || fontSize + YOLO_PAD_Y * 2;

  return (
    <g
      className="yolo-label yolo-label--segment"
      transform={`translate(${midX}, ${midY}) rotate(${angleDeg})`}
    >
      <g transform={`translate(0, ${normalOffset})`}>
        <rect
          x={-w / 2}
          y={-h / 2}
          width={w}
          height={h}
          rx={2}
          ry={2}
          fill={color}
          fillOpacity={0.93}
        />
        <text
          x={0}
          y={0}
          fill="#ffffff"
          fontSize={fontSize}
          fontWeight={600}
          textAnchor="middle"
          dominantBaseline="central"
          style={{ fontFamily: 'system-ui, -apple-system, sans-serif' }}
        >
          {text}
        </text>
      </g>
    </g>
  );
}
