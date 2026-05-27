import type { BlobInfo } from '@/types/manifest';

interface Props {
  blobs: BlobInfo[];
}

export function MediaTab({ blobs }: Props) {
  if (blobs.length === 0) {
    return (
      <div className="text-gray-500 text-sm py-8">
        Нет медиа-файлов в пакете.
      </div>
    );
  }

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">
        Медиа ({blobs.length})
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {blobs.map(blob => (
          <div
            key={blob.logical_path}
            className="border border-gray-800 rounded-lg overflow-hidden bg-gray-900/40 hover:border-gray-700 transition-colors"
          >
            <div className="aspect-[4/3] bg-gray-800 flex items-center justify-center">
              <img
                src={blob.preview_url}
                alt={blob.logical_path}
                className="w-full h-full object-contain"
                loading="lazy"
                onError={e => {
                  (e.target as HTMLImageElement).style.display = 'none';
                }}
              />
            </div>
            <div className="p-3">
              <div className="text-xs text-gray-300 font-mono truncate" title={blob.logical_path}>
                {blob.logical_path}
              </div>
              <div className="flex items-center justify-between mt-1">
                <div className="text-[11px] text-gray-500">
                  {formatBytes(blob.size_bytes)}
                </div>
                <a
                  href={blob.preview_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[11px] text-blue-400 hover:text-blue-300"
                >
                  скачать
                </a>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
