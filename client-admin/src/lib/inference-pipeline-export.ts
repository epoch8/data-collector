/** Сырые JSON-экспорты пайплайна (`4875_mp4-0003_jpg.json` и т.д.). */
const pipelineExportModules = import.meta.glob('../../../datapipe_test/*.json', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>;

const EXCLUDED_JSON = new Set([
  'mock_datapipe_inference.json',
  'mock_datapipe_annotations.json',
  'inference.json',
  'field_changelog.json',
]);

export function getInferencePipelineExport(filename: string): unknown | null {
  if (!filename || EXCLUDED_JSON.has(filename)) return null;
  const key = Object.keys(pipelineExportModules).find(p => p.endsWith(`/${filename}`));
  if (!key) return null;
  try {
    return JSON.parse(pipelineExportModules[key]) as unknown;
  } catch {
    return null;
  }
}
