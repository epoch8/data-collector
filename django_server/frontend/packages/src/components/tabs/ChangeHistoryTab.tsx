import type { FieldChangeLogEntry } from '@/types/manifest';
import { EmptyState } from '@/components/ui/EmptyState';
import { formatDateTime } from '@/lib/format';

interface Props {
  entries: FieldChangeLogEntry[];
  loading?: boolean;
}

function toViewValue(value: unknown): string {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export function ChangeHistoryTab({ entries, loading }: Props) {
  if (loading) {
    return <p className="text-sm text-gray-500">Загрузка истории изменений...</p>;
  }

  if (!entries.length) {
    return (
      <EmptyState
        title="История изменений пуста"
        description="Для этого пакета пока нет ручных корректировок."
      />
    );
  }

  return (
    <div className="space-y-3">
      {entries
        .slice()
        .sort((a, b) => new Date(b.changed_at).getTime() - new Date(a.changed_at).getTime())
        .map((entry, idx) => (
          <div key={`${entry.package_id}-${entry.field_id}-${entry.changed_at}-${idx}`} className="ui-card p-4">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
              <p className="text-sm text-gray-200">
                Поле: <span className="font-mono text-blue-300">{entry.field_id}</span>
              </p>
              <p className="text-xs text-gray-500">{formatDateTime(entry.changed_at)}</p>
            </div>
            <p className="text-sm text-gray-400 mb-2">
              Причина: <span className="text-gray-200">{entry.reason}</span>
            </p>
            <p className="text-xs text-gray-500 mb-2">
              Верификатор: {entry.verifier_email?.trim() ? entry.verifier_email : 'не указан'}
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="rounded-md border border-red-500/20 bg-red-500/5 p-3">
                <p className="text-xs uppercase tracking-wide text-red-300 mb-1">Старое значение</p>
                <pre className="text-xs text-gray-200 whitespace-pre-wrap break-words">{toViewValue(entry.before)}</pre>
              </div>
              <div className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-3">
                <p className="text-xs uppercase tracking-wide text-emerald-300 mb-1">Новое значение</p>
                <pre className="text-xs text-gray-200 whitespace-pre-wrap break-words">{toViewValue(entry.after)}</pre>
              </div>
            </div>
          </div>
        ))}
    </div>
  );
}
