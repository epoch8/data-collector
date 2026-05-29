import { useEffect, useState, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, ApiError } from '@/api/client';
import { useAuth } from '@/auth/useAuth';
import type { PackageWorkspace } from '@/types/manifest';
import type { PackageSession } from '@/types/manifest';
import type { ProjectConfig } from '@/types/config';
import { DataTab } from '@/components/tabs/DataTab';
import { MediaTab } from '@/components/tabs/MediaTab';
import { VisualisationTab } from '@/components/tabs/VisualisationTab';
import type { WorkspaceTab } from '@/components/ui/TabBar';
import { Button } from '@/components/ui/Button';
import { WorkspaceHeader } from '@/components/workspace/WorkspaceHeader';
import { PackageSidebar } from '@/components/workspace/PackageSidebar';
import { WorkspaceSkeleton } from '@/components/ui/Spinner';
import { useToast } from '@/components/ui/Toast';
import { collectFormBlobPaths } from '@/lib/form-fields';
import { getCowKeypointAnnotationsForPackage } from '@/lib/datapipe-mock';
import { getCowInferenceForPackage } from '@/lib/datapipe-inference-mock';

export function PackageWorkspacePage() {
  const { projectId, packageId } = useParams<{ projectId: string; packageId: string }>();
  const { ready, user, bypass } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [ws, setWs] = useState<PackageWorkspace | null>(null);
  const [packages, setPackages] = useState<PackageSession[]>([]);
  const [projectConfig, setProjectConfig] = useState<ProjectConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [listLoading, setListLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('data');
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready || !projectId) return;
    if (!bypass && !user) return;
    setListLoading(true);
    Promise.all([api.getProjectConfig(projectId), api.listPackages(projectId)])
      .then(([config, pkgs]) => {
        setProjectConfig(config);
        setPackages(pkgs);
        setListLoading(false);
      })
      .catch(err => {
        setListLoading(false);
        if (err instanceof ApiError && err.status === 401) {
          navigate('/login', { replace: true });
        }
      });
  }, [ready, user, bypass, projectId, navigate]);

  const loadWorkspace = useCallback(() => {
    if (!ready || !projectId || !packageId) return;
    if (!bypass && !user) return;
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
        if (err instanceof ApiError && err.status === 401) {
          navigate('/login', { replace: true });
          return;
        }
        setError(err instanceof ApiError ? err.message : 'Не удалось загрузить пакет');
      });
  }, [ready, user, bypass, projectId, packageId, navigate]);

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

  const confirmLeave = useCallback(() => {
    if (!dirty) return true;
    return window.confirm('Есть несохранённые изменения. Уйти без сохранения?');
  }, [dirty]);

  const handleBack = () => {
    if (!confirmLeave()) return;
    navigate('/packages');
  };

  const handleNavigatePackage = useCallback(
    (targetId: string) => {
      if (!projectId || targetId === packageId) return;
      if (!confirmLeave()) return;
      navigate(`/projects/${projectId}/packages/${targetId}`);
    },
    [projectId, packageId, confirmLeave, navigate],
  );

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

  const projectName = projectConfig?.name ?? ws?.project_config.name ?? projectId ?? 'Проект';

  return (
    <div className={`workspace-shell ${dirty ? 'workspace-shell--dirty' : ''}`}>
      {projectId && packageId && (
        <PackageSidebar
          projectId={projectId}
          projectName={projectName}
          packageId={packageId}
          packages={packages}
          projectConfig={projectConfig}
          loading={listLoading}
          onNavigatePackage={handleNavigatePackage}
        />
      )}

      <div className="workspace-shell__main">
        {loading ? (
          <WorkspaceSkeleton />
        ) : error || !ws ? (
          <div className="p-6 max-w-lg">
            <p className="text-red-400 text-sm">{error ?? 'Пакет не найден'}</p>
          </div>
        ) : (
          <>
            <WorkspaceHeader
              projectName={projectName}
              packageId={ws.session.package_id}
              phase={ws.session.phase}
              uploaderEmail={ws.session.uploader_email}
              createdAt={ws.session.created_at}
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
                  fields={ws.project_config.config?.fields ?? []}
                  flow={ws.project_config.config?.flow}
                  data={ws.manifest.data ?? {}}
                  blobs={ws.blobs}
                  onChange={handleDataChange}
                  readOnly={!isEditable}
                />
              )}
              {activeTab === 'media' && (
                <div className="max-w-7xl mx-auto w-full">
                  <MediaTab
                    blobs={ws.blobs}
                    formBlobPaths={collectFormBlobPaths(ws.manifest.data ?? {})}
                  />
                </div>
              )}
              {activeTab === 'visualisation' && (
                <VisualisationTab
                  blobs={ws.blobs}
                  gtRecords={gtRecords}
                  inferenceRecords={inferenceRecords}
                />
              )}
            </div>

            {dirty && isEditable && (
              <div className="workspace-save-bar">
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
          </>
        )}
      </div>
    </div>
  );
}
