import type { ConfigField } from '@/types/config';
import type { BlobInfo } from '@/types/manifest';
import { sortFields } from '@/lib/config-field';
import { FieldWidget } from '@/components/widgets/FieldWidget';

interface Props {
  fields: ConfigField[];
  data: Record<string, unknown>;
  blobs: BlobInfo[];
  onChange: (fieldId: string, value: unknown) => void;
  readOnly?: boolean;
}

export function DataTab({ fields, data, blobs, onChange, readOnly }: Props) {
  const ordered = sortFields(fields);

  return (
    <div className="max-w-3xl space-y-4">
      <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
        Данные формы
      </h3>
      {ordered.map(field => (
        <FieldWidget
          key={field.field_id}
          field={field}
          value={data[field.field_id]}
          onChange={v => onChange(field.field_id, v)}
          blobs={blobs}
          readOnly={readOnly}
        />
      ))}
    </div>
  );
}
