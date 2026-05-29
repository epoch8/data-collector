import { useState } from 'react';
import type { BlobInfo } from '@/types/manifest';
import { AuthenticatedImage } from '@/components/AuthenticatedImage';
import { downloadAuthenticatedFile } from '@/lib/authenticated-media';
import { formatBytes, blobFileName } from '@/lib/format';
import { Tag } from '@/components/ui/Badge';
import { Lightbox, type LightboxSlide } from '@/components/ui/Lightbox';
import { EmptyState } from '@/components/ui/EmptyState';

interface Props {
  blobs: BlobInfo[];
  formBlobPaths?: Set<string>;
}

export function MediaTab({ blobs, formBlobPaths }: Props) {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  if (blobs.length === 0) {
    return (
      <EmptyState
        title="Нет медиа-файлов"
        description="В пакете пока нет загруженных blobs."
      />
    );
  }

  const slides: LightboxSlide[] = blobs.map(b => ({
    src: b.preview_url,
    title: b.logical_path,
    subtitle: formatBytes(b.size_bytes),
  }));

  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-2 mb-5">
        <h3 className="text-base font-semibold text-gray-100">Медиа</h3>
        <p className="text-xs text-gray-500">
          {blobs.length} файл(ов) · снимки с формы отмечены
        </p>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-3 sm:gap-4">
        {blobs.map((blob, idx) => {
          const inForm = formBlobPaths?.has(blob.logical_path);
          return (
            <article
              key={blob.logical_path}
              className="ui-card ui-card--media overflow-hidden group"
            >
              <button
                type="button"
                onClick={() => setLightboxIndex(idx)}
                className="w-full aspect-[4/3] bg-gray-900 relative block"
              >
                <AuthenticatedImage
                  src={blob.preview_url}
                  alt={blob.logical_path}
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
                <span className="absolute inset-0 flex items-center justify-center bg-black/0 group-hover:bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity text-xs text-white font-medium">
                  Открыть
                </span>
              </button>
              <div className="p-2.5 border-t border-emerald-900/30">
                <div className="flex items-center gap-1 flex-wrap mb-1">
                  {inForm && <Tag className="bg-emerald-950/60 text-emerald-400">в форме</Tag>}
                </div>
                <p className="text-[11px] text-gray-400 font-mono truncate" title={blob.logical_path}>
                  {blobFileName(blob.logical_path)}
                </p>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-[10px] text-gray-600">{formatBytes(blob.size_bytes)}</span>
                  <button
                    type="button"
                    onClick={e => {
                      e.stopPropagation();
                      void downloadAuthenticatedFile(blob.preview_url, blobFileName(blob.logical_path));
                    }}
                    className="text-[10px] text-emerald-400/90 hover:text-emerald-300"
                  >
                    скачать
                  </button>
                </div>
              </div>
            </article>
          );
        })}
      </div>

      {lightboxIndex != null && (
        <Lightbox
          slides={slides}
          index={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
          onIndexChange={setLightboxIndex}
        />
      )}
    </div>
  );
}
