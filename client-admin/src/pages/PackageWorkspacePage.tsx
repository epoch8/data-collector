import { useEffect, useState, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, ApiError } from '@/api/client';
import type { PackageWorkspace } from '@/types/manifest';
import { DataTab } from '@/components/tabs/DataTab';
import { MediaTab } from '@/components/tabs/MediaTab';
import { VisualisationTab } from '@/components/tabs/VisualisationTab';
import type { WorkspaceTab } from '@/components/ui/TabBar';
import { Button } from '@/components/ui/Button';
import { WorkspaceHeader } from '@/components/workspace/WorkspaceHeader';
import { WorkspaceSkeleton } from '@/components/ui/Spinner';
import { useToast } from '@/components/ui/Toast';
import { collectFormBlobPaths } from '@/lib/form-fields';
import { getCowKeypointAnnotationsForPackage } from '@/lib/datapipe-mock';
import { getCowInferenceForPackage } from '@/lib/datapipe-inference-mock';

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

  const gtRecords = useMemo(() => {
    if (!ws) return [];
    return getCowKeypointAnnotationsForPackage(ws.session.project_id, ws.session.package_id);
  }, [ws]);

  const inferenceRecords = useMemo(() => {
    if (!ws) return [];
    return getCowInferenceForPackage(ws.session.project_id, ws.session.package_id);
  }, [ws]);

  const hasVisualisation = gtRecords.length > 0 || inferenceRecords.length > 0;

  const tabs = useMemo(
    () => [
      { id: 'data' as const, label: 'Данные' },
      { id: 'media' as const, label: 'Медиа' },
      ...(hasVisualisation ? [{ id: 'visualisation' as const, label: 'Визуализация' }] : []),
    ],
    [hasVisualisation],
  );

  useEffect(() => {
    if (activeTab === 'visualisation' && !hasVisualisation) {
      setActiveTab('data');
    }
  }, [activeTab, hasVisualisation]);

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
      <WorkspaceHeader
        projectName={project_config.name}
        packageId={session.package_id}
        phase={session.phase}
        uploaderEmail={session.uploader_email}
        createdAt={session.created_at}
        dirty={dirty}
        isEditable={isEditable}
        saving={saving}
        saveError={saveError}
        readOnlyHint={!isEditable}
        tabs={tabs}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onBack={handleBack}
        onReset={handleReset}
        onSave={() => void handleSave()}
      />

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
        {activeTab === 'visualisation' && (
          <VisualisationTab
            blobs={blobs}
            gtRecords={gtRecords}
            inferenceRecords={inferenceRecords}
          />
        )}
      </div>

      {dirty && isEditable && (
        <div className="fixed bottom-0 inset-x-0 z-30 border-t border-[var(--color-border)] bg-[var(--color-surface-raised)]/95 backdrop-blur-md shadow-[0_-8px_24px_rgba(0,0,0,0.35)]">
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
