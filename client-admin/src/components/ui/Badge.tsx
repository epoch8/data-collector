import { phaseBadgeClass, phaseLabel } from '@/lib/phase-labels';

export function PhaseBadge({ phase }: { phase: string }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded border ${phaseBadgeClass(phase)}`}>
      {phaseLabel(phase)}
    </span>
  );
}

export function Tag({ children, className = '' }: { children: string; className?: string }) {
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 ${className}`}>
      {children}
    </span>
  );
}
