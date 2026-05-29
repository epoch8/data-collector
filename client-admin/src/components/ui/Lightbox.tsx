import { useEffect, useCallback } from 'react';
import { AuthenticatedImage } from '@/components/AuthenticatedImage';
import { blobFileName } from '@/lib/format';

export interface LightboxSlide {
  src: string;
  title: string;
  subtitle?: string;
}

interface Props {
  slides: LightboxSlide[];
  index: number;
  onClose: () => void;
  onIndexChange: (index: number) => void;
}

export function Lightbox({ slides, index, onClose, onIndexChange }: Props) {
  const slide = slides[index];

  const goPrev = useCallback(() => {
    if (slides.length <= 1) return;
    onIndexChange((index - 1 + slides.length) % slides.length);
  }, [index, slides.length, onIndexChange]);

  const goNext = useCallback(() => {
    if (slides.length <= 1) return;
    onIndexChange((index + 1) % slides.length);
  }, [index, slides.length, onIndexChange]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowLeft') goPrev();
      if (e.key === 'ArrowRight') goNext();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose, goPrev, goNext]);

  if (!slide) return null;

  return (
    <div
      className="fixed inset-0 z-[90] flex flex-col bg-black/90 backdrop-blur-sm"
      role="dialog"
      aria-modal
      onClick={onClose}
    >
      <div className="flex items-center justify-between px-4 py-3 text-sm text-gray-300">
        <span className="font-mono truncate max-w-[70%]" title={slide.title}>
          {blobFileName(slide.title)}
        </span>
        <span className="text-gray-500">
          {index + 1} / {slides.length}
        </span>
        <button
          type="button"
          onClick={onClose}
          className="px-3 py-1 rounded-md hover:bg-white/10 text-gray-300"
        >
          Закрыть
        </button>
      </div>
      <div
        className="flex-1 flex items-center justify-center px-4 pb-4 min-h-0"
        onClick={e => e.stopPropagation()}
      >
        {slides.length > 1 && (
          <button
            type="button"
            onClick={goPrev}
            className="flex-shrink-0 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 text-xl"
            aria-label="Предыдущее"
          >
            ‹
          </button>
        )}
        <AuthenticatedImage
          src={slide.src}
          alt={slide.title}
          className="max-h-[calc(100vh-8rem)] max-w-full object-contain mx-4"
        />
        {slides.length > 1 && (
          <button
            type="button"
            onClick={goNext}
            className="flex-shrink-0 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 text-xl"
            aria-label="Следующее"
          >
            ›
          </button>
        )}
      </div>
      {slide.subtitle && (
        <p className="text-center text-xs text-gray-500 pb-4 font-mono">{slide.subtitle}</p>
      )}
    </div>
  );
}
