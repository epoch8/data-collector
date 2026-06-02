export type WorkspaceTab = 'data' | 'media' | 'visualisation' | 'change_history';

interface Tab {
  id: WorkspaceTab;
  label: string;
}

interface Props {
  tabs: Tab[];
  active: WorkspaceTab;
  onChange: (id: WorkspaceTab) => void;
}

const ACTIVE_CLASS: Record<WorkspaceTab, string> = {
  data: 'ui-tab ui-tab--active-data',
  media: 'ui-tab ui-tab--active-media',
  visualisation: 'ui-tab ui-tab--active-visualisation',
  change_history: 'ui-tab ui-tab--active-visualisation',
};

export function TabBar({ tabs, active, onChange }: Props) {
  return (
    <div className="workspace-tabs border-t border-[var(--color-border)]">
      <div className="workspace-inner flex gap-1 sm:gap-2 overflow-x-auto ui-scrollbar">
        {tabs.map(tab => (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={tab.id === active ? ACTIVE_CLASS[tab.id] : 'ui-tab'}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  );
}
