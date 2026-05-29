/** Значения в .npy — расстояние до камеры в метрах. */
export function formatDepthMeters(meters: number): string {
  if (!Number.isFinite(meters)) return '—';
  if (meters >= 10) return `${meters.toFixed(1)} м`;
  if (meters >= 1) return `${meters.toFixed(2)} м`;
  return `${(meters * 100).toFixed(0)} см`;
}

export function formatDepthRange(min: number, max: number): string {
  return `${formatDepthMeters(min)} – ${formatDepthMeters(max)}`;
}
