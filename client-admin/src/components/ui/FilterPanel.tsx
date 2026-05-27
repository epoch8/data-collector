import type { ReactNode } from 'react';

interface Props {
  children: ReactNode;
  footer?: ReactNode;
}

/** Карточка с фильтрами и поиском на странице списка. */
export function FilterPanel({ children, footer }: Props) {
  return (
    <div className="ui-panel mb-5">
      <div className="p-4 space-y-4">{children}</div>
      {footer && (
        <div className="px-4 py-2.5 border-t border-[var(--color-border)] bg-gray-900/30 text-xs text-gray-500">
          {footer}
        </div>
      )}
    </div>
  );
}

export function FilterRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
      <span className="text-[11px] font-medium uppercase tracking-wider text-gray-500 sm:w-24 shrink-0">
        {label}
      </span>
      <div className="flex flex-wrap items-center gap-2 flex-1 min-w-0">{children}</div>
    </div>
  );
}

export function SegmentedControl<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: { id: T; label: string; disabled?: boolean }[];
  onChange: (id: T) => void;
}) {
  return (
    <div className="inline-flex rounded-lg border border-[var(--color-border)] overflow-hidden bg-gray-900/50 p-0.5">
      {options.map((opt, i) => (
        <button
          key={opt.id}
          type="button"
          disabled={opt.disabled}
          onClick={() => onChange(opt.id)}
          className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
            value === opt.id
              ? 'bg-blue-600/40 text-blue-100 shadow-sm'
              : 'text-gray-400 hover:text-gray-200 disabled:opacity-40'
          } ${i > 0 ? '' : ''}`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
