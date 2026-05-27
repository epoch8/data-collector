import type { ConfigField } from '@/types/config';

export function fieldLabel(field: ConfigField): string {
  return field.title;
}

export function fieldRequired(field: ConfigField): boolean {
  return field.validation?.required ?? false;
}

export function fieldHint(field: ConfigField): string | undefined {
  return field.instructions || undefined;
}

/** Admin UI order follows config.fields array (flow is mobile-only). */
export function sortFields(fields: ConfigField[]): ConfigField[] {
  return [...fields];
}
