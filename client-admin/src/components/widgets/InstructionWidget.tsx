import type { ConfigField } from '@/types/config';
import { FieldCard } from '@/components/ui/FieldCard';

interface Props {
  field: ConfigField;
}

export function InstructionWidget({ field }: Props) {
  return (
    <FieldCard field={field} variant="data">
      <div className="text-sm text-gray-300 leading-relaxed prose-invert space-y-2">
        {renderMarkdown(field.instructions ?? '')}
      </div>
    </FieldCard>
  );
}

function renderMarkdown(text: string) {
  const lines = text.split('\n');
  return lines.map((line, i) => {
    const trimmed = line.trim();
    if (!trimmed) return <br key={i} />;
    if (trimmed.startsWith('- ')) {
      return (
        <p key={i} className="pl-3 text-gray-400 before:content-['•'] before:mr-2 before:text-gray-600">
          {formatInline(trimmed.slice(2))}
        </p>
      );
    }
    return <p key={i}>{formatInline(trimmed)}</p>;
  });
}

function formatInline(text: string) {
  const parts = text.split(/\*\*(.*?)\*\*/g);
  return parts.map((part, i) =>
    i % 2 === 1 ? <strong key={i} className="text-gray-100 font-medium">{part}</strong> : part,
  );
}
