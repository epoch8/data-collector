import { useEffect, useState } from 'react';

import { Link } from 'react-router-dom';

import { api } from '@/api/client';

import type { PackageSession } from '@/types/manifest';

import type { ProjectSummary } from '@/types/config';



export function PackageListPage() {

  const [projects, setProjects] = useState<ProjectSummary[]>([]);

  const [projectId, setProjectId] = useState<string>('');

  const [packages, setPackages] = useState<PackageSession[]>([]);

  const [loading, setLoading] = useState(true);

  const [phaseFilter, setPhaseFilter] = useState<string>('all');



  useEffect(() => {

    api.listProjects().then(list => {

      setProjects(list);

      if (list.length > 0) {

        setProjectId(list[0].project_id);

      }

      setLoading(false);

    });

  }, []);



  useEffect(() => {

    if (!projectId) return;

    setLoading(true);

    api.listPackages(projectId).then(pkgs => {

      setPackages(pkgs);

      setLoading(false);

    });

  }, [projectId]);



  const filtered = phaseFilter === 'all'

    ? packages

    : packages.filter(p => p.phase === phaseFilter);



  const phases = ['all', ...new Set(packages.map(p => p.phase))];



  return (

    <div className="p-6 max-w-5xl">

      <h2 className="text-xl font-semibold text-gray-100 mb-1">Пакеты</h2>

      <p className="text-sm text-gray-500 mb-5">Просмотр принятых пакетов data-collector</p>



      <div className="flex flex-wrap items-center gap-3 mb-4">

        {projects.length > 0 && (

          <select

            value={projectId}

            onChange={e => setProjectId(e.target.value)}

            className="bg-gray-800 border border-gray-700 rounded-md px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500/60"

          >

            {projects.map(p => (

              <option key={p.project_id} value={p.project_id}>

                {p.name} ({p.project_id})

              </option>

            ))}

          </select>

        )}

        <div className="flex gap-2">

          {phases.map(ph => (

            <button

              key={ph}

              onClick={() => setPhaseFilter(ph)}

              className={`px-3 py-1 text-xs rounded-full transition-colors ${

                phaseFilter === ph

                  ? 'bg-blue-600 text-white'

                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'

              }`}

            >

              {ph === 'all' ? 'Все' : ph}

            </button>

          ))}

        </div>

      </div>



      {loading ? (

        <div className="text-gray-500 text-sm py-8">Загрузка...</div>

      ) : projects.length === 0 ? (

        <div className="text-gray-500 text-sm py-8">Нет проектов в django_server</div>

      ) : filtered.length === 0 ? (

        <div className="text-gray-500 text-sm py-8">Нет пакетов</div>

      ) : (

        <div className="border border-gray-800 rounded-lg overflow-hidden">

          <table className="w-full text-sm">

            <thead>

              <tr className="bg-gray-800/50 text-gray-400 text-left text-xs uppercase tracking-wider">

                <th className="px-4 py-3">Package ID</th>

                <th className="px-4 py-3">Phase</th>

                <th className="px-4 py-3">Дата</th>

                <th className="px-4 py-3">Загрузил</th>

              </tr>

            </thead>

            <tbody className="divide-y divide-gray-800/60">

              {filtered.map(pkg => (

                <tr key={pkg.package_id} className="hover:bg-gray-800/30 transition-colors">

                  <td className="px-4 py-3">

                    <Link

                      to={`/projects/${pkg.project_id}/packages/${pkg.package_id}`}

                      className="text-blue-400 hover:text-blue-300 font-mono text-xs"

                    >

                      {pkg.package_id.slice(0, 8)}…

                    </Link>

                  </td>

                  <td className="px-4 py-3">

                    <PhaseBadge phase={pkg.phase} />

                  </td>

                  <td className="px-4 py-3 text-gray-400">

                    {new Date(pkg.created_at).toLocaleString('ru-RU')}

                  </td>

                  <td className="px-4 py-3 text-gray-400">{pkg.uploader_email || '—'}</td>

                </tr>

              ))}

            </tbody>

          </table>

        </div>

      )}

    </div>

  );

}



function PhaseBadge({ phase }: { phase: string }) {

  const colors: Record<string, string> = {

    completed: 'bg-green-900/40 text-green-400 border-green-700/50',

    uploading: 'bg-yellow-900/40 text-yellow-400 border-yellow-700/50',

    awaiting_blobs: 'bg-yellow-900/40 text-yellow-400 border-yellow-700/50',

    ready_to_commit: 'bg-blue-900/40 text-blue-400 border-blue-700/50',

    failed: 'bg-red-900/40 text-red-400 border-red-700/50',

  };

  return (

    <span className={`text-xs px-2 py-0.5 rounded border ${colors[phase] ?? 'bg-gray-800 text-gray-400 border-gray-700'}`}>

      {phase}

    </span>

  );

}

