import type { ConfigField } from '@/types/config';
import type { BlobInfo } from '@/types/manifest';
import { fieldHint, fieldLabel, fieldRequired } from '@/lib/config-field';

interface Props {
  field: ConfigField;
  value: unknown;
  blobs: BlobInfo[];
}

export function CameraPhotoWidget({ field, value, blobs }: Props) {
  const shots = extractShots(value);
  const blobByPath = new Map(blobs.map(b => [b.logical_path, b]));

  return (
    <div className="border border-gray-800 rounded-lg p-4 bg-gray-900/30">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-sm text-gray-300 font-medium">{fieldLabel(field)}</span>
        {fieldRequired(field) && <span className="text-red-400 text-[10px]">required</span>}
        <span className="text-[10px] text-gray-600 font-mono ml-auto">{field.field_id}</span>
      </div>
      {fieldHint(field) && (
        <p className="text-xs text-gray-500 mb-3">{fieldHint(field)}</p>
      )}

      {shots.length === 0 ? (
        <div className="text-sm text-gray-500">Нет кадров</div>
      ) : (
        <div className="space-y-3">
          {shots.map(shot => {
            const blob = blobByPath.get(shot.path);
            return (
              <div
                key={shot.path}
                className="border border-gray-700/60 rounded-lg bg-gray-800/40 overflow-hidden"
              >
                <div className="aspect-[16/9] bg-gray-800 flex items-center justify-center">
                  {blob ? (
                    <img
                      src={blob.preview_url}
                      alt={shot.path}
                      className="w-full h-full object-contain"
                      loading="lazy"
                    />
                  ) : (
                    <div className="text-center px-4">
                      <div className="text-gray-500 text-2xl mb-1">📷</div>
                      <div className="text-xs text-gray-500 font-mono">{shot.path}</div>
                      <div className="text-[10px] text-amber-600/80 mt-1">blob не найден в пакете</div>
                    </div>
                  )}
                </div>
                <div className="px-3 py-2 border-t border-gray-700/40 flex items-center justify-between gap-2">
                  <div className="text-xs text-gray-500 font-mono truncate" title={shot.path}>
                    {shot.path}
                  </div>
                  {blob && (
                    <a
                      href={blob.preview_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[10px] text-blue-400 hover:text-blue-300 shrink-0"
                    >
                      открыть
                    </a>
                  )}
                </div>
                {shot.metadata && (
                  <div className="px-3 py-2 border-t border-gray-700/40">
                    <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
                      {typeof shot.metadata.collected_at === 'string' && (
                        <MetaRow label="Снято" value={new Date(shot.metadata.collected_at).toLocaleString('ru-RU')} />
                      )}
                      {isFrameCamera(shot.metadata.frame_camera) && (
                        <>
                          <MetaRow
                            label="Разрешение"
                            value={`${shot.metadata.frame_camera.image_width_px}×${shot.metadata.frame_camera.image_height_px}`}
                          />
                          <MetaRow
                            label="Focal"
                            value={`fx=${shot.metadata.frame_camera.fx_px}`}
                          />
                        </>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-400 font-mono">{value}</span>
    </div>
  );
}

interface Shot {
  path: string;
  metadata: Record<string, unknown> | null;
}

function isFrameCamera(v: unknown): v is Record<string, number> {
  return v != null && typeof v === 'object' && 'image_width_px' in (v as object);
}

function extractShots(value: unknown): Shot[] {
  if (value == null || typeof value !== 'object') return [];
  return Object.entries(value as Record<string, unknown>)
    .filter(([key]) => key.startsWith('blobs/'))
    .map(([path, meta]) => ({
      path,
      metadata: meta && typeof meta === 'object' ? meta as Record<string, unknown> : null,
    }));
}
