/** Экран ожидания Firebase — только CSS из index.css, без tailwind-утилит. */
export function AuthLoadingScreen({ label = 'Подключение…' }: { label?: string }) {
  return (
    <div className="login-page">
      <p className="login-card__sub" style={{ margin: 0, textAlign: 'center' }}>
        {label}
      </p>
    </div>
  );
}
