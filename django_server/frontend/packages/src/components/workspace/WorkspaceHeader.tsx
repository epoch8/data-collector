import type { ReactNode } from 'react';
import { PhaseBadge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { TabBar, type WorkspaceTab } from '@/components/ui/TabBar';
import { formatDateTime, shortPackageId } from '@/lib/format';

interface Tab {
  id: WorkspaceTab;
  label: string;
}

interface Props {
  projectName: string;
  packageId: string;
  phase: string;
  uploaderEmail: string;
  createdAt: string;
  dirty: boolean;
  isEditable: boolean;
  saving: boolean;
  saveError: string | null;
  readOnlyHint?: boolean;
  tabs: Tab[];
  activeTab: WorkspaceTab;
  onTabChange: (tab: WorkspaceTab) => void;
  onBack: () => void;
  onReset: () => void;
  onSave: () => void;
}

export function WorkspaceHeader({
  projectName,
  packageId,
  phase,
  uploaderEmail,
  createdAt,
  dirty,
  isEditable,
  saving,
  saveError,
  readOnlyHint,
  tabs,
  activeTab,
  onTabChange,
  onBack,
  onReset,
  onSave,
}: Props) {
  return (
    <header className="workspace-header sticky top-0 z-20">
      <div className="workspace-header__top workspace-inner">
        <nav className="workspace-header__crumb" aria-label="Навигация">
          <button type="button" onClick={onBack} className="workspace-header__crumb-link">
            Пакеты
          </button>
          <span className="workspace-header__crumb-sep" aria-hidden>
            /
          </span>
          <span className="text-gray-400 truncate max-w-[200px] sm:max-w-none">{projectName}</span>
        </nav>

        <div className="workspace-header__main">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1
                className="text-xl sm:text-2xl font-semibold text-gray-50 font-mono tracking-tight truncate"
                title={packageId}
              >
                {shortPackageId(packageId)}
              </h1>
              <PhaseBadge phase={phase} />
              {dirty && (
                <span className="workspace-header__dirty">не сохранено</span>
              )}
            </div>
            <p className="workspace-header__meta">
              <span className="truncate max-w-[140px] sm:max-w-none inline-block align-bottom">
                {uploaderEmail || '—'}
              </span>
              <span className="workspace-header__meta-dot" aria-hidden>
                ·
              </span>
              <time dateTime={createdAt}>{formatDateTime(createdAt)}</time>
            </p>
          </div>

          <div className="workspace-header__actions hidden sm:flex">
            <Button variant="ghost" onClick={onReset} disabled={!dirty} className="!px-4">
              Откатить
            </Button>
            <Button
              variant="primary"
              onClick={onSave}
              disabled={!dirty || saving || !isEditable}
              loading={saving}
              className="!px-4"
            >
              Сохранить
            </Button>
          </div>
        </div>

        {(readOnlyHint || saveError) && (
          <div className="workspace-header__alerts">
            {readOnlyHint && (
              <AlertBanner variant="warning">
                Только просмотр: правки доступны для пакетов в статусе «Завершён».
              </AlertBanner>
            )}
            {saveError && <AlertBanner variant="error">{saveError}</AlertBanner>}
          </div>
        )}
      </div>

      <TabBar tabs={tabs} active={activeTab} onChange={onTabChange} />
    </header>
  );
}

function AlertBanner({
  variant,
  children,
}: {
  variant: 'warning' | 'error';
  children: ReactNode;
}) {
  const cls =
    variant === 'warning'
      ? 'workspace-header__alert workspace-header__alert--warning'
      : 'workspace-header__alert workspace-header__alert--error';
  return <p className={cls}>{children}</p>;
}
