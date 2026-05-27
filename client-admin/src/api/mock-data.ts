import type { PackageSession, PackageWorkspace } from '@/types/manifest';
import type { ProjectConfig, ProjectSummary } from '@/types/config';

export const MOCK_PROJECTS: ProjectSummary[] = [
  { project_id: 'korovas-2026', name: 'Korovas 2026', config_version: '1.0' },
];

const KOROVAS_CONFIG: ProjectConfig = {
  id: 'korovas-2026',
  name: 'Korovas 2026',
  version: '1.0',
  config: {
    fields: [
      {
        field_id: 'cow_identifier',
        type: 'text_input',
        title: 'ID коровы',
        instructions: 'Напр. Bessie-99',
        validation: { required: true },
      },
      {
        field_id: 'cow_age',
        type: 'text_input',
        title: 'Возраст (мес.)',
        instructions: '',
        validation: { required: false },
      },
      {
        field_id: 'cow_weight',
        type: 'text_input',
        title: 'Вес (кг)',
        instructions: '',
        validation: { required: false },
      },
      {
        field_id: 'cow_breed',
        type: 'text_input',
        title: 'Порода',
        instructions: '',
        validation: { required: false },
      },
      {
        field_id: 'scan_time',
        type: 'datetime',
        title: 'Время сканирования',
        instructions: '',
        validation: { required: true },
      },
      {
        field_id: 'scan_instruction',
        type: 'instruction',
        title: 'Инструкция',
        instructions: '**Убедитесь**, что корова стоит ровно и хвост не загораживает крестец.',
      },
      {
        field_id: 'pose_1',
        type: 'camera_photo',
        title: 'Поза 1 (вид сбоку)',
        instructions: 'Снимите корову сбоку.',
        validation: { required: true },
      },
    ],
    flow: {
      steps: [
        {
          id: 'cow_data',
          screen: 'scroll_form',
          form_title: 'Данные коровы',
          field_ids: ['cow_identifier', 'cow_age', 'cow_weight', 'cow_breed', 'scan_time'],
        },
        {
          id: 'instruction',
          screen: 'scroll_form',
          form_title: 'Инструкция',
          field_ids: ['scan_instruction'],
        },
        {
          id: 'photo',
          screen: 'scroll_form',
          form_title: 'Фото',
          field_ids: ['pose_1'],
        },
        { id: 'review', screen: 'review' },
      ],
    },
    pipelines: [
      { id: 'inference', type: 'inference', trigger: 'on_commit', inference_version_id: 'korovas-v3' },
      { id: 'cvat_export', type: 'cvat', trigger: 'on_commit', depends_on: ['inference'], cvat_project: 'korovas' },
    ],
    admin_ui: {
      skeletons: {
        korovas_v1: {
          points: [
            { id: 'withers', label: 'Холка' },
            { id: 'hook', label: 'Крючок' },
            { id: 'sacrum', label: 'Крестец' },
          ],
          edges: [['withers', 'hook'], ['hook', 'sacrum']],
        },
      },
      metric_mappings: [
        { label: 'Высота холки, см', gt_path: 'data.withers_height_cm', inference_key: 'withers_height_cm' },
        { label: 'Длина туловища, см', gt_path: 'data.body_length_cm', inference_key: 'body_length_cm' },
      ],
      annotation_defaults: { format: 'coco_keypoints', skeleton_id: 'korovas_v1' },
    },
  },
};

const SAMPLE_MANIFEST = {
  package_id: '00000000-0000-4000-8000-000000000001',
  project_id: 'korovas-2026',
  created_at: '2026-05-20T10:00:00Z',
  submitted_by: { firebase_uid: 'fixture-uid', email: 'operator@example.com' },
  data: {
    scan_time: '2026-05-20T09:55:00Z',
    cow_identifier: 'Bessie-99',
    cow_age: 36,
    cow_weight: 520,
    cow_breed: 'holstein',
    pose_1: {
      'blobs/pose_1/shot_0.jpg': {
        collected_at: '2026-05-20T09:56:00Z',
        frame_camera: {
          image_width_px: 4032, image_height_px: 3024,
          fx_px: 2800.0, fy_px: 2800.0,
          cx_px: 2016.0, cy_px: 1512.0,
          intrinsics_source: 'exif_focal_sensor',
        },
      },
    },
  },
  pipeline_results: {
    inference: {
      runs: [{
        run_id: 'run-fixture-1', pipeline_id: 'inference', version: 'korovas-v3-dev',
        status: 'done' as const,
        started_at: '2026-05-20T10:01:00Z', finished_at: '2026-05-20T10:01:04Z',
        metrics: { withers_height_cm: 142, body_length_cm: 168 },
        raw: { model: 'fixture', note: 'Replace when platform inference is wired' },
      }],
      latest: 'run-fixture-1',
    },
    cvat: {
      task_id: 99901, project_slug: 'korovas',
      status: 'annotation', updated_at: '2026-05-20T10:05:00Z',
    },
  },
  _ui_meta: {
    manifest_revision: 1,
    pipeline_log: [{ pipeline_id: 'inference', status: 'done', at: '2026-05-20T10:01:04Z' }],
  },
};

export const MOCK_PACKAGES: PackageSession[] = [
  {
    package_id: '00000000-0000-4000-8000-000000000001',
    project_id: 'korovas-2026',
    phase: 'completed',
    created_at: '2026-05-20T10:00:00Z',
    uploader_email: 'operator@example.com',
    has_inference: true,
    has_cvat: true,
    data_fields: {
      cow_identifier: 'Bessie-99',
      cow_age: 36,
      cow_weight: 520,
      cow_breed: 'holstein',
      scan_time: '2026-05-20T09:55:00Z',
    },
  },
  {
    package_id: '00000000-0000-4000-8000-000000000002',
    project_id: 'korovas-2026',
    phase: 'completed',
    created_at: '2026-05-21T08:30:00Z',
    uploader_email: 'field-user@example.com',
    has_inference: true,
    has_cvat: false,
    data_fields: {
      cow_identifier: 'Daisy-12',
      cow_age: 24,
      cow_weight: 480,
      cow_breed: 'jersey',
      scan_time: '2026-05-21T08:25:00Z',
    },
  },
  {
    package_id: '00000000-0000-4000-8000-000000000003',
    project_id: 'korovas-2026',
    phase: 'awaiting_blobs',
    created_at: '2026-05-22T14:15:00Z',
    uploader_email: 'field-user@example.com',
    has_inference: false,
    has_cvat: false,
    data_fields: {},
  },
];

export const MOCK_WORKSPACE: PackageWorkspace = {
  session: MOCK_PACKAGES[0],
  manifest: SAMPLE_MANIFEST,
  blobs: [
    {
      blob_id: 1,
      logical_path: 'blobs/pose_1/shot_0.jpg',
      size_bytes: 2_400_000,
      preview_url: 'https://placehold.co/400x300/1e293b/94a3b8?text=pose_1/shot_0.jpg',
    },
  ],
  project_config: KOROVAS_CONFIG,
};
