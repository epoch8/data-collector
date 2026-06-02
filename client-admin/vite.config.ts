import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'node:path';
import fs from 'node:fs';
import { promises as fsp } from 'node:fs';
import type { IncomingMessage, ServerResponse } from 'node:http';

type ChangeRecord = {
  project_id: string;
  package_id: string;
  field_id: string;
  before: unknown;
  after: unknown;
  reason: string;
  verifier_email?: string;
  changed_at: string;
};

const changelogPath = path.resolve(__dirname, '../datapipe_test/field_changelog.json');

function sendJson(res: ServerResponse, status: number, payload: unknown) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.end(JSON.stringify(payload));
}

async function readJsonBody(req: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  const raw = Buffer.concat(chunks).toString('utf-8').trim();
  if (!raw) return null;
  return JSON.parse(raw);
}

async function readChangelog(): Promise<ChangeRecord[]> {
  if (!fs.existsSync(changelogPath)) return [];
  const raw = await fsp.readFile(changelogPath, 'utf-8');
  if (!raw.trim()) return [];
  const parsed = JSON.parse(raw);
  return Array.isArray(parsed) ? (parsed as ChangeRecord[]) : [];
}

async function writeChangelog(records: ChangeRecord[]) {
  await fsp.mkdir(path.dirname(changelogPath), { recursive: true });
  await fsp.writeFile(changelogPath, JSON.stringify(records, null, 2), 'utf-8');
}

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    {
      name: 'local-field-changelog-api',
      configureServer(server) {
        server.middlewares.use(async (req, res, next) => {
          const reqUrl = req.url ? new URL(req.url, 'http://localhost') : null;
          if (!reqUrl || reqUrl.pathname !== '/local-api/field-changelog') {
            next();
            return;
          }

          try {
            if (req.method === 'GET') {
              const packageId = reqUrl.searchParams.get('package_id')?.trim();
              const projectId = reqUrl.searchParams.get('project_id')?.trim();
              const all = await readChangelog();
              const filtered = all.filter(item => {
                if (packageId && item.package_id !== packageId) return false;
                if (projectId && item.project_id !== projectId) return false;
                return true;
              });
              sendJson(res, 200, { entries: filtered });
              return;
            }

            if (req.method === 'POST') {
              const body = (await readJsonBody(req)) as {
                reason?: string;
                project_id?: string;
                package_id?: string;
                verifier_email?: string;
                changes?: Array<{ field_id?: string; before?: unknown; after?: unknown }>;
              } | null;
              const reason = body?.reason?.trim();
              const projectId = body?.project_id?.trim();
              const packageId = body?.package_id?.trim();
              if (!reason || !projectId || !packageId || !Array.isArray(body?.changes) || !body?.changes.length) {
                sendJson(res, 400, { error: 'invalid_payload' });
                return;
              }
              const now = new Date().toISOString();
              const normalized: ChangeRecord[] = body.changes
                .filter(change => typeof change.field_id === 'string' && change.field_id.trim().length > 0)
                .map(change => ({
                  project_id: projectId,
                  package_id: packageId,
                  field_id: (change.field_id as string).trim(),
                  before: change.before ?? null,
                  after: change.after ?? null,
                  reason,
                  verifier_email: body.verifier_email?.trim() || '',
                  changed_at: now,
                }));
              if (!normalized.length) {
                sendJson(res, 400, { error: 'no_valid_changes' });
                return;
              }
              const all = await readChangelog();
              all.push(...normalized);
              await writeChangelog(all);
              sendJson(res, 200, { ok: true, entries_count: normalized.length });
              return;
            }

            sendJson(res, 405, { error: 'method_not_allowed' });
          } catch (err) {
            sendJson(res, 500, { error: 'local_changelog_failed', message: String(err) });
          }
        });
      },
    },
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/admin-api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
