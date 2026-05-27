import type { ConfigField } from '@/types/config';
import type { BlobInfo } from '@/types/manifest';
import { TextInputWidget } from './TextInputWidget';
import { DatetimeWidget } from './DatetimeWidget';
import { InstructionWidget } from './InstructionWidget';
import { CameraPhotoWidget } from './CameraPhotoWidget';

interface Props {
  field: ConfigField;
  value: unknown;
  onChange: (value: unknown) => void;
  blobs: BlobInfo[];
  readOnly?: boolean;
}

/**
 * Widget Resolver: field.type -> admin widget.
 */
export function FieldWidget({ field, value, onChange, blobs, readOnly }: Props) {
  switch (field.type) {
    case 'text_input':
      return (
        <TextInputWidget
          field={field}
          value={value as string | number | undefined}
          onChange={onChange}
          readOnly={readOnly}
        />
      );
    case 'datetime':
      return (
        <DatetimeWidget
          field={field}
          value={value as string | undefined}
        />
      );
    case 'instruction':
      return <InstructionWidget field={field} />;
    case 'camera_photo':
      return <CameraPhotoWidget field={field} value={value} blobs={blobs} />;
    default:
      return (
        <div className="border border-gray-800 rounded-lg p-3 bg-gray-900/40">
          <span className="text-xs text-gray-500">
            Неизвестный тип поля: {(field as ConfigField).type}
          </span>
        </div>
      );
  }
}
