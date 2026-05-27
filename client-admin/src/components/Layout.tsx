import { NavLink, Outlet } from 'react-router-dom';

export function Layout() {
  return (
    <div className="flex h-screen bg-[var(--color-surface)] text-gray-200">
      <aside className="w-60 flex-shrink-0 border-r border-[var(--color-border)] bg-[var(--color-surface-raised)] flex flex-col">
        <div className="px-5 py-5 border-b border-[var(--color-border)]">
          <div className="flex items-center gap-2">
            <span className="w-8 h-8 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 text-xs font-bold">
              DC
            </span>
            <div>
              <h1 className="text-sm font-bold tracking-wide text-gray-100">Data Collector</h1>
              <span className="text-[10px] text-gray-500">client-admin</span>
            </div>
          </div>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          <SideLink to="/packages" label="Пакеты" />
        </nav>
        <div className="px-5 py-3 border-t border-[var(--color-border)] text-[10px] text-gray-600">
          Ядро v1.1 · Data + Media
        </div>
      </aside>
      <main className="flex-1 overflow-auto min-w-0 bg-[var(--color-surface)]">
        <Outlet />
      </main>
    </div>
  );
}

function SideLink({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `block px-3 py-2 rounded-md text-sm transition-colors ${
          isActive
            ? 'bg-blue-600/20 text-blue-300 font-medium border border-blue-500/20'
            : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
        }`
      }
    >
      {label}
    </NavLink>
  );
}
