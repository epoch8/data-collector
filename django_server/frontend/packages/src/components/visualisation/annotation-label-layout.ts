import type { InferenceSegment } from '@/types/datapipe';

export function approxTextWidth(text: string, fontSize: number): number {
  let w = 0;
  for (const ch of text) {
    w += ch === ' ' ? fontSize * 0.3 : fontSize * (ch.charCodeAt(0) > 127 ? 0.56 : 0.5);
  }
  return w;
}

export function formatSegmentLabel(label: string, valueCm?: number): string {
  if (valueCm != null && Number.isFinite(valueCm)) {
    return `${label} — ${valueCm.toFixed(1)} см`;
  }
  return label;
}

export interface SegmentGeometry {
  midX: number;
  midY: number;
  angleDeg: number;
  length: number;
  normalOffset: number;
  text: string;
  boxW: number;
  boxH: number;
}

const FONT_SIZE = 13;
const PAD_X = 6;
const PAD_Y = 4;

interface Aabb {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

function labelAabb(
  midX: number,
  midY: number,
  boxW: number,
  boxH: number,
  angleDeg: number,
  normalOffset: number,
): Aabb {
  const rad = (angleDeg * Math.PI) / 180;
  const nx = -Math.sin(rad) * normalOffset;
  const ny = Math.cos(rad) * normalOffset;
  const cx = midX + nx;
  const cy = midY + ny;
  const hw = boxW / 2 + 4;
  const hh = boxH / 2 + 4;
  const c = Math.abs(Math.cos(rad));
  const s = Math.abs(Math.sin(rad));
  const extW = hw * c + hh * s;
  const extH = hw * s + hh * c;
  return { x0: cx - extW, y0: cy - extH, x1: cx + extW, y1: cy + extH };
}

function overlaps(a: Aabb, b: Aabb, gap = 6): boolean {
  return !(
    a.x1 + gap < b.x0 ||
    b.x1 + gap < a.x0 ||
    a.y1 + gap < b.y0 ||
    b.y1 + gap < a.y0
  );
}

/** Раскладка подписей измерений: на линии + сдвиг по нормали при пересечениях. */
export function layoutSegmentLabels(segments: InferenceSegment[]): SegmentGeometry[] {
  const placed: Aabb[] = [];
  const out: SegmentGeometry[] = [];

  segments.forEach((seg, index) => {
    const dx = seg.x2 - seg.x1;
    const dy = seg.y2 - seg.y1;
    const length = Math.hypot(dx, dy) || 1;
    let angleDeg = (Math.atan2(dy, dx) * 180) / Math.PI;
    if (angleDeg > 90) angleDeg -= 180;
    if (angleDeg < -90) angleDeg += 180;

    const text = formatSegmentLabel(seg.label, seg.value_cm);
    const fontSize = text.length > 32 ? 11 : FONT_SIZE;
    const boxW = approxTextWidth(text, fontSize) + PAD_X * 2;
    const boxH = fontSize + PAD_Y * 2;
    const midX = (seg.x1 + seg.x2) / 2;
    const midY = (seg.y1 + seg.y2) / 2;

    const tryOffsets = [0, 16, -16, 28, -28, 40, -40];
    if (index % 2 === 1) tryOffsets.reverse();

    let normalOffset = 0;
    for (const off of tryOffsets) {
      const aabb = labelAabb(midX, midY, boxW, boxH, angleDeg, off);
      if (!placed.some(p => overlaps(p, aabb))) {
        normalOffset = off;
        placed.push(aabb);
        break;
      }
    }

    out.push({
      midX,
      midY,
      angleDeg,
      length,
      normalOffset,
      text,
      boxW,
      boxH,
    });
  });

  return out;
}

export function pointLabelAnchor(
  px: number,
  py: number,
  index: number,
  imageW: number,
  imageH: number,
): { dx: number; dy: number; anchor: 'start' | 'end' } {
  const margin = 48;
  const nearRight = px > imageW - margin;
  const nearLeft = px < margin;
  const nearTop = py < margin;
  const nearBottom = py > imageH - margin;

  if (nearRight && nearTop) return { dx: -10, dy: 14, anchor: 'end' };
  if (nearRight) return { dx: -10, dy: -6, anchor: 'end' };
  if (nearLeft && nearBottom) return { dx: 10, dy: -14, anchor: 'start' };
  if (nearLeft) return { dx: 10, dy: -6, anchor: 'start' };
  if (nearTop) return { dx: 6, dy: 14, anchor: 'start' };
  if (nearBottom) return { dx: 6, dy: -14, anchor: 'start' };

  const corners = [
    { dx: 11, dy: -7, anchor: 'start' as const },
    { dx: -11, dy: -7, anchor: 'end' as const },
    { dx: 11, dy: 10, anchor: 'start' as const },
    { dx: -11, dy: 10, anchor: 'end' as const },
  ];
  return corners[index % corners.length];
}

export const YOLO_FONT_SIZE = FONT_SIZE;
export const YOLO_PAD_X = PAD_X;
export const YOLO_PAD_Y = PAD_Y;
