import type { PackageSession, PackageWorkspace, Manifest } from '@/types/manifest';
import type { ProjectConfig, ProjectSummary } from '@/types/config';
import { fetchWithAuth } from '@/lib/authenticated-media';
import { MOCK_PACKAGES, MOCK_WORKSPACE, MOCK_PROJECTS } from './mock-data';

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

const delay = (ms: number) => new Promise(r => setTimeout(r, ms));

class ApiError extends Error {
  code: string;
  status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetchWithAuth(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });
  if (!res.ok) {
    let code = 'request_failed';
    let message = res.statusText;
    try {
      const body = await res.json();
      if (body?.error?.code) code = body.error.code;
      if (body?.error?.message) message = body.error.message;
    } catch {
      // ignore parse errors
    }
    throw new ApiError(code, message, res.status);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  async listProjects(): Promise<ProjectSummary[]> {
    if (USE_MOCK) {
      await delay(200);
      return MOCK_PROJECTS;
    }
    const data = await fetchJson<{ projects: ProjectSummary[] }>('/admin-api/v1/projects');
    return data.projects;
  },

  async getProjectConfig(projectId: string): Promise<ProjectConfig> {
    if (USE_MOCK) {
      await delay(150);
      return structuredClone(MOCK_WORKSPACE.project_config);
    }
    return fetchJson<ProjectConfig>(`/admin-api/v1/projects/${projectId}/config`);
  },

  async listPackages(projectId: string, phase?: string): Promise<PackageSession[]> {
    if (USE_MOCK) {
      await delay(300);
      const pkgs = MOCK_PACKAGES.filter(p => p.project_id === projectId);
      if (!phase) return pkgs;
      return pkgs.filter(p => p.phase === phase);
    }
    const qs = phase ? `?phase=${encodeURIComponent(phase)}` : '';
    return fetchJson<PackageSession[]>(`/admin-api/v1/projects/${projectId}/packages${qs}`);
  },

  async getWorkspace(projectId: string, packageId: string): Promise<PackageWorkspace> {
    if (USE_MOCK) {
      await delay(400);
      if (packageId === MOCK_WORKSPACE.session.package_id) {
        return structuredClone(MOCK_WORKSPACE);
      }
      const session = MOCK_PACKAGES.find(p => p.package_id === packageId);
      if (!session) throw new Error(`Package ${packageId} not found`);
      return {
        ...structuredClone(MOCK_WORKSPACE),
        session,
        manifest: { ...structuredClone(MOCK_WORKSPACE.manifest), package_id: packageId },
      };
    }
    return fetchJson<PackageWorkspace>(
      `/admin-api/v1/projects/${projectId}/packages/${packageId}/workspace`,
    );
  },

  async patchManifest(projectId: string, packageId: string, manifest: Manifest): Promise<{ ok: boolean }> {
    if (USE_MOCK) {
      await delay(500);
      console.log('[mock] PATCH manifest', manifest);
      return { ok: true };
    }
    return fetchJson<{ ok: boolean }>(
      `/admin-api/v1/projects/${projectId}/packages/${packageId}/manifest`,
      { method: 'PATCH', body: JSON.stringify(manifest) },
    );
  },
};

export { ApiError };
