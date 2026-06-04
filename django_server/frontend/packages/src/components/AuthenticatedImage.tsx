import type { ImgHTMLAttributes } from 'react';
import { useEffect, useState } from 'react';
import { resolveAuthenticatedImageUrl } from '@/lib/authenticated-media';

interface Props extends Omit<ImgHTMLAttributes<HTMLImageElement>, 'src'> {
  src: string;
}

export function AuthenticatedImage({ src, alt = '', className, ...rest }: Props) {
  const [resolved, setResolved] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setFailed(false);
    setResolved(null);

    resolveAuthenticatedImageUrl(src)
      .then(url => {
        if (!cancelled) setResolved(url);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });

    return () => {
      cancelled = true;
    };
  }, [src]);

  if (failed) {
    return (
      <div
        className={className}
        role="img"
        aria-label={alt}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'rgb(30 41 59)',
          color: '#94a3b8',
          fontSize: '0.65rem',
        }}
      >
        Нет превью
      </div>
    );
  }

  if (!resolved) {
    return (
      <div
        className={className}
        aria-hidden
        style={{ background: 'rgb(30 41 59 / 0.6)', animation: 'pulse 1.5s ease-in-out infinite' }}
      />
    );
  }

  return <img src={resolved} alt={alt} className={className} {...rest} />;
}
