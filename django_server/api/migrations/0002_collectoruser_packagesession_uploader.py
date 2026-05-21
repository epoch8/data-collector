from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CollectorUser",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("firebase_uid", models.CharField(db_index=True, max_length=128, unique=True, verbose_name="Firebase UID")),
                (
                    "email",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        max_length=254,
                        verbose_name="Email (из токена / для отображения)",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "projects",
                    models.ManyToManyField(
                        blank=True,
                        related_name="collector_users",
                        to="api.project",
                        verbose_name="Доступные проекты",
                    ),
                ),
            ],
            options={
                "verbose_name": "Сборщик (Firebase)",
                "verbose_name_plural": "Сборщики (Firebase)",
                "ordering": ["email", "firebase_uid"],
            },
        ),
        migrations.AddField(
            model_name="packagesession",
            name="uploader_email",
            field=models.CharField(blank=True, default="", max_length=254),
        ),
        migrations.AddField(
            model_name="packagesession",
            name="uploader_uid",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Firebase UID создателя сессии (первый POST packages).",
                max_length=128,
            ),
        ),
    ]
