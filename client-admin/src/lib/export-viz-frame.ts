import type { AnnotationLayer } from '@/types/datapipe';
import type { DepthMapData } from '@/lib/depth-npy';
import { rasterizeDepthMap } from '@/lib/depth-colormap';
import {
  approxTextWidth,
  layoutSegmentLabels,
  YOLO_FONT_SIZE,
  YOLO_PAD_X,
  YOLO_PAD_Y,
} from '@/components/visualisation/annotation-label-layout';

const PALETTE = {
  gt: {
    box: '#22c55e',
    boxFill: 'rgba(34, 197, 94, 0.08)',
    point: '#f59e0b',
    segment: '#c084fc',
    layerLabel: 'GT',
  },
  inference: {
    box: '#06b6d4',
    boxFill: 'rgba(6, 182, 212, 0.08)',
    point: '#3b82f6',
    segment: '#8b5cf6',
    layerLabel: 'Inference',
  },
} as const;

export interface VizExportOptions {
  imageUrl: string;
  width: number;
  height: number;
  layers: AnnotationLayer[];
  showBoxes: boolean;
  showLabels: boolean;
  depth?: {
    data: DepthMapData;
    opacity: number;
    vmin: number;
    vmax: number;
  };
}

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error('Не удалось загрузить изображение'));
    img.src = url;
  });
}

function labelColor(label: string, palette: keyof typeof PALETTE): string {
  if (palette === 'gt') {
    let h = 0;
    for (let i = 0; i < label.length; i++) h = (h * 31 + label.charCodeAt(i)) >>> 0;
    return `hsl(${h % 360} 70% 52%)`;
  }
  return PALETTE.inference.point;
}

function drawYoloPill(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  text: string,
  color: string,
  anchor: 'start' | 'middle' | 'end' = 'start',
  valign: 'above' | 'on' = 'above',
  fontSize = YOLO_FONT_SIZE,
): void {
  ctx.font = `600 ${fontSize}px system-ui, -apple-system, sans-serif`;
  const boxW = approxTextWidth(text, fontSize) + YOLO_PAD_X * 2;
  const boxH = fontSize + YOLO_PAD_Y * 2;

  let bx = x;
  if (anchor === 'middle') bx = x - boxW / 2;
  if (anchor === 'end') bx = x - boxW;

  let by = y - boxH;
  if (valign === 'on') by = y - boxH / 2;

  const textX =
    anchor === 'middle' ? x : anchor === 'end' ? bx + boxW - YOLO_PAD_X : bx + YOLO_PAD_X;
  const textY = by + boxH / 2;

  ctx.fillStyle = color;
  ctx.globalAlpha = 0.92;
  ctx.fillRect(bx, by, boxW, boxH);
  ctx.globalAlpha = 1;

  ctx.fillStyle = '#ffffff';
  ctx.textAlign = anchor === 'middle' ? 'center' : anchor;
  ctx.textBaseline = 'middle';
  ctx.fillText(text, textX, textY);
}

function drawSegmentOnLine(
  ctx: CanvasRenderingContext2D,
  midX: number,
  midY: number,
  angleDeg: number,
  normalOffset: number,
  text: string,
  color: string,
): void {
  const fontSize = text.length > 32 ? 11 : YOLO_FONT_SIZE;
  ctx.save();
  ctx.translate(midX, midY);
  ctx.rotate((angleDeg * Math.PI) / 180);
  ctx.translate(0, normalOffset);
  drawYoloPill(ctx, 0, 0, text, color, 'middle', 'on', fontSize);
  ctx.restore();
}

function drawLayers(
  ctx: CanvasRenderingContext2D,
  layers: AnnotationLayer[],
  showBoxes: boolean,
  showLabels: boolean,
): void {
  for (const layer of layers) {
    if (!layer.visible) continue;
    const p = PALETTE[layer.palette];

    if (showBoxes) {
      for (const box of layer.boxes) {
        const w = Math.max(0, box.xbr - box.xtl);
        const h = Math.max(0, box.ybr - box.ytl);
        ctx.fillStyle = p.boxFill;
        ctx.fillRect(box.xtl, box.ytl, w, h);
        ctx.strokeStyle = p.box;
        ctx.lineWidth = 2.5;
        ctx.strokeRect(box.xtl, box.ytl, w, h);
        if (showLabels) {
          drawYoloPill(ctx, box.xtl, box.ytl, box.label || p.layerLabel, p.box, 'start', 'above');
        }
      }
    }

    if (layer.segments?.length) {
      const layouts = layoutSegmentLabels(layer.segments);
      layer.segments.forEach((seg, idx) => {
        ctx.strokeStyle = p.segment;
        ctx.lineWidth = 2.5;
        ctx.setLineDash([8, 5]);
        ctx.beginPath();
        ctx.moveTo(seg.x1, seg.y1);
        ctx.lineTo(seg.x2, seg.y2);
        ctx.stroke();
        ctx.setLineDash([]);

        if (showLabels && layouts[idx]) {
          const layout = layouts[idx];
          drawSegmentOnLine(
            ctx,
            layout.midX,
            layout.midY,
            layout.angleDeg,
            layout.normalOffset,
            layout.text,
            p.segment,
          );
        }
      });
    }

    for (const point of layer.points) {
      const color = layer.palette === 'gt' ? labelColor(point.label, 'gt') : p.point;
      ctx.fillStyle = 'rgba(15, 17, 23, 0.8)';
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(point.x, point.y, 7, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(point.x, point.y, 2.5, 0, Math.PI * 2);
      ctx.fill();

      if (showLabels) {
        drawYoloPill(ctx, point.x + 12, point.y - 4, point.label, color, 'start', 'above');
      }
    }
  }
}

function drawDepth(
  ctx: CanvasRenderingContext2D,
  depth: NonNullable<VizExportOptions['depth']>,
  width: number,
  height: number,
): void {
  const { data, opacity, vmin, vmax } = depth;
  const raster = rasterizeDepthMap(
    data.values,
    data.gridWidth,
    data.gridHeight,
    vmin,
    vmax,
    'overlay',
  );

  const off = document.createElement('canvas');
  off.width = data.gridWidth;
  off.height = data.gridHeight;
  const offCtx = off.getContext('2d');
  if (!offCtx) return;
  offCtx.putImageData(raster, 0, 0);

  ctx.save();
  ctx.globalAlpha = opacity;
  ctx.drawImage(off, 0, 0, data.gridWidth, data.gridHeight, 0, 0, width, height);
  ctx.restore();
}

export async function renderVizFrameToBlob(options: VizExportOptions): Promise<Blob> {
  const { imageUrl, width, height, layers, showBoxes, showLabels, depth } = options;

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('Canvas не поддерживается');

  const img = await loadImage(imageUrl);
  ctx.drawImage(img, 0, 0, width, height);

  if (depth) {
    drawDepth(ctx, depth, width, height);
  }

  drawLayers(ctx, layers, showBoxes, showLabels);

  return new Promise((resolve, reject) => {
    canvas.toBlob(
      blob => {
        if (blob) resolve(blob);
        else reject(new Error('Не удалось сформировать PNG'));
      },
      'image/png',
      1,
    );
  });
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
