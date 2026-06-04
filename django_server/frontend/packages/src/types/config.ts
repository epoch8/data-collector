/** Field types supported by both mobile app and admin */
export type FieldType = 'text_input' | 'datetime' | 'instruction' | 'camera_photo';

export interface ConfigField {
  field_id: string;
  type: FieldType;
  title: string;
  instructions: string;
  priority?: number;
  multiple?: boolean;
  validation?: {
    required?: boolean;
    min_items?: number;
  };
}

export interface FlowStep {
  id?: string;
  screen: 'scroll_form' | 'review';
  form_title?: string;
  field_ids?: string[];
}

export interface Flow {
  steps: FlowStep[];
}

export interface PipelineConfig {
  id: string;
  type: 'inference' | 'cvat' | 'annotation_sync';
  trigger: 'on_commit' | 'manual';
  depends_on?: string[];
  inference_version_id?: string;
  cvat_project?: string;
}

export interface SkeletonPoint {
  id: string;
  label: string;
}

export interface SkeletonConfig {
  points: SkeletonPoint[];
  edges: [string, string][];
}

export interface MetricMapping {
  label: string;
  gt_path: string;
  inference_key: string;
}

export interface AdminUI {
  skeletons?: Record<string, SkeletonConfig>;
  metric_mappings?: MetricMapping[];
  widget_overrides?: Record<string, string>;
  custom_tabs?: Array<{ id: string; label: string }>;
  annotation_defaults?: {
    format: string;
    skeleton_id: string;
  };
}

export interface ProjectConfig {
  id: string;
  name: string;
  version?: string;
  config: {
    fields: ConfigField[];
    flow: Flow;
    pipelines?: PipelineConfig[];
    admin_ui?: AdminUI;
    admin_plugins?: Array<{
      id: string;
      hooks: string[];
    }>;
  };
}

export interface ProjectSummary {
  project_id: string;
  name: string;
  config_version?: string;
  updated_at?: string;
}
