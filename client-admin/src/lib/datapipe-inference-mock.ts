import inferenceTableRaw from '../../../datapipe_test/mock_datapipe_inference.json?raw';
import type { CowInferenceRecord, CowInferenceTable } from '@/types/datapipe';

let cached: CowInferenceTable | null = null;

function parseTable(): CowInferenceTable {
  if (cached) return cached;
  cached = JSON.parse(inferenceTableRaw) as CowInferenceTable;
  return cached;
}

export function getCowInferenceForPackage(
  projectId: string,
  packageId: string,
): CowInferenceRecord[] {
  try {
    return parseTable().records.filter(
      r => r.project_id === projectId && r.package_id === packageId,
    );
  } catch {
    return [];
  }
}
