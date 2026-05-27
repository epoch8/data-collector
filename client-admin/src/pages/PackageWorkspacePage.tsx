import { useEffect, useState, useCallback } from 'react';

import { useParams, useNavigate } from 'react-router-dom';

import { api, ApiError } from '@/api/client';

import type { PackageWorkspace } from '@/types/manifest';

import { DataTab } from '@/components/tabs/DataTab';

import { MediaTab } from '@/components/tabs/MediaTab';



type TabId = 'data' | 'media';



const TABS: { id: TabId; label: string }[] = [

  { id: 'data', label: 'Data' },

  { id: 'media', label: 'Media' },

];



export function PackageWorkspacePage() {

  const { projectId, packageId } = useParams<{ projectId: string; packageId: string }>();

  const navigate = useNavigate();

  const [ws, setWs] = useState<PackageWorkspace | null>(null);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<TabId>('data');

  const [dirty, setDirty] = useState(false);

  const [saving, setSaving] = useState(false);

  const [saveError, setSaveError] = useState<string | null>(null);



  const loadWorkspace = useCallback(() => {

    if (!projectId || !packageId) return;

    setLoading(true);

    setError(null);

    api.getWorkspace(projectId, packageId)

      .then(data => {

        setWs(data);

        setLoading(false);

      })

      .catch(err => {

        setLoading(false);

        if (err instanceof ApiError) {

          setError(err.message);

        } else {

          setError('Не удалось загрузить пакет');

        }

      });

  }, [projectId, packageId]);



  useEffect(() => {

    loadWorkspace();

  }, [loadWorkspace]);



  const isEditable = ws?.session.phase === 'completed';



  const handleDataChange = useCallback((fieldId: string, value: unknown) => {

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

  }, [isEditable]);



  const handleSave = useCallback(async () => {

    if (!ws || !projectId || !packageId || !isEditable) return;

    setSaving(true);

    setSaveError(null);

    try {

      await api.patchManifest(projectId, packageId, ws.manifest);

      setDirty(false);

    } catch (err) {

      setSaveError(err instanceof ApiError ? err.message : 'Ошибка сохранения');

    } finally {

      setSaving(false);

    }

  }, [ws, projectId, packageId, isEditable]);



  const handleReset = useCallback(() => {

    if (!projectId || !packageId) return;

    setDirty(false);

    setSaveError(null);

    loadWorkspace();

  }, [projectId, packageId, loadWorkspace]);



  if (loading) {

    return <div className="p-6 text-gray-500 text-sm">Загрузка пакета...</div>;

  }



  if (error || !ws) {

    return (

      <div className="p-6">

        <button

          onClick={() => navigate('/packages')}

          className="text-gray-500 hover:text-gray-300 text-sm mb-4"

        >

          &larr; Пакеты

        </button>

        <div className="text-red-400 text-sm">{error ?? 'Пакет не найден'}</div>

      </div>

    );

  }



  const { session, manifest, blobs, project_config } = ws;

  const fields = project_config.config?.fields ?? [];



  return (

    <div className="flex flex-col h-full">

      <header className="flex-shrink-0 px-6 py-4 border-b border-gray-800 bg-[#13151d]/80 backdrop-blur">

        <div className="flex items-center justify-between">

          <div className="flex items-center gap-4">

            <button

              onClick={() => navigate('/packages')}

              className="text-gray-500 hover:text-gray-300 text-sm"

            >

              &larr; Пакеты

            </button>

            <div>

              <h2 className="text-base font-semibold text-gray-100 font-mono">

                {session.package_id.slice(0, 8)}…

              </h2>

              <div className="flex items-center gap-3 text-xs text-gray-500 mt-0.5">

                <span>{project_config.name}</span>

                <span className="text-gray-700">|</span>

                <span>{session.phase}</span>

                <span className="text-gray-700">|</span>

                <span>{session.uploader_email || '—'}</span>

                <span className="text-gray-700">|</span>

                <span>{new Date(session.created_at).toLocaleString('ru-RU')}</span>

              </div>

            </div>

          </div>

          <div className="flex gap-2">

            <button

              onClick={handleReset}

              disabled={!dirty}

              className="px-3 py-1.5 text-xs rounded-md border border-gray-700 text-gray-400 hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"

            >

              Откатить

            </button>

            <button

              onClick={handleSave}

              disabled={!dirty || saving || !isEditable}

              className="px-4 py-1.5 text-xs rounded-md bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"

            >

              {saving ? 'Сохранение...' : 'Сохранить'}

            </button>

          </div>

        </div>

        {!isEditable && (

          <div className="mt-3 text-xs text-amber-500/90 bg-amber-950/20 border border-amber-800/40 rounded-md px-3 py-2">

            Только просмотр: правки доступны для пакетов в статусе completed.

          </div>

        )}

        {saveError && (

          <div className="mt-3 text-xs text-red-400 bg-red-950/20 border border-red-800/40 rounded-md px-3 py-2">

            {saveError}

          </div>

        )}

      </header>



      <div className="flex-shrink-0 px-6 pt-3 border-b border-gray-800 flex gap-1">

        {TABS.map(tab => (

          <button

            key={tab.id}

            onClick={() => setActiveTab(tab.id)}

            className={`px-4 py-2 text-sm rounded-t-md transition-colors ${

              activeTab === tab.id

                ? 'bg-gray-800/60 text-gray-100 border-b-2 border-blue-500'

                : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800/30'

            }`}

          >

            {tab.label}

          </button>

        ))}

      </div>



      <div className="flex-1 overflow-auto p-6">

        {activeTab === 'data' && (

          <DataTab

            fields={fields}

            data={manifest.data ?? {}}

            blobs={blobs}

            onChange={handleDataChange}

            readOnly={!isEditable}

          />

        )}

        {activeTab === 'media' && <MediaTab blobs={blobs} />}

      </div>

    </div>

  );

}

