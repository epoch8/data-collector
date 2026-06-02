import { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, ApiError } from '@/api/client';
import { useAuth } from '@/auth/useAuth';
import type { FieldChangeLogEntry, PackageSession, PackageWorkspace } from '@/types/manifest';
import type { ProjectConfig } from '@/types/config';
import { DataTab } from '@/components/tabs/DataTab';
import { MediaTab } from '@/components/tabs/MediaTab';
import { VisualisationTab } from '@/components/tabs/VisualisationTab';
import { ChangeHistoryTab } from '@/components/tabs/ChangeHistoryTab';
import type { WorkspaceTab } from '@/components/ui/TabBar';
import { Button } from '@/components/ui/Button';
import { WorkspaceHeader } from '@/components/workspace/WorkspaceHeader';
import { PackageSidebar } from '@/components/workspace/PackageSidebar';
import { WorkspaceSkeleton } from '@/components/ui/Spinner';
import { useToast } from '@/components/ui/Toast';
import { collectFormBlobPaths } from '@/lib/form-fields';
import { shortPackageId } from '@/lib/format';
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
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [historyEntries, setHistoryEntries] = useState<FieldChangeLogEntry[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [reasonDialogOpen, setReasonDialogOpen] = useState(false);
  const [reasonChoice, setReasonChoice] = useState<'input_error' | 'stale_data' | 'invalid_format' | 'custom'>(
    'input_error',
  );
  const [customReason, setCustomReason] = useState('');
  const pendingReasonRef = useRef<string | null>(null);
  const initialDataRef = useRef<Record<string, unknown>>({});

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
        initialDataRef.current = { ...(data.manifest.data ?? {}) };
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

  useEffect(() => {
    setSidebarOpen(false);
  }, [packageId]);

  useEffect(() => {
    if (!sidebarOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [sidebarOpen]);

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

  const loadHistory = useCallback(async () => {
    if (!projectId || !packageId) return;
    setHistoryLoading(true);
    try {
      const rows = await api.getFieldChangelog(projectId, packageId);
      setHistoryEntries(rows);
    } catch {
      setHistoryEntries([]);
    } finally {
      setHistoryLoading(false);
    }
  }, [projectId, packageId]);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  const getChanges = useCallback(() => {
    if (!ws) return [];
    const currentData = ws.manifest.data ?? {};
    const previousData = initialDataRef.current;
    const changedFieldIds = new Set<string>([...Object.keys(previousData), ...Object.keys(currentData)]);
    return Array.from(changedFieldIds)
      .filter(fieldId => JSON.stringify(previousData[fieldId]) !== JSON.stringify(currentData[fieldId]))
      .map(fieldId => ({
        field_id: fieldId,
        before: previousData[fieldId] ?? null,
        after: currentData[fieldId] ?? null,
      }));
  }, [ws]);

  const startSaveFlow = useCallback(() => {
    if (!dirty || !isEditable || !ws || !projectId || !packageId) return;
    const changes = getChanges();
    if (!changes.length) {
      setDirty(false);
      return;
    }
    pendingReasonRef.current = null;
    setCustomReason('');
    setReasonChoice('input_error');
    setReasonDialogOpen(true);
  }, [dirty, isEditable, ws, projectId, packageId, getChanges]);

  const resolveReason = useCallback(() => {
    if (reasonChoice === 'input_error') return 'ошибка в введенных данных';
    if (reasonChoice === 'stale_data') return 'устаревшие данные';
    if (reasonChoice === 'invalid_format') return 'неправильный формат данных';
    return customReason.trim();
  }, [reasonChoice, customReason]);

  const handleSave = useCallback(async () => {
    if (!ws || !projectId || !packageId || !isEditable) return;
    const changes = getChanges();
    if (!changes.length) {
      setDirty(false);
      return;
    }
    const reason = pendingReasonRef.current?.trim();
    if (!reason) {
      startSaveFlow();
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      await api.patchManifest(projectId, packageId, ws.manifest);
      await api.appendFieldChangelog({
        project_id: projectId,
        package_id: packageId,
        reason,
        verifier_email: user?.email ?? undefined,
        changes,
      });
      initialDataRef.current = { ...(ws.manifest.data ?? {}) };
      setDirty(false);
      pendingReasonRef.current = null;
      await loadHistory();
      toast.show('Изменения сохранены');
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Ошибка сохранения';
      setSaveError(msg);
      toast.show(msg, 'error');
    } finally {
      setSaving(false);
    }
  }, [ws, projectId, packageId, isEditable, toast, getChanges, startSaveFlow, user?.email, loadHistory]);

  const confirmReasonAndSave = useCallback(() => {
    const reason = resolveReason();
    if (!reason) {
      toast.show('Укажите причину изменения', 'error');
      return;
    }
    pendingReasonRef.current = reason;
    setReasonDialogOpen(false);
    void handleSave();
  }, [resolveReason, toast, handleSave]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        if (dirty && isEditable && ws && projectId && packageId) {
          startSaveFlow();
        }
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [dirty, isEditable, ws, projectId, packageId, startSaveFlow]);

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
      { id: 'change_history' as const, label: 'История изменений' },
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
          mobileOpen={sidebarOpen}
          onMobileClose={() => setSidebarOpen(false)}
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
            <div className="workspace-mobile-bar">
              <button
                type="button"
                className="workspace-mobile-bar__btn"
                onClick={() => setSidebarOpen(true)}
              >
                ☰ Пакеты
              </button>
              <span className="workspace-mobile-bar__hint">
                {shortPackageId(ws.session.package_id)}
              </span>
            </div>

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
              onSave={startSaveFlow}
            />

            <div className="workspace-content">
              <div className="workspace-inner">
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
                  <MediaTab
                    blobs={ws.blobs}
                    formBlobPaths={collectFormBlobPaths(ws.manifest.data ?? {})}
                  />
                )}
                {activeTab === 'visualisation' && (
                  <VisualisationTab
                    blobs={ws.blobs}
                    gtRecords={gtRecords}
                    inferenceRecords={inferenceRecords}
                  />
                )}
                {activeTab === 'change_history' && (
                  <ChangeHistoryTab entries={historyEntries} loading={historyLoading} />
                )}
              </div>
            </div>

            {dirty && isEditable && (
              <div className="workspace-save-bar">
                <div className="workspace-inner py-3 flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm text-amber-400/90">
                    Есть несохранённые изменения
                    <span className="hidden sm:inline text-gray-600"> · Ctrl+S</span>
                  </p>
                  <div className="flex gap-2 w-full sm:w-auto">
                    <Button variant="ghost" onClick={handleReset} className="flex-1 sm:flex-none">
                      Откатить
                    </Button>
                    <Button
                      variant="primary"
                      onClick={startSaveFlow}
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
      {reasonDialogOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="ui-card w-full max-w-xl p-5">
            <h3 className="text-lg font-semibold text-gray-100 mb-3">Причина ручной корректировки</h3>
            <div className="space-y-2 text-sm text-gray-200">
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="reason"
                  value="input_error"
                  checked={reasonChoice === 'input_error'}
                  onChange={() => setReasonChoice('input_error')}
                />
                ошибка в введенных данных
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="reason"
                  value="stale_data"
                  checked={reasonChoice === 'stale_data'}
                  onChange={() => setReasonChoice('stale_data')}
                />
                устаревшие данные
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="reason"
                  value="invalid_format"
                  checked={reasonChoice === 'invalid_format'}
                  onChange={() => setReasonChoice('invalid_format')}
                />
                неправильный формат данных
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="reason"
                  value="custom"
                  checked={reasonChoice === 'custom'}
                  onChange={() => setReasonChoice('custom')}
                />
                своя причина
              </label>
            </div>
            <textarea
              className="ui-input w-full mt-3 min-h-24"
              placeholder="Опишите причину..."
              value={customReason}
              onChange={e => setCustomReason(e.target.value)}
              disabled={reasonChoice !== 'custom'}
            />
            <div className="flex justify-end gap-2 mt-4">
              <Button
                variant="ghost"
                onClick={() => {
                  pendingReasonRef.current = null;
                  setReasonDialogOpen(false);
                }}
              >
                Отмена
              </Button>
              <Button variant="primary" onClick={confirmReasonAndSave}>
                Сохранить
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
