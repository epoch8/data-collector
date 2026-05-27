import type { ConfigField } from '@/types/config';
import { fieldLabel } from '@/lib/config-field';

interface Props {
  field: ConfigField;
}

export function InstructionWidget({ field }: Props) {
  const content = field.instructions ?? '';

  return (
    <div className="border border-gray-800 rounded-lg p-4 bg-indigo-950/20 border-l-2 border-l-indigo-500/40">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-sm text-gray-400 font-medium">{fieldLabel(field)}</span>
        <span className="text-[10px] text-gray-600 bg-gray-800 px-1.5 py-0.5 rounded">readonly</span>
      </div>
      <div className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">
        {renderSimpleMarkdown(content)}
      </div>
    </div>
  );
}

/** Very basic markdown: **bold** and line breaks. */
function renderSimpleMarkdown(text: string): string {
  return text.replace(/\*\*(.*?)\*\*/g, '$1');
}
