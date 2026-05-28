import { Outlet } from 'react-router-dom';

/** Оболочка без бокового меню — навигация через хлебные крошки на страницах. */
export function Layout() {
  return (
    <div className="min-h-screen bg-[var(--color-surface)] text-gray-200">
      <main className="min-h-screen">
        <Outlet />
      </main>
    </div>
  );
}
