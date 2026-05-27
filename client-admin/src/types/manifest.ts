export interface InferenceRun {
  run_id: string;
  pipeline_id: string;
  version: string;
  status: 'pending' | 'running' | 'done' | 'error';
  started_at: string;
  finished_at?: string;
  metrics: Record<string, number>;
  raw: Record<string, unknown>;
}

export interface InferenceResults {
  runs: InferenceRun[];
  latest: string;
}

export interface CvatResults {
  task_id: number;
  project_slug: string;
  status: string;
  export_url?: string | null;
  updated_at: string;
}

export interface AnnotationEntry {
  format: 'coco_keypoints' | 'polygon' | 'bbox' | 'cvat_xml_ref';
  skeleton_id?: string;
  source: string;
  revision: number;
  points?: number[][];
  labels?: string[];
}

export interface PipelineResults {
  inference?: InferenceResults;
  cvat?: CvatResults;
  annotations?: Record<string, AnnotationEntry>;
}

export interface UiMeta {
  manifest_revision?: number;
  pipeline_log?: Array<{
    pipeline_id: string;
    status: string;
    at: string;
  }>;
}

export interface Manifest {
  package_id: string;
  project_id: string;
  created_at: string;
  submitted_by: {
    firebase_uid: string;
    email: string;
  };
  data: Record<string, unknown>;
  pipeline_results?: PipelineResults;
  _ui_meta?: UiMeta;
}

export interface BlobInfo {
  blob_id?: number;
  logical_path: string;
  size_bytes: number;
  preview_url: string;
}

export interface PackageSession {
  package_id: string;
  project_id: string;
  phase: string;
  created_at: string;
  uploader_email: string;
  has_inference?: boolean;
  has_cvat?: boolean;
}

export interface PackageWorkspace {
  session: PackageSession;
  manifest: Manifest;
  blobs: BlobInfo[];
  project_config: import('./config').ProjectConfig;
}
