import { useCallback, useEffect, useId, useRef, useState } from 'react';

export type VizExportAction = 'png' | 'annotated';

interface Props {
  disabled?: boolean;
  busy?: VizExportAction | null;
  pngDisabled?: boolean;
  onExport: (action: VizExportAction) => void;
}

export function VizExportMenu({ disabled, busy, pngDisabled, onExport }: Props) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuId = useId();
  const isBusy = busy != null;

  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) close();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
    };
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [open, close]);

  const pick = (action: VizExportAction) => {
    close();
    onExport(action);
  };

  return (
    <div ref={rootRef} className="viz-export-menu">
      <button
        type="button"
        className="viz-export-btn"
        disabled={disabled || isBusy}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen(v => !v)}
      >
        {isBusy ? 'Экспорт…' : 'Экспорт'}
        <span className="viz-export-menu__chevron" aria-hidden>
          ▾
        </span>
      </button>
      {open && !isBusy && (
        <div id={menuId} className="viz-export-menu__dropdown" role="menu">
          <button
            type="button"
            role="menuitem"
            className="viz-export-menu__item"
            disabled={pngDisabled}
            onClick={() => pick('png')}
          >
            <span className="viz-export-menu__item-title">PNG с слоями</span>
            <span className="viz-export-menu__item-desc">Как на экране: включённые GT, inference, глубина</span>
          </button>
          <button
            type="button"
            role="menuitem"
            className="viz-export-menu__item"
            onClick={() => pick('annotated')}
          >
            <span className="viz-export-menu__item-title">Изображение + JSON</span>
            <span className="viz-export-menu__item-desc">Оригинал и полная разметка (GT, inference, глубина)</span>
          </button>
        </div>
      )}
    </div>
  );
}
