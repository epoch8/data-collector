import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import type { PackageSession } from '@/types/manifest';
import type { ProjectConfig } from '@/types/config';
import { PhaseBadge } from '@/components/ui/Badge';
import { phaseLabel } from '@/lib/phase-labels';
import { formatRelativeTime, shortPackageId } from '@/lib/format';
import { fieldLabel } from '@/lib/config-field';
import {
  filterPackages,
  packagePhaseOptions,
  searchableConfigFields,
  type PackageSearchMode,
} from '@/lib/package-list-filters';

interface Props {
  projectId: string;
  projectName: string;
  packageId: string;
  packages: PackageSession[];
  projectConfig: ProjectConfig | null;
  loading: boolean;
  onNavigatePackage: (targetPackageId: string) => void;
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

export function PackageSidebar({
  projectId,
  projectName,
  packageId,
  packages,
  projectConfig,
  loading,
  onNavigatePackage,
  mobileOpen = false,
  onMobileClose,
}: Props) {
  const [phaseFilter, setPhaseFilter] = useState('completed');
  const [searchMode, setSearchMode] = useState<PackageSearchMode>('meta');
  const [searchFieldId, setSearchFieldId] = useState('');
  const [searchText, setSearchText] = useState('');
  const [searchDate, setSearchDate] = useState('');
  const activeRef = useRef<HTMLButtonElement>(null);

  const fields = projectConfig?.config?.fields ?? [];
  const searchableFields = useMemo(() => searchableConfigFields(fields), [fields]);

  useEffect(() => {
    if (searchableFields.length === 0) {
      setSearchMode('meta');
      return;
    }
    const key = `client-admin:last-search-field:${projectId}`;
    const saved = localStorage.getItem(key);
    const initial =
      saved && searchableFields.some(f => f.field_id === saved)
        ? saved
        : searchableFields[0]?.field_id ?? '';
    setSearchFieldId(initial);
  }, [projectId, searchableFields]);

  useEffect(() => {
    if (projectId && searchFieldId) {
      localStorage.setItem(`client-admin:last-search-field:${projectId}`, searchFieldId);
    }
  }, [projectId, searchFieldId]);

  const selectedField = searchableFields.find(f => f.field_id === searchFieldId);
  const isDatetimeField = selectedField?.type === 'datetime';

  useEffect(() => {
    if (isDatetimeField) setSearchText('');
    else setSearchDate('');
  }, [searchFieldId, isDatetimeField]);

  const phases = useMemo(() => packagePhaseOptions(packages), [packages]);

  const filtered = useMemo(
    () =>
      filterPackages(packages, fields, {
        phaseFilter,
        searchMode,
        searchFieldId,
        searchText,
        searchDate,
      }),
    [packages, fields, phaseFilter, searchMode, searchFieldId, searchText, searchDate],
  );

  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [packageId, filtered.length]);

  return (
    <>
      <button
        type="button"
        className={`package-sidebar__backdrop ${mobileOpen ? 'package-sidebar__backdrop--visible' : ''}`}
        aria-label="Закрыть список пакетов"
        tabIndex={mobileOpen ? 0 : -1}
        onClick={onMobileClose}
      />
      <aside
        className={`package-sidebar ${mobileOpen ? 'package-sidebar--open' : ''}`}
        aria-label="Список пакетов"
      >
      <div className="package-sidebar__head">
        <Link to="/packages" className="package-sidebar__back" onClick={onMobileClose}>
          ← Все пакеты
        </Link>
        <p className="package-sidebar__project" title={projectName}>
          {projectName}
        </p>
      </div>

      <div className="package-sidebar__search">
        <input
          type="search"
          value={searchText}
          onChange={e => setSearchText(e.target.value)}
          placeholder={
            searchMode === 'field' && selectedField
              ? `${fieldLabel(selectedField)}…`
              : 'ID или email…'
          }
          className="package-sidebar__input"
          disabled={searchMode === 'field' && isDatetimeField}
        />
        <div className="package-sidebar__search-row">
          <select
            value={searchMode}
            onChange={e => setSearchMode(e.target.value as PackageSearchMode)}
            className="package-sidebar__select"
            aria-label="Режим поиска"
          >
            <option value="meta">ID / email</option>
            <option value="field" disabled={searchableFields.length === 0}>
              По полю
            </option>
          </select>
          {searchMode === 'field' && searchableFields.length > 0 && (
            <select
              value={searchFieldId}
              onChange={e => setSearchFieldId(e.target.value)}
              className="package-sidebar__select package-sidebar__select--grow"
              aria-label="Поле поиска"
            >
              {searchableFields.map(f => (
                <option key={f.field_id} value={f.field_id}>
                  {fieldLabel(f)}
                </option>
              ))}
            </select>
          )}
        </div>
        {searchMode === 'field' && isDatetimeField && (
          <input
            type="date"
            value={searchDate}
            onChange={e => setSearchDate(e.target.value)}
            className="package-sidebar__input"
          />
        )}
      </div>

      <div className="package-sidebar__phases" role="group" aria-label="Статус">
        {phases.map(ph => (
          <button
            key={ph}
            type="button"
            onClick={() => setPhaseFilter(ph)}
            className={`package-sidebar__phase ${phaseFilter === ph ? 'package-sidebar__phase--on' : ''}`}
          >
            {ph === 'all' ? 'Все' : phaseLabel(ph)}
          </button>
        ))}
      </div>

      <p className="package-sidebar__count">
        {loading ? 'Загрузка…' : `${filtered.length} из ${packages.length}`}
      </p>

      <nav className="package-sidebar__list ui-scrollbar ui-scrollbar--ghost">
        {loading ? (
          <div className="package-sidebar__skeleton" aria-hidden>
            {Array.from({ length: 8 }, (_, i) => (
              <div key={i} className="package-sidebar__skeleton-row" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <p className="package-sidebar__empty">Нет пакетов по фильтру</p>
        ) : (
          filtered.map(pkg => {
            const active = pkg.package_id === packageId;
            return (
              <button
                key={pkg.package_id}
                ref={active ? activeRef : undefined}
                type="button"
                onClick={() => {
                  onNavigatePackage(pkg.package_id);
                  onMobileClose?.();
                }}
                className={`package-sidebar__item ${active ? 'package-sidebar__item--active' : ''}`}
              >
                <div className="package-sidebar__item-top">
                  <span className="package-sidebar__item-id">{shortPackageId(pkg.package_id)}</span>
                  <PhaseBadge phase={pkg.phase} />
                </div>
                <span className="package-sidebar__item-meta">
                  {formatRelativeTime(pkg.created_at)}
                  {pkg.uploader_email ? ` · ${pkg.uploader_email}` : ''}
                </span>
              </button>
            );
          })
        )}
      </nav>
    </aside>
    </>
  );
}
