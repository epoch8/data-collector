export type WorkspaceTab = 'data' | 'media';

interface Tab {
  id: WorkspaceTab;
  label: string;
}

interface Props {
  tabs: Tab[];
  active: WorkspaceTab;
  onChange: (id: WorkspaceTab) => void;
}

export function TabBar({ tabs, active, onChange }: Props) {
  return (
    <div className="flex gap-1 border-b border-[var(--color-border)] px-6 pt-2">
      {tabs.map(tab => {
        const isActive = tab.id === active;
        const activeClass =
          tab.id === 'data'
            ? 'ui-tab ui-tab--active-data'
            : tab.id === 'media'
              ? 'ui-tab ui-tab--active-media'
              : 'ui-tab';
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={isActive ? activeClass : 'ui-tab'}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
