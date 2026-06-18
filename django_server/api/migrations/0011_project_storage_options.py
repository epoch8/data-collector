from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0010_project_storage_uris"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="storage_options_encrypted",
            field=models.TextField(
                blank=True,
                default="",
                help_text=(
                    "Зашифрованный JSON с креды/опциями fsspec "
                    "(например S3 endpoint_url/key/secret). "
                    "Редактируется в UI; секрет шифруется Fernet."
                ),
            ),
        ),
    ]
