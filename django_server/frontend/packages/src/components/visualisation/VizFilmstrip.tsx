import { useEffect, useRef } from 'react';
import { AuthenticatedImage } from '@/components/AuthenticatedImage';
import { blobFileName } from '@/lib/format';

export interface FilmstripSlide {
  key: string;
  previewUrl: string;
  caption: string;
}

interface Props {
  slides: FilmstripSlide[];
  activeIndex: number;
  onSelect: (index: number) => void;
}

export function VizFilmstrip({ slides, activeIndex, onSelect }: Props) {
  const trackRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    itemRefs.current[activeIndex]?.scrollIntoView({
      behavior: 'smooth',
      block: 'nearest',
      inline: 'center',
    });
  }, [activeIndex]);

  if (slides.length <= 1) return null;

  return (
    <div className="viz-filmstrip">
      <div className="viz-filmstrip__header">
        <span className="viz-filmstrip__title">Кадры</span>
        <span className="viz-filmstrip__counter">
          {activeIndex + 1} / {slides.length}
        </span>
      </div>
      <div ref={trackRef} className="viz-filmstrip__track" role="tablist" aria-label="Кадры пакета">
        {slides.map((slide, i) => {
          const isActive = i === activeIndex;
          return (
            <button
              ref={el => {
                itemRefs.current[i] = el;
              }}
              key={slide.key}
              type="button"
              role="tab"
              aria-selected={isActive}
              aria-label={`${slide.caption}, кадр ${i + 1}`}
              onClick={() => onSelect(i)}
              className={`viz-filmstrip__item ${isActive ? 'viz-filmstrip__item--active' : ''}`}
            >
              <span className="viz-filmstrip__frame">
                <AuthenticatedImage src={slide.previewUrl} alt="" className="viz-filmstrip__img" />
                <span className="viz-filmstrip__index">{i + 1}</span>
              </span>
              <span className="viz-filmstrip__caption" title={slide.caption}>
                {blobFileName(slide.caption)}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
