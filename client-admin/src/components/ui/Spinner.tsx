export function Spinner({ className = '' }: { className?: string }) {
  return (
    <span
      className={`inline-block w-5 h-5 border-2 border-gray-600 border-t-blue-400 rounded-full animate-spin ${className}`}
      role="status"
      aria-label="Загрузка"
    />
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="ui-card overflow-hidden animate-pulse">
      <div className="h-10 bg-gray-800/50 border-b border-gray-800" />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-12 border-b border-gray-800/60 flex gap-4 px-4 items-center">
          <div className="h-3 bg-gray-800 rounded w-24" />
          <div className="h-3 bg-gray-800 rounded w-16" />
          <div className="h-3 bg-gray-800 rounded flex-1 max-w-[120px]" />
          <div className="h-3 bg-gray-800 rounded w-32" />
        </div>
      ))}
    </div>
  );
}

export function WorkspaceSkeleton() {
  return (
    <div className="p-6 space-y-4 animate-pulse max-w-3xl">
      <div className="h-8 bg-gray-800 rounded w-1/3" />
      <div className="h-24 ui-card" />
      <div className="h-24 ui-card" />
      <div className="h-40 ui-card" />
    </div>
  );
}
