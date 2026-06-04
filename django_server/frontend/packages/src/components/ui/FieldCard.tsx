import type { ReactNode } from 'react';
import type { ConfigField } from '@/types/config';
import { fieldLabel, fieldRequired } from '@/lib/config-field';

interface Props {
  field: ConfigField;
  children: ReactNode;
  variant?: 'data' | 'media' | 'default';
  id?: string;
}

const VARIANT_CLASS = {
  data: 'ui-card ui-card--data',
  media: 'ui-card ui-card--media',
  default: 'ui-card',
};

export function FieldCard({ field, children, variant = 'data', id }: Props) {
  return (
    <section id={id ?? `field-${field.field_id}`} className={`p-4 scroll-mt-24 ${VARIANT_CLASS[variant]}`}>
      <header className="flex items-start gap-2 mb-3">
        <FieldTypeIcon type={field.type} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="text-base font-medium text-gray-200">{fieldLabel(field)}</h4>
            {fieldRequired(field) && (
              <span className="text-xs text-red-400/90 uppercase tracking-wide">обязательно</span>
            )}
          </div>
        </div>
      </header>
      {children}
      <details className="mt-3 group">
        <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-500 list-none">
          <span className="group-open:hidden">Техническое</span>
          <span className="hidden group-open:inline">Скрыть</span>
        </summary>
        <p className="mt-1 text-xs font-mono text-gray-600">{field.field_id}</p>
      </details>
    </section>
  );
}

function FieldTypeIcon({ type }: { type: ConfigField['type'] }) {
  const icons: Record<ConfigField['type'], string> = {
    text_input: 'Aa',
    datetime: '⏱',
    instruction: 'ℹ',
    camera_photo: '📷',
  };
  return (
    <span
      className="flex-shrink-0 w-8 h-8 rounded-md bg-gray-800/80 border border-gray-700/60 flex items-center justify-center text-xs text-gray-400"
      aria-hidden
    >
      {icons[type]}
    </span>
  );
}
