from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0011_project_storage_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="database_options_encrypted",
            field=models.TextField(
                blank=True,
                default="",
                help_text=(
                    "Зашифрованный JSON с кредами БД (user, password). "
                    "Редактируется в UI; пароль шифруется Fernet."
                ),
            ),
        ),
        migrations.AlterField(
            model_name="project",
            name="database_uri",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "SQLAlchemy URL для project DB без логина/пароля "
                    "(postgresql+psycopg2://host:5432/db). "
                    "Креды — в database_options_encrypted. "
                    "Пусто — SQLite в PROJECT_DB_ROOT/{project_id}/."
                ),
                max_length=1024,
            ),
        ),
    ]
