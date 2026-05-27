import type { ConfigField, Flow } from '@/types/config';

export interface FormShot {
  path: string;
  metadata: Record<string, unknown> | null;
}

/** Поля, которые показываем на вкладке «Данные» (без instruction и camera_photo). */
export function isDataTabField(field: ConfigField): boolean {
  return field.type === 'text_input' || field.type === 'datetime';
}

export interface FlowFormSection {
  id: string;
  title: string;
  fields: ConfigField[];
}

/**
 * Секции по шагам scroll_form из config.flow.
 * Заголовок — form_title шага, иначе id шага.
 */
export function buildFlowSections(flow: Flow | undefined, fields: ConfigField[]): FlowFormSection[] {
  const byId = new Map(fields.map(f => [f.field_id, f]));
  const used = new Set<string>();
  const sections: FlowFormSection[] = [];

  for (const step of flow?.steps ?? []) {
    if (step.screen !== 'scroll_form' || !step.field_ids?.length) continue;

    const stepFields: ConfigField[] = [];
    for (const fid of step.field_ids) {
      const f = byId.get(fid);
      if (!f || !isDataTabField(f)) continue;
      stepFields.push(f);
      used.add(fid);
    }
    if (stepFields.length === 0) continue;

    sections.push({
      id: step.id ?? step.field_ids.join('-'),
      title: (step.form_title ?? '').trim() || step.id || 'Форма',
      fields: stepFields,
    });
  }

  const orphan = fields.filter(f => isDataTabField(f) && !used.has(f.field_id));
  if (orphan.length > 0) {
    sections.push({ id: '_other', title: 'Прочее', fields: orphan });
  }

  if (sections.length === 0) {
    const all = fields.filter(isDataTabField);
    if (all.length > 0) {
      sections.push({ id: '_all', title: 'Данные', fields: all });
    }
  }

  return sections;
}

export function flattenSections(sections: FlowFormSection[]): ConfigField[] {
  return sections.flatMap(s => s.fields);
}

/** Поля для поиска в списке пакетов (из config.fields JSON). */
export function searchableConfigFields(fields: ConfigField[]): ConfigField[] {
  return fields.filter(isDataTabField);
}

export function formatFieldValueForSearch(value: unknown): string {
  if (value == null) return '';
  return String(value).toLowerCase();
}

/** ISO или epoch из manifest.data. */
export function parseManifestDatetime(value: unknown): Date | null {
  if (value == null || value === '') return null;
  if (typeof value === 'number') {
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? null : d;
  }
  if (typeof value === 'string') {
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? null : d;
  }
  return null;
}

/** YYYY-MM-DD в локальной таймзоне браузера. */
export function localDateKeyFromManifestValue(value: unknown): string | null {
  const d = parseManifestDatetime(value);
  if (!d) return null;
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/** Совпадение календарного дня с выбранной датой (input type=date). */
export function matchesDatetimeDayFilter(value: unknown, filterYmd: string): boolean {
  if (!filterYmd) return true;
  const key = localDateKeyFromManifestValue(value);
  return key === filterYmd;
}

/** Shots collected for a camera_photo field — only paths under manifest.data[field_id]. */
export function extractFormShots(value: unknown): FormShot[] {
  if (value == null || typeof value !== 'object') return [];
  return Object.entries(value as Record<string, unknown>)
    .filter(([key]) => key.startsWith('blobs/'))
    .map(([path, meta]) => ({
      path,
      metadata: meta && typeof meta === 'object' ? (meta as Record<string, unknown>) : null,
    }));
}

/** All blob paths referenced anywhere in manifest.data (for QA badges on Media tab). */
export function collectFormBlobPaths(data: Record<string, unknown>): Set<string> {
  const out = new Set<string>();
  const walk = (obj: unknown) => {
    if (typeof obj === 'string' && obj.startsWith('blobs/')) {
      out.add(obj.replace(/\\/g, '/'));
    } else if (Array.isArray(obj)) {
      obj.forEach(walk);
    } else if (obj && typeof obj === 'object') {
      for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
        const key = k.replace(/\\/g, '/');
        if (key.startsWith('blobs/')) out.add(key);
        walk(v);
      }
    }
  };
  walk(data);
  return out;
}
