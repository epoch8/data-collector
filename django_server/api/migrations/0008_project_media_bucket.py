from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0007_packagefieldchange"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="media_bucket",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "GCS-бакет для медиа пакетов (prod). "
                    "Пусто — шаблон PROJECT_MEDIA_BUCKET_TEMPLATE."
                ),
                max_length=256,
            ),
        ),
    ]
