import json
from datetime import datetime
from pathlib import Path

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def _parse_changed_at(raw) -> datetime:
    if isinstance(raw, datetime):
        return raw if timezone.is_aware(raw) else timezone.make_aware(raw)
    if isinstance(raw, str) and raw.strip():
        text = raw.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
            return dt if timezone.is_aware(dt) else timezone.make_aware(dt)
        except ValueError:
            pass
    return timezone.now()


def import_field_changelog_json(apps, schema_editor):
    PackageFieldChange = apps.get_model("api", "PackageFieldChange")
    PackageSession = apps.get_model("api", "PackageSession")
    legacy_path = Path(
        getattr(
            settings,
            "PACKAGE_FIELD_CHANGELOG_PATH",
            Path(settings.BASE_DIR) / "data" / "field_changelog.json",
        ),
    )
    if not legacy_path.is_file():
        return
    try:
        data = json.loads(legacy_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    if not isinstance(data, list):
        return

    rows = []
    for item in data:
        if not isinstance(item, dict):
            continue
        project_id = (item.get("project_id") or "").strip()
        package_id = (item.get("package_id") or "").strip()
        field_id = (item.get("field_id") or "").strip()
        if not project_id or not package_id or not field_id:
            continue
        session = PackageSession.objects.filter(
            project_id=project_id,
            package_id=package_id,
        ).first()
        if session is None:
            continue
        rows.append(
            PackageFieldChange(
                session=session,
                field_id=field_id,
                before_value=item.get("before"),
                after_value=item.get("after"),
                reason=(item.get("reason") or "").strip() or "imported",
                verifier_email=(item.get("verifier_email") or "").strip(),
                changed_at=_parse_changed_at(item.get("changed_at")),
            ),
        )
    if rows:
        PackageFieldChange.objects.bulk_create(rows)


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0006_git_backed_projects"),
    ]

    operations = [
        migrations.CreateModel(
            name="PackageFieldChange",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("field_id", models.CharField(db_index=True, max_length=256)),
                ("before_value", models.JSONField(blank=True, null=True)),
                ("after_value", models.JSONField(blank=True, null=True)),
                ("reason", models.TextField()),
                ("verifier_email", models.CharField(blank=True, default="", max_length=254)),
                ("changed_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="field_changes",
                        to="api.packagesession",
                    ),
                ),
            ],
            options={
                "verbose_name": "Правка поля пакета",
                "verbose_name_plural": "Правки полей пакетов",
                "ordering": ["-changed_at"],
            },
        ),
        migrations.AddIndex(
            model_name="packagefieldchange",
            index=models.Index(fields=["session", "-changed_at"], name="api_pkgfld_session_changed"),
        ),
        migrations.RunPython(import_field_changelog_json, migrations.RunPython.noop),
    ]
