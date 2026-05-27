const PHASE_LABELS: Record<string, string> = {
  completed: 'Завершён',
  awaiting_blobs: 'Ожидает файлы',
  ready_to_commit: 'Готов к commit',
  failed: 'Ошибка',
  uploading: 'Загрузка',
};

const PHASE_STYLES: Record<string, string> = {
  completed: 'bg-emerald-950/50 text-emerald-400 border-emerald-700/50',
  awaiting_blobs: 'bg-amber-950/50 text-amber-400 border-amber-700/50',
  ready_to_commit: 'bg-blue-950/50 text-blue-400 border-blue-700/50',
  failed: 'bg-red-950/50 text-red-400 border-red-700/50',
  uploading: 'bg-amber-950/50 text-amber-400 border-amber-700/50',
};

export function phaseLabel(phase: string): string {
  return PHASE_LABELS[phase] ?? phase;
}

export function phaseBadgeClass(phase: string): string {
  return PHASE_STYLES[phase] ?? 'bg-gray-800/80 text-gray-400 border-gray-700';
}
