import type { ConfigField } from '@/types/config';
import { fieldHint, fieldLabel, fieldRequired } from '@/lib/config-field';

interface Props {
  field: ConfigField;
  value: string | number | undefined;
  onChange: (value: string | number) => void;
  readOnly?: boolean;
}

export function TextInputWidget({ field, value, onChange, readOnly }: Props) {
  return (
    <div className="border border-gray-800 rounded-lg p-4 bg-gray-900/30">
      <label className="flex items-center gap-2 mb-2">
        <span className="text-sm text-gray-300 font-medium">{fieldLabel(field)}</span>
        {fieldRequired(field) && <span className="text-red-400 text-[10px]">required</span>}
        <span className="text-[10px] text-gray-600 font-mono ml-auto">{field.field_id}</span>
      </label>
      {fieldHint(field) && (
        <p className="text-xs text-gray-500 mb-2">{fieldHint(field)}</p>
      )}
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
        className="w-full bg-gray-800/60 border border-gray-700 rounded-md px-3 py-2 text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-blue-500/60 focus:ring-1 focus:ring-blue-500/30 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
      />
    </div>
  );
}
