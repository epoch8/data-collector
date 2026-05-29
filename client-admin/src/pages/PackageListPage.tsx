import { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { api } from '@/api/client';
import type { PackageSession } from '@/types/manifest';
import type { ProjectConfig, ProjectSummary } from '@/types/config';
import { PageHeader } from '@/components/ui/PageHeader';
import { PhaseBadge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { TableSkeleton } from '@/components/ui/Spinner';
import { FilterPanel, FilterRow, SegmentedControl } from '@/components/ui/FilterPanel';
import { phaseLabel } from '@/lib/phase-labels';
import { formatDateTime, formatRelativeTime, shortPackageId } from '@/lib/format';
import { searchableConfigFields } from '@/lib/form-fields';
import {
  filterPackages,
  packagePhaseOptions,
  initialSearchFieldId,
} from '@/lib/package-list-filters';
import { fieldLabel } from '@/lib/config-field';

const STORAGE_KEY = 'client-admin:last-project-id';
const SEARCH_FIELD_KEY = 'client-admin:last-search-field';

type SearchMode = 'field' | 'meta';

export function PackageListPage() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [projectId, setProjectId] = useState('');
  const [projectConfig, setProjectConfig] = useState<ProjectConfig | null>(null);
  const [packages, setPackages] = useState<PackageSession[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [loadingPackages, setLoadingPackages] = useState(false);
  const [phaseFilter, setPhaseFilter] = useState<string>('completed');
  const [searchMode, setSearchMode] = useState<SearchMode>('field');
  const [searchFieldId, setSearchFieldId] = useState('');
  const [searchText, setSearchText] = useState('');
  const [searchDate, setSearchDate] = useState('');

  const searchableFields = useMemo(
    () => searchableConfigFields(projectConfig?.config?.fields ?? []),
    [projectConfig],
  );

  const currentProject = projects.find(p => p.project_id === projectId);

  useEffect(() => {
    api.listProjects().then(list => {
      setProjects(list);
      const saved = localStorage.getItem(STORAGE_KEY);
      const initial =
        saved && list.some(p => p.project_id === saved)
          ? saved
          : list[0]?.project_id ?? '';
      setProjectId(initial);
      setLoadingProjects(false);
    });
  }, []);

  useEffect(() => {
    if (!projectId) return;
    localStorage.setItem(STORAGE_KEY, projectId);
    setLoadingPackages(true);
    setProjectConfig(null);
    Promise.all([api.getProjectConfig(projectId), api.listPackages(projectId)]).then(
      ([config, pkgs]) => {
        setProjectConfig(config);
        setPackages(pkgs);
        setLoadingPackages(false);
        const fields = config.config?.fields ?? [];
        setSearchFieldId(initialSearchFieldId(fields, projectId));
        if (fields.length > 0) setSearchMode('field');
      },
    );
  }, [projectId]);

  useEffect(() => {
    if (projectId && searchFieldId) {
      localStorage.setItem(`${SEARCH_FIELD_KEY}:${projectId}`, searchFieldId);
    }
  }, [projectId, searchFieldId]);

  const phases = useMemo(() => packagePhaseOptions(packages), [packages]);

  const selectedField = searchableFields.find(f => f.field_id === searchFieldId);
  const isDatetimeField = selectedField?.type === 'datetime';

  useEffect(() => {
    if (isDatetimeField) {
      setSearchText('');
    } else {
      setSearchDate('');
    }
  }, [searchFieldId, isDatetimeField]);

  const filtered = useMemo(
    () =>
      filterPackages(packages, projectConfig?.config?.fields ?? [], {
        phaseFilter,
        searchMode,
        searchFieldId,
        searchText,
        searchDate,
      }),
    [
      packages,
      projectConfig,
      phaseFilter,
      searchText,
      searchDate,
      searchMode,
      searchFieldId,
    ],
  );

  const hasActiveFieldFilter =
    searchMode === 'field' &&
    searchFieldId &&
    (isDatetimeField ? !!searchDate : !!searchText.trim());

  const loading = loadingProjects || loadingPackages;
  const showFieldColumn = searchMode === 'field' && !!selectedField;

  return (
    <div className="p-4 sm:p-6 max-w-6xl mx-auto w-full">
      <PageHeader
        title="Пакеты"
        subtitle={
          currentProject
            ? `${currentProject.name} · полей для поиска: ${searchableFields.length}`
            : 'Просмотр и правка принятых пакетов'
        }
      />

      <FilterPanel
        footer={
          !loading && packages.length > 0 ? (
            <span>
              Показано <strong className="text-gray-400">{filtered.length}</strong> из{' '}
              {packages.length}
              {hasActiveFieldFilter && selectedField && (
                <>
                  {' '}
                  · фильтр: «{fieldLabel(selectedField)}»
                  {isDatetimeField && searchDate && (
                    <> = {formatDateFilterLabel(searchDate)}</>
                  )}
                </>
              )}
            </span>
          ) : undefined
        }
      >
        <FilterRow label="Проект">
          {projects.length > 0 ? (
            <select
              value={projectId}
              onChange={e => setProjectId(e.target.value)}
              className="ui-input max-w-md py-2"
            >
              {projects.map(p => (
                <option key={p.project_id} value={p.project_id}>
                  {p.name}
                </option>
              ))}
            </select>
          ) : (
            <span className="text-sm text-gray-500">Нет проектов</span>
          )}
        </FilterRow>

        <FilterRow label="Поиск">
          <SegmentedControl
            value={searchMode}
            onChange={setSearchMode}
            options={[
              { id: 'field', label: 'По полю', disabled: searchableFields.length === 0 },
              { id: 'meta', label: 'ID / email' },
            ]}
          />
          {searchMode === 'field' && searchableFields.length > 0 && (
            <select
              value={searchFieldId}
              onChange={e => setSearchFieldId(e.target.value)}
              className="ui-input w-auto min-w-[140px] max-w-[200px] py-2"
            >
              {searchableFields.map(f => (
                <option key={f.field_id} value={f.field_id}>
                  {fieldLabel(f)}
                  {f.type === 'datetime' ? ' (дата)' : ''}
                </option>
              ))}
            </select>
          )}
          {searchMode === 'field' && isDatetimeField ? (
            <div className="flex flex-wrap items-center gap-2 flex-1 min-w-[200px]">
              <input
                type="date"
                value={searchDate}
                onChange={e => setSearchDate(e.target.value)}
                className="ui-input w-auto py-2"
                aria-label={`Дата: ${fieldLabel(selectedField!)}`}
              />
              {searchDate && (
                <button
                  type="button"
                  onClick={() => setSearchDate('')}
                  className="text-xs text-gray-500 hover:text-gray-300 px-2 py-1 rounded border border-gray-700"
                >
                  Сбросить дату
                </button>
              )}
              {!searchDate && (
                <span className="text-xs text-gray-600">Выберите день — покажем пакеты за эту дату</span>
              )}
            </div>
          ) : (
            <input
              type="search"
              placeholder={
                searchMode === 'field' && selectedField
                  ? `Значение: ${fieldLabel(selectedField)}…`
                  : 'UUID или email…'
              }
              value={searchText}
              onChange={e => setSearchText(e.target.value)}
              className="ui-input flex-1 min-w-[160px] max-w-md py-2"
            />
          )}
        </FilterRow>

        <FilterRow label="Статус">
          <div className="flex flex-wrap gap-1.5">
            {phases.map(ph => (
              <button
                key={ph}
                type="button"
                onClick={() => setPhaseFilter(ph)}
                className={`ui-chip ${phaseFilter === ph ? 'ui-chip--active' : ''}`}
              >
                {ph === 'all' ? 'Все' : phaseLabel(ph)}
              </button>
            ))}
          </div>
        </FilterRow>
      </FilterPanel>

      {loading ? (
        <TableSkeleton rows={6} />
      ) : projects.length === 0 ? (
        <EmptyState
          title="Нет проектов"
          description="Запустите django_server и выполните load_projects_from_assets."
        />
      ) : searchableFields.length === 0 && searchMode === 'field' ? (
        <EmptyState
          title="Нет полей для поиска"
          description="В config.fields проекта нет text_input или datetime."
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          title="Нет пакетов"
          description={
            isDatetimeField && searchDate
              ? `Нет пакетов с «${fieldLabel(selectedField!)}» за ${formatDateFilterLabel(searchDate)}.`
              : 'Измените фильтр или запрос поиска.'
          }
        />
      ) : (
        <div className="ui-panel overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-800/50 text-gray-400 text-left text-[11px] uppercase tracking-wider">
                  <th className="px-4 py-3 font-medium">Пакет</th>
                  {showFieldColumn && (
                    <th className="px-4 py-3 font-medium">{fieldLabel(selectedField!)}</th>
                  )}
                  <th className="px-4 py-3 font-medium">Статус</th>
                  <th className="px-4 py-3 font-medium">Дата</th>
                  <th className="px-4 py-3 font-medium hidden md:table-cell">Загрузил</th>
                  <th className="w-10" />
                </tr>
              </thead>
              <tbody>
                {filtered.map((pkg, i) => (
                  <tr
                    key={pkg.package_id}
                    className={`group border-t border-gray-800/40 hover:bg-blue-950/20 transition-colors ${
                      i % 2 === 0 ? 'bg-transparent' : 'bg-gray-900/20'
                    }`}
                  >
                    <td className="px-4 py-3">
                      <Link
                        to={`/projects/${pkg.project_id}/packages/${pkg.package_id}`}
                        className="block"
                      >
                        <span className="text-blue-400 group-hover:text-blue-300 font-mono text-xs">
                          {shortPackageId(pkg.package_id)}
                        </span>
                        <span className="block text-[10px] text-gray-600 md:hidden mt-0.5 truncate max-w-[180px]">
                          {pkg.uploader_email || '—'}
                        </span>
                      </Link>
                    </td>
                    {showFieldColumn && (
                      <td className="px-4 py-3 text-gray-300 text-xs max-w-[220px]">
                        <span className="line-clamp-2" title={String(pkg.data_fields?.[searchFieldId] ?? '')}>
                          {formatCellValue(pkg.data_fields?.[searchFieldId])}
                        </span>
                      </td>
                    )}
                    <td className="px-4 py-3">
                      <PhaseBadge phase={pkg.phase} />
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs whitespace-nowrap" title={formatDateTime(pkg.created_at)}>
                      {formatRelativeTime(pkg.created_at)}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs truncate max-w-[180px] hidden md:table-cell">
                      {pkg.uploader_email || '—'}
                    </td>
                    <td className="px-2 py-3">
                      <button
                        type="button"
                        title="Копировать ID"
                        onClick={() => navigator.clipboard.writeText(pkg.package_id)}
                        className="opacity-0 group-hover:opacity-100 p-1.5 rounded hover:bg-gray-800 text-gray-500 hover:text-gray-300 text-xs transition-opacity"
                      >
                        ⧉
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function formatCellValue(value: string | number | boolean | null | undefined): string {
  if (value == null || value === '') return '—';
  if (typeof value === 'string' && !Number.isNaN(Date.parse(value)) && value.includes('T')) {
    return formatDateTime(value);
  }
  if (typeof value === 'number' && !Number.isNaN(new Date(value).getTime())) {
    return formatDateTime(new Date(value).toISOString());
  }
  return String(value);
}

function formatDateFilterLabel(ymd: string): string {
  const [y, m, d] = ymd.split('-').map(Number);
  if (!y || !m || !d) return ymd;
  return new Date(y, m - 1, d).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}
