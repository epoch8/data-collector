import type { PackageSession } from '@/types/manifest';
import type { ConfigField } from '@/types/config';
import {
  searchableConfigFields,
  formatFieldValueForSearch,
  matchesDatetimeDayFilter,
} from '@/lib/form-fields';

export type PackageSearchMode = 'field' | 'meta';

export interface PackageListFilterState {
  phaseFilter: string;
  searchMode: PackageSearchMode;
  searchFieldId: string;
  searchText: string;
  searchDate: string;
}

export function filterPackages(
  packages: PackageSession[],
  fields: ConfigField[],
  state: PackageListFilterState,
): PackageSession[] {
  const { phaseFilter, searchMode, searchFieldId, searchText, searchDate } = state;
  let list = phaseFilter === 'all' ? packages : packages.filter(p => p.phase === phaseFilter);

  const selectedField = fields.find(f => f.field_id === searchFieldId);
  const isDatetimeField = selectedField?.type === 'datetime';

  if (searchMode === 'field' && searchFieldId) {
    if (isDatetimeField) {
      if (searchDate) {
        list = list.filter(p =>
          matchesDatetimeDayFilter(p.data_fields?.[searchFieldId], searchDate),
        );
      }
    } else {
      const q = searchText.trim().toLowerCase();
      if (q) {
        list = list.filter(p => {
          const raw = p.data_fields?.[searchFieldId];
          return formatFieldValueForSearch(raw).includes(q);
        });
      }
    }
    return list;
  }

  const q = searchText.trim().toLowerCase();
  if (!q) return list;
  return list.filter(
    p =>
      p.package_id.toLowerCase().includes(q) ||
      (p.uploader_email ?? '').toLowerCase().includes(q),
  );
}

export function packagePhaseOptions(packages: PackageSession[]): string[] {
  const set = new Set(packages.map(p => p.phase));
  return ['all', 'completed', ...Array.from(set).filter(p => p !== 'completed')];
}

export function initialSearchFieldId(
  fields: ConfigField[],
  projectId: string,
): string {
  const searchable = searchableConfigFields(fields);
  const key = `client-admin:last-search-field:${projectId}`;
  const saved = localStorage.getItem(key);
  if (saved && searchable.some(f => f.field_id === saved)) return saved;
  return searchable[0]?.field_id ?? '';
}

export { searchableConfigFields };
