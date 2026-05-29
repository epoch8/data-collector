export interface DatapipePoint {
  label: string;
  x: number;
  y: number;
}

export interface DatapipeBox {
  label: string;
  xtl: number;
  ytl: number;
  xbr: number;
  ybr: number;
}

/** Строка таблицы `cow_keypoint_annotation` (mock datapipe). */
export interface CowKeypointAnnotationRecord {
  package_id: string;
  project_id: string;
  manifest_blob_key: string;
  cvat_link: string;
  image_size: {
    width: number;
    height: number;
  };
  annotation: {
    boxes: DatapipeBox[];
    points: DatapipePoint[];
  };
}

export interface CowKeypointAnnotationTable {
  table: 'cow_keypoint_annotation';
  version: number;
  generated_from: string;
  records: CowKeypointAnnotationRecord[];
}

/** @deprecated используйте CowKeypointAnnotationRecord */
export type DatapipeAnnotationRecord = CowKeypointAnnotationRecord;

/** @deprecated используйте CowKeypointAnnotationTable */
export type DatapipeAnnotationsMockTable = CowKeypointAnnotationTable;

export interface InferenceSegment {
  label: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  value_cm?: number;
  mode?: string;
}

export interface InferenceKeypoint extends DatapipePoint {
  confidence?: number;
}

export interface CowInferenceRecord {
  package_id: string;
  project_id: string;
  manifest_blob_key: string;
  source_export: string;
  image_size: { width: number; height: number };
  inference: {
    processing_time_sec?: number;
    distances?: Record<string, number>;
    annotation: {
      boxes: DatapipeBox[];
      keypoints: InferenceKeypoint[];
      segments: InferenceSegment[];
    };
  };
  depth_map?: {
    asset_path: string;
    width: number;
    height: number;
    format?: 'npy' | 'png';
    /** Единица значений в массиве глубины (mock: метры). */
    unit?: 'm' | 'cm';
  };
}

export interface CowInferenceTable {
  table: 'cow_inference_result';
  version: number;
  records: CowInferenceRecord[];
}

export type AnnotationPalette = 'gt' | 'inference';

export interface AnnotationLayer {
  id: string;
  palette: AnnotationPalette;
  visible: boolean;
  boxes: DatapipeBox[];
  points: DatapipePoint[];
  segments?: InferenceSegment[];
}
