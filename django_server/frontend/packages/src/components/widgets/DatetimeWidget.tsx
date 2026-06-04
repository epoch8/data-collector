import type { ConfigField } from '@/types/config';
import { fieldHint } from '@/lib/config-field';
import { FieldCard } from '@/components/ui/FieldCard';

interface Props {
  field: ConfigField;
  value: string | undefined;
}

export function DatetimeWidget({ field, value }: Props) {
  const hint = fieldHint(field);
  const displayValue = value
    ? new Date(value).toLocaleString('ru-RU', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    : '—';

  return (
    <FieldCard field={field} variant="data">
      {hint && <p className="text-xs text-gray-500 mb-3">{hint}</p>}
      <div className="ui-input text-gray-200 font-mono">{displayValue}</div>
      {value && <p className="text-[10px] text-gray-600 mt-2 font-mono">{value}</p>}
    </FieldCard>
  );
}
