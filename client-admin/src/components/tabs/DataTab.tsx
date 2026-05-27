import { useEffect, useState, useMemo } from 'react';
import type { ConfigField, Flow } from '@/types/config';
import type { BlobInfo } from '@/types/manifest';
import { buildFlowSections, flattenSections } from '@/lib/form-fields';
import { fieldLabel } from '@/lib/config-field';
import { FieldWidget } from '@/components/widgets/FieldWidget';
import { EmptyState } from '@/components/ui/EmptyState';

interface Props {
  fields: ConfigField[];
  flow?: Flow;
  data: Record<string, unknown>;
  blobs: BlobInfo[];
  onChange: (fieldId: string, value: unknown) => void;
  readOnly?: boolean;
}

export function DataTab({ fields, flow, data, blobs, onChange, readOnly }: Props) {
  const sections = useMemo(() => buildFlowSections(flow, fields), [flow, fields]);
  const allFields = useMemo(() => flattenSections(sections), [sections]);
  const [activeFieldId, setActiveFieldId] = useState<string | null>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        for (const e of entries) {
          if (e.isIntersecting) {
            const id = e.target.id.replace(/^field-/, '');
            setActiveFieldId(id);
            break;
          }
        }
      },
      { rootMargin: '-20% 0px -60% 0px', threshold: 0 },
    );
    for (const f of allFields) {
      const el = document.getElementById(`field-${f.field_id}`);
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, [allFields]);

  const scrollToField = (fieldId: string) => {
    document.getElementById(`field-${fieldId}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const scrollToSection = (sectionId: string) => {
    document.getElementById(`section-${sectionId}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  if (allFields.length === 0) {
    return (
      <EmptyState
        title="Нет текстовых полей"
        description="В конфиге проекта нет полей text_input или datetime для отображения."
      />
    );
  }

  return (
    <div className="flex flex-col lg:flex-row gap-6 max-w-6xl">
      <nav className="lg:w-52 flex-shrink-0 hidden lg:block">
        <p className="text-[10px] uppercase tracking-wider text-gray-500 mb-2 px-2">Формы</p>
        <ul className="space-y-3 sticky top-4 max-h-[calc(100vh-12rem)] overflow-y-auto">
          {sections.map(section => (
            <li key={section.id}>
              <button
                type="button"
                onClick={() => scrollToSection(section.id)}
                className="w-full text-left px-2 py-1 text-xs font-medium text-gray-400 hover:text-gray-200 truncate"
              >
                {section.title}
              </button>
              <ul className="mt-0.5 space-y-0.5 pl-2 border-l border-gray-800">
                {section.fields.map(f => (
                  <li key={f.field_id}>
                    <button
                      type="button"
                      onClick={() => scrollToField(f.field_id)}
                      className={`w-full text-left px-2 py-1 text-[11px] rounded-md truncate transition-colors ${
                        activeFieldId === f.field_id
                          ? 'bg-blue-600/20 text-blue-300'
                          : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800/50'
                      }`}
                    >
                      {fieldLabel(f)}
                    </button>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </nav>

      <div className="flex-1 min-w-0 space-y-8">
        {sections.map(section => (
          <section key={section.id} id={`section-${section.id}`} className="scroll-mt-24">
            <h3 className="text-sm font-semibold text-gray-200 mb-4 pb-2 border-b border-[var(--color-border)]">
              {section.title}
            </h3>
            <div className="space-y-4">
              {section.fields.map(field => (
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
          </section>
        ))}
      </div>
    </div>
  );
}
