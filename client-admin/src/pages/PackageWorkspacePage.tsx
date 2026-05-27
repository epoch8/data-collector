import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, ApiError } from '@/api/client';
import type { PackageWorkspace } from '@/types/manifest';
import { DataTab } from '@/components/tabs/DataTab';
import { MediaTab } from '@/components/tabs/MediaTab';
import { TabBar, type WorkspaceTab } from '@/components/ui/TabBar';
import { Button } from '@/components/ui/Button';
import { PhaseBadge } from '@/components/ui/Badge';
import { WorkspaceSkeleton } from '@/components/ui/Spinner';
import { useToast } from '@/components/ui/Toast';
import { collectFormBlobPaths } from '@/lib/form-fields';
import { formatDateTime, shortPackageId } from '@/lib/format';

const TABS = [
  { id: 'data' as const, label: 'Данные' },
  { id: 'media' as const, label: 'Медиа' },
];

export function PackageWorkspacePage() {
  const { projectId, packageId } = useParams<{ projectId: string; packageId: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const [ws, setWs] = useState<PackageWorkspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('data');
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const loadWorkspace = useCallback(() => {
    if (!projectId || !packageId) return;
    setLoading(true);
    setError(null);
    api
      .getWorkspace(projectId, packageId)
      .then(data => {
        setWs(data);
        setLoading(false);
      })
      .catch(err => {
        setLoading(false);
        setError(err instanceof ApiError ? err.message : 'Не удалось загрузить пакет');
      });
  }, [projectId, packageId]);

  useEffect(() => {
    loadWorkspace();
  }, [loadWorkspace]);

  const isEditable = ws?.session.phase === 'completed';

  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (dirty) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', onBeforeUnload);
    return () => window.removeEventListener('beforeunload', onBeforeUnload);
  }, [dirty]);

  const handleDataChange = useCallback(
    (fieldId: string, value: unknown) => {
      if (!isEditable) return;
      setWs(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          manifest: {
            ...prev.manifest,
            data: { ...prev.manifest.data, [fieldId]: value },
          },
        };
      });
      setDirty(true);
      setSaveError(null);
    },
    [isEditable],
  );

  const handleSave = useCallback(async () => {
    if (!ws || !projectId || !packageId || !isEditable) return;
    setSaving(true);
    setSaveError(null);
    try {
      await api.patchManifest(projectId, packageId, ws.manifest);
      setDirty(false);
      toast.show('Изменения сохранены');
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Ошибка сохранения';
      setSaveError(msg);
      toast.show(msg, 'error');
    } finally {
      setSaving(false);
    }
  }, [ws, projectId, packageId, isEditable, toast]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        if (dirty && isEditable && ws && projectId && packageId) {
          void handleSave();
        }
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [dirty, isEditable, ws, projectId, packageId, handleSave]);

  const handleReset = useCallback(() => {
    if (dirty && !window.confirm('Отменить несохранённые изменения?')) return;
    setDirty(false);
    setSaveError(null);
    loadWorkspace();
  }, [dirty, loadWorkspace]);

  const handleBack = () => {
    if (dirty && !window.confirm('Есть несохранённые изменения. Уйти со страницы?')) return;
    navigate('/packages');
  };

  if (loading) {
    return <WorkspaceSkeleton />;
  }

  if (error || !ws) {
    return (
      <div className="p-6 max-w-lg">
        <button type="button" onClick={() => navigate('/packages')} className="text-sm text-gray-500 hover:text-gray-300 mb-4">
          ← Пакеты
        </button>
        <p className="text-red-400 text-sm">{error ?? 'Пакет не найден'}</p>
      </div>
    );
  }

  const { session, manifest, blobs, project_config } = ws;
  const fields = project_config.config?.fields ?? [];
  const formBlobPaths = collectFormBlobPaths(manifest.data ?? {});

  return (
    <div className={`flex flex-col min-h-full ${dirty ? 'pb-20' : ''}`}>
      <header className="sticky top-0 z-20 border-b border-[var(--color-border)] bg-[var(--color-surface-raised)]/95 backdrop-blur-md">
        <div className="px-4 sm:px-6 py-3 sm:py-4 max-w-7xl mx-auto w-full">
          <nav className="text-xs text-gray-500 mb-2 flex items-center gap-1.5 flex-wrap">
            <button type="button" onClick={handleBack} className="hover:text-gray-300">
              Пакеты
            </button>
            <span className="text-gray-700">/</span>
            <span className="text-gray-400">{project_config.name}</span>
            <span className="text-gray-700">/</span>
            <span className="font-mono text-gray-400" title={session.package_id}>
              {shortPackageId(session.package_id)}
            </span>
          </nav>

          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <h2 className="text-lg font-semibold text-gray-100 font-mono" title={session.package_id}>
                  {shortPackageId(session.package_id)}
                </h2>
                <PhaseBadge phase={session.phase} />
                {dirty && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-950/50 text-amber-400 border border-amber-700/40">
                    не сохранено
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-500 mt-1.5">
                {session.uploader_email || '—'} · {formatDateTime(session.created_at)}
              </p>
            </div>
            <div className="hidden sm:flex gap-2">
              <Button variant="ghost" onClick={handleReset} disabled={!dirty}>
                Откатить
              </Button>
              <Button
                variant="primary"
                onClick={handleSave}
                disabled={!dirty || saving || !isEditable}
                loading={saving}
              >
                Сохранить
              </Button>
            </div>
          </div>

          {!isEditable && (
            <p className="mt-3 text-xs text-amber-500/90 bg-amber-950/30 border border-amber-800/40 rounded-md px-3 py-2">
              Только просмотр: правки доступны для пакетов в статусе «Завершён».
            </p>
          )}
          {saveError && (
            <p className="mt-3 text-xs text-red-400 bg-red-950/30 border border-red-800/40 rounded-md px-3 py-2">
              {saveError}
            </p>
          )}
        </div>

        <TabBar tabs={TABS} active={activeTab} onChange={setActiveTab} />
      </header>

      <div className="flex-1 p-4 sm:p-6">
        {activeTab === 'data' && (
          <DataTab
            fields={fields}
            flow={project_config.config?.flow}
            data={manifest.data ?? {}}
            blobs={blobs}
            onChange={handleDataChange}
            readOnly={!isEditable}
          />
        )}
        {activeTab === 'media' && (
          <div className="max-w-7xl mx-auto w-full">
            <MediaTab blobs={blobs} formBlobPaths={formBlobPaths} />
          </div>
        )}
      </div>

      {dirty && isEditable && (
        <div className="fixed bottom-0 left-60 right-0 z-30 border-t border-[var(--color-border)] bg-[var(--color-surface-raised)]/95 backdrop-blur-md shadow-[0_-8px_24px_rgba(0,0,0,0.35)]">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-amber-400/90">
              Есть несохранённые изменения
              <span className="hidden sm:inline text-gray-600"> · Ctrl+S</span>
            </p>
            <div className="flex gap-2 w-full sm:w-auto">
              <Button variant="ghost" onClick={handleReset} className="flex-1 sm:flex-none">
                Откатить
              </Button>
              <Button
                variant="primary"
                onClick={handleSave}
                disabled={saving}
                loading={saving}
                className="flex-1 sm:flex-none"
              >
                Сохранить
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
