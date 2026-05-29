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
  const [activeSectionId, setActiveSectionId] = useState<string | null>(sections[0]?.id ?? null);
  const [activeFieldId, setActiveFieldId] = useState<string | null>(null);

  useEffect(() => {
    if (sections.length && !sections.some(s => s.id === activeSectionId)) {
      setActiveSectionId(sections[0].id);
    }
  }, [sections, activeSectionId]);

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
      { rootMargin: '-25% 0px -55% 0px', threshold: 0 },
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
    setActiveSectionId(sectionId);
    document.getElementById(`section-${sectionId}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  if (allFields.length === 0) {
    return (
      <EmptyState
        title="Нет текстовых полей"
        description="В конфиге проекта нет полей text_input или datetime."
      />
    );
  }

  return (
    <div className="flex flex-col xl:flex-row gap-5 w-full">
      {/* Мобильная: горизонтальные чипы форм */}
      <div className="xl:hidden -mx-1 overflow-x-auto pb-1">
        <div className="flex gap-2 px-1 min-w-min">
          {sections.map(section => (
            <button
              key={section.id}
              type="button"
              onClick={() => scrollToSection(section.id)}
              className={`ui-chip shrink-0 ${activeSectionId === section.id ? 'ui-chip--active' : ''}`}
            >
              {section.title}
            </button>
          ))}
        </div>
      </div>

      {/* Десктоп: боковая навигация */}
      <nav className="hidden xl:block w-56 shrink-0">
        <div className="ui-nav-rail sticky top-[7.5rem] max-h-[calc(100vh-9rem)] overflow-y-auto">
          <p className="text-xs uppercase tracking-wider text-gray-500 mb-3 px-1">Формы</p>
          <ul className="space-y-4">
            {sections.map(section => (
              <li key={section.id}>
                <button
                  type="button"
                  onClick={() => scrollToSection(section.id)}
                  className={`w-full text-left px-2 py-1.5 text-sm font-semibold truncate rounded-md transition-colors ${
                    activeSectionId === section.id
                      ? 'text-blue-300 bg-blue-600/10'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  {section.title}
                </button>
                <ul className="mt-1 space-y-0.5 pl-2 border-l-2 border-gray-800 ml-1">
                  {section.fields.map(f => (
                    <li key={f.field_id}>
                      <button
                        type="button"
                        onClick={() => scrollToField(f.field_id)}
                        className={`w-full text-left px-2 py-1 text-sm rounded-md truncate transition-colors ${
                          activeFieldId === f.field_id
                            ? 'bg-blue-600/25 text-blue-200'
                            : 'text-gray-500 hover:text-gray-300'
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
        </div>
      </nav>

      <div className="flex-1 min-w-0 space-y-10">
        {sections.map(section => (
          <section
            key={section.id}
            id={`section-${section.id}`}
            className="scroll-mt-28"
          >
            <div className="flex items-center gap-3 mb-4">
              <span className="w-1 h-6 rounded-full bg-blue-500/80" />
              <h3 className="text-lg font-semibold text-gray-100">{section.title}</h3>
              <span className="text-xs text-gray-600 tabular-nums">
                {section.fields.length} пол.
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {section.fields.map(field => (
                <div
                  key={field.field_id}
                  className={field.type === 'datetime' ? 'md:col-span-2' : ''}
                >
                  <FieldWidget
                    field={field}
                    value={data[field.field_id]}
                    onChange={v => onChange(field.field_id, v)}
                    blobs={blobs}
                    readOnly={readOnly}
                  />
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
