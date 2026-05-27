import { NavLink, Outlet } from 'react-router-dom';

export function Layout() {
  return (
    <div className="flex h-screen bg-[#0f1117] text-gray-200">
      <aside className="w-56 flex-shrink-0 border-r border-gray-800 bg-[#13151d] flex flex-col">
        <div className="px-5 py-4 border-b border-gray-800">
          <h1 className="text-sm font-bold tracking-wide text-gray-100">Data Collector</h1>
          <span className="text-[11px] text-gray-500">client-admin</span>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          <SideLink to="/packages" label="Пакеты" />
        </nav>
        <div className="px-5 py-3 border-t border-gray-800 text-[11px] text-gray-600">
          v1 core
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
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
            ? 'bg-blue-600/20 text-blue-400 font-medium'
            : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/60'
        }`
      }
    >
      {label}
    </NavLink>
  );
}
