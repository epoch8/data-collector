import { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { api } from '@/api/client';
import type { PackageSession } from '@/types/manifest';
import type { ProjectConfig, ProjectSummary } from '@/types/config';
import { PageHeader } from '@/components/ui/PageHeader';
import { PhaseBadge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { TableSkeleton } from '@/components/ui/Spinner';
import { phaseLabel } from '@/lib/phase-labels';
import { formatDateTime, formatRelativeTime, shortPackageId } from '@/lib/format';
import { searchableConfigFields, formatFieldValueForSearch } from '@/lib/form-fields';
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
  const [search, setSearch] = useState('');

  const searchableFields = useMemo(
    () => searchableConfigFields(projectConfig?.config?.fields ?? []),
    [projectConfig],
  );

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
        const fields = searchableConfigFields(config.config?.fields ?? []);
        const savedField = localStorage.getItem(`${SEARCH_FIELD_KEY}:${projectId}`);
        const initialField =
          savedField && fields.some(f => f.field_id === savedField)
            ? savedField
            : fields[0]?.field_id ?? '';
        setSearchFieldId(initialField);
        if (fields.length > 0) setSearchMode('field');
      },
    );
  }, [projectId]);

  useEffect(() => {
    if (projectId && searchFieldId) {
      localStorage.setItem(`${SEARCH_FIELD_KEY}:${projectId}`, searchFieldId);
    }
  }, [projectId, searchFieldId]);

  const phases = useMemo(() => {
    const set = new Set(packages.map(p => p.phase));
    return ['all', 'completed', ...Array.from(set).filter(p => p !== 'completed')];
  }, [packages]);

  const selectedField = searchableFields.find(f => f.field_id === searchFieldId);

  const filtered = useMemo(() => {
    let list = phaseFilter === 'all' ? packages : packages.filter(p => p.phase === phaseFilter);
    const q = search.trim().toLowerCase();
    if (!q) return list;

    if (searchMode === 'field' && searchFieldId) {
      list = list.filter(p => {
        const raw = p.data_fields?.[searchFieldId];
        return formatFieldValueForSearch(raw).includes(q);
      });
    } else {
      list = list.filter(
        p =>
          p.package_id.toLowerCase().includes(q) ||
          (p.uploader_email ?? '').toLowerCase().includes(q),
      );
    }
    return list;
  }, [packages, phaseFilter, search, searchMode, searchFieldId]);

  const loading = loadingProjects || loadingPackages;

  const showFieldColumn = searchMode === 'field' && !!selectedField;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <PageHeader
        title="Пакеты"
        subtitle="Просмотр и правка принятых пакетов data-collector"
      />

      <div className="flex flex-wrap items-center gap-3 mb-4">
        {projects.length > 0 && (
          <select
            value={projectId}
            onChange={e => setProjectId(e.target.value)}
            className="ui-input w-auto min-w-[200px] py-1.5"
          >
            {projects.map(p => (
              <option key={p.project_id} value={p.project_id}>
                {p.name}
              </option>
            ))}
          </select>
        )}

        <div className="flex rounded-md border border-[var(--color-border)] overflow-hidden text-xs">
          <button
            type="button"
            onClick={() => setSearchMode('field')}
            disabled={searchableFields.length === 0}
            className={`px-3 py-1.5 transition-colors ${
              searchMode === 'field'
                ? 'bg-blue-600/30 text-blue-200'
                : 'bg-gray-800/50 text-gray-400 hover:text-gray-300 disabled:opacity-40'
            }`}
          >
            По полю
          </button>
          <button
            type="button"
            onClick={() => setSearchMode('meta')}
            className={`px-3 py-1.5 transition-colors border-l border-[var(--color-border)] ${
              searchMode === 'meta'
                ? 'bg-blue-600/30 text-blue-200'
                : 'bg-gray-800/50 text-gray-400 hover:text-gray-300'
            }`}
          >
            ID / email
          </button>
        </div>

        {searchMode === 'field' && searchableFields.length > 0 && (
          <select
            value={searchFieldId}
            onChange={e => setSearchFieldId(e.target.value)}
            className="ui-input w-auto min-w-[160px] py-1.5"
            title="Поле из config.fields"
          >
            {searchableFields.map(f => (
              <option key={f.field_id} value={f.field_id}>
                {fieldLabel(f)}
              </option>
            ))}
          </select>
        )}

        <input
          type="search"
          placeholder={
            searchMode === 'field' && selectedField
              ? `Значение «${fieldLabel(selectedField)}»…`
              : 'Package ID или email…'
          }
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="ui-input w-auto flex-1 min-w-[180px] max-w-sm py-1.5"
        />

        <div className="flex flex-wrap gap-1.5">
          {phases.map(ph => (
            <button
              key={ph}
              type="button"
              onClick={() => setPhaseFilter(ph)}
              className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                phaseFilter === ph
                  ? 'bg-blue-600/30 text-blue-200 border-blue-500/40'
                  : 'bg-gray-800/50 text-gray-400 border-gray-700/50 hover:border-gray-600'
              }`}
            >
              {ph === 'all' ? 'Все' : phaseLabel(ph)}
            </button>
          ))}
        </div>
      </div>

      {!loading && packages.length > 0 && (
        <p className="text-xs text-gray-500 mb-3">
          Показано {filtered.length} из {packages.length}
          {searchMode === 'field' && selectedField && search.trim() && (
            <span> · поиск по «{fieldLabel(selectedField)}»</span>
          )}
        </p>
      )}

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
        <EmptyState title="Нет пакетов" description="Измените фильтр или запрос поиска." />
      ) : (
        <div className="ui-card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-800/40 text-gray-400 text-left text-xs uppercase tracking-wider">
                <th className="px-4 py-3">Package ID</th>
                {showFieldColumn && (
                  <th className="px-4 py-3">{fieldLabel(selectedField!)}</th>
                )}
                <th className="px-4 py-3">Статус</th>
                <th className="px-4 py-3">Дата</th>
                <th className="px-4 py-3">Загрузил</th>
                <th className="px-4 py-3 w-10" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/50">
              {filtered.map(pkg => (
                <tr key={pkg.package_id} className="hover:bg-gray-800/25 transition-colors">
                  <td className="px-4 py-3">
                    <Link
                      to={`/projects/${pkg.project_id}/packages/${pkg.package_id}`}
                      className="text-blue-400 hover:text-blue-300 font-mono text-xs"
                      title={pkg.package_id}
                    >
                      {shortPackageId(pkg.package_id)}
                    </Link>
                  </td>
                  {showFieldColumn && (
                    <td className="px-4 py-3 text-gray-300 font-mono text-xs max-w-[200px] truncate">
                      {formatCellValue(pkg.data_fields?.[searchFieldId])}
                    </td>
                  )}
                  <td className="px-4 py-3">
                    <PhaseBadge phase={pkg.phase} />
                  </td>
                  <td className="px-4 py-3 text-gray-400" title={formatDateTime(pkg.created_at)}>
                    {formatRelativeTime(pkg.created_at)}
                  </td>
                  <td className="px-4 py-3 text-gray-400 truncate max-w-[200px]">
                    {pkg.uploader_email || '—'}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      title="Копировать ID"
                      onClick={() => navigator.clipboard.writeText(pkg.package_id)}
                      className="text-gray-600 hover:text-gray-400 text-xs"
                    >
                      ⧉
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function formatCellValue(value: string | number | boolean | null | undefined): string {
  if (value == null || value === '') return '—';
  if (typeof value === 'string' && value.includes('T') && !Number.isNaN(Date.parse(value))) {
    return formatDateTime(value);
  }
  return String(value);
}
