from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0009_remove_legacy_package_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="database_uri",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "SQLAlchemy URL для project DB (пакеты + pipeline). "
                    "Пусто — SQLite в PROJECT_DB_ROOT/{project_id}/project.sqlite3."
                ),
                max_length=1024,
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="storage_uri",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "fsspec URI корня blobs пакетов (file:// | gs:// | s3://). "
                    "Пусто — папка в PROJECT_MEDIA_ROOT/{project_id}/."
                ),
                max_length=1024,
            ),
        ),
        migrations.AlterField(
            model_name="project",
            name="media_bucket",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "Deprecated: используйте storage_uri. "
                    "GCS-бакет для медиа пакетов (prod)."
                ),
                max_length=256,
            ),
        ),
    ]
