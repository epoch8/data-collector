interface Props {
  title: string;
  description?: string;
}

export function EmptyState({ title, description }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      <div className="w-12 h-12 rounded-full bg-gray-800/80 border border-gray-700 flex items-center justify-center text-gray-500 text-xl mb-4">
        ∅
      </div>
      <p className="text-sm text-gray-300 font-medium">{title}</p>
      {description && <p className="text-xs text-gray-500 mt-2 max-w-sm">{description}</p>}
    </div>
  );
}
