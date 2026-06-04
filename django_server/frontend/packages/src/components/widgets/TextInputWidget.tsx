import type { ConfigField } from '@/types/config';
import { fieldHint } from '@/lib/config-field';
import { FieldCard } from '@/components/ui/FieldCard';

interface Props {
  field: ConfigField;
  value: string | number | undefined;
  onChange: (value: string | number) => void;
  readOnly?: boolean;
}

export function TextInputWidget({ field, value, onChange, readOnly }: Props) {
  const hint = fieldHint(field);
  return (
    <FieldCard field={field} variant="data">
      {hint && <p className="text-xs text-gray-500 mb-3">{hint}</p>}
      <input
        type="text"
        value={value ?? ''}
        readOnly={readOnly}
        disabled={readOnly}
        onChange={e => {
          const raw = e.target.value;
          const asNum = Number(raw);
          onChange(!isNaN(asNum) && raw.trim() !== '' && typeof value === 'number' ? asNum : raw);
        }}
        className="ui-input"
      />
    </FieldCard>
  );
}
