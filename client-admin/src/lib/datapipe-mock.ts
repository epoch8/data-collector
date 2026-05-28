import mockTableRaw from '../../../datapipe_test/mock_datapipe_annotations.json?raw';
import type { CowKeypointAnnotationRecord, CowKeypointAnnotationTable } from '@/types/datapipe';

let cached: CowKeypointAnnotationTable | null = null;

function parseMockTable(): CowKeypointAnnotationTable {
  if (cached) return cached;
  const data = JSON.parse(mockTableRaw) as CowKeypointAnnotationTable;
  cached = data;
  return data;
}

export function getCowKeypointAnnotationsForPackage(
  projectId: string,
  packageId: string,
): CowKeypointAnnotationRecord[] {
  try {
    const table = parseMockTable();
    return table.records.filter(
      r => r.project_id === projectId && r.package_id === packageId,
    );
  } catch {
    return [];
  }
}

/** @deprecated используйте getCowKeypointAnnotationsForPackage */
export const getDatapipeAnnotationsForPackage = getCowKeypointAnnotationsForPackage;
