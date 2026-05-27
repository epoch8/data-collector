import { useState } from 'react';
import type { ConfigField } from '@/types/config';
import type { BlobInfo } from '@/types/manifest';
import { fieldHint } from '@/lib/config-field';
import { extractFormShots } from '@/lib/form-fields';
import { blobFileName } from '@/lib/format';
import { FieldCard } from '@/components/ui/FieldCard';
import { Lightbox, type LightboxSlide } from '@/components/ui/Lightbox';

interface Props {
  field: ConfigField;
  value: unknown;
  blobs: BlobInfo[];
}

export function CameraPhotoWidget({ field, value, blobs }: Props) {
  const shots = extractFormShots(value);
  const blobByPath = new Map(blobs.map(b => [b.logical_path, b]));
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  const slides: LightboxSlide[] = shots.flatMap(shot => {
    const blob = blobByPath.get(shot.path);
    if (!blob) return [];
    return [{ src: blob.preview_url, title: shot.path, subtitle: field.field_id }];
  });

  const hint = fieldHint(field);

  return (
    <FieldCard field={field} variant="data">
      {hint && <p className="text-xs text-gray-500 mb-3">{hint}</p>}

      {shots.length === 0 ? (
        <p className="text-sm text-gray-500 py-2">Кадры не собраны</p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {shots.map(shot => {
            const blob = blobByPath.get(shot.path);
            const slideIdx = slides.findIndex(s => s.title === shot.path);
            return (
              <button
                key={shot.path}
                type="button"
                disabled={!blob}
                onClick={() => slideIdx >= 0 && setLightboxIndex(slideIdx)}
                className="group relative aspect-[4/3] rounded-lg overflow-hidden border border-gray-700/60 bg-gray-800/60 hover:border-blue-500/40 transition-colors text-left disabled:cursor-default"
              >
                {blob ? (
                  <img
                    src={blob.preview_url}
                    alt={shot.path}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center p-2 text-center">
                    <span className="text-gray-500 text-lg">📷</span>
                    <span className="text-[10px] text-amber-600/90 mt-1">файл не в пакете</span>
                  </div>
                )}
                <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-2">
                  <span className="text-[10px] text-gray-300 font-mono truncate block">
                    {blobFileName(shot.path)}
                  </span>
                </div>
                {blob && (
                  <span className="absolute inset-0 flex items-center justify-center bg-black/0 group-hover:bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity text-xs text-white">
                    Открыть
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}

      {lightboxIndex != null && slides.length > 0 && (
        <Lightbox
          slides={slides}
          index={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
          onIndexChange={setLightboxIndex}
        />
      )}
    </FieldCard>
  );
}
