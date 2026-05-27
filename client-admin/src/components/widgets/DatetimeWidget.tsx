import type { ConfigField } from '@/types/config';
import { fieldHint, fieldLabel, fieldRequired } from '@/lib/config-field';

interface Props {
  field: ConfigField;
  value: string | undefined;
}

export function DatetimeWidget({ field, value }: Props) {
  const displayValue = value
    ? new Date(value).toLocaleString('ru-RU', {
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
      })
    : '—';

  return (
    <div className="border border-gray-800 rounded-lg p-4 bg-gray-900/30">
      <label className="flex items-center gap-2 mb-2">
        <span className="text-sm text-gray-300 font-medium">{fieldLabel(field)}</span>
        {fieldRequired(field) && <span className="text-red-400 text-[10px]">required</span>}
        <span className="text-[10px] text-gray-600 bg-gray-800 px-1.5 py-0.5 rounded ml-auto">readonly</span>
      </label>
      {fieldHint(field) && (
        <p className="text-xs text-gray-500 mb-2">{fieldHint(field)}</p>
      )}
      <div className="text-sm text-gray-200 font-mono bg-gray-800/60 border border-gray-700 rounded-md px-3 py-2">
        {displayValue}
      </div>
      {value && (
        <div className="text-xs text-gray-500 mt-1.5 font-mono">{value}</div>
      )}
    </div>
  );
}
