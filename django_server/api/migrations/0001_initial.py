import django.db.models.deletion
from django.db import migrations, models


def _legacy_blob_upload_to(instance, filename: str) -> str:
    lid = instance.logical_path.replace("\\", "/").replace("/", "__")
    return f"pkg/{instance.session_id}/{lid}_{filename}"


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Project",
            fields=[
                ("project_id", models.CharField(max_length=256, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=512)),
                ("config_version", models.CharField(max_length=128)),
                ("raw_json", models.TextField(help_text="Full project JSON for clients (Project.fromJson).")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="PackageSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("package_id", models.CharField(db_index=True, max_length=512)),
                (
                    "phase",
                    models.CharField(
                        choices=[
                            ("awaiting_blobs", "awaiting_blobs"),
                            ("ready_to_commit", "ready_to_commit"),
                            ("completed", "completed"),
                            ("failed", "failed"),
                        ],
                        default="awaiting_blobs",
                        max_length=32,
                    ),
                ),
                ("manifest_json", models.TextField(blank=True, default="")),
                ("failure_reason", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="packages",
                        to="api.project",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="UploadedBlob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("logical_path", models.CharField(help_text="Например blobs/img_0001.jpg", max_length=1024)),
                ("size_bytes", models.PositiveBigIntegerField(default=0)),
                ("file", models.FileField(upload_to=_legacy_blob_upload_to)),
                ("sha256", models.CharField(blank=True, default="", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="blobs",
                        to="api.packagesession",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="packagesession",
            constraint=models.UniqueConstraint(fields=("project", "package_id"), name="unique_package_per_project"),
        ),
        migrations.AddConstraint(
            model_name="uploadedblob",
            constraint=models.UniqueConstraint(fields=("session", "logical_path"), name="unique_blob_path_per_session"),
        ),
    ]
