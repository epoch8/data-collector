# Generated manually — Git-backed projects (конфиг в репозитории).

import django.db.models.deletion
from django.db import migrations, models


def delete_legacy_projects(apps, schema_editor):
    """Старые проекты с raw_json не мигрируются — чистый старт по спеке."""
    Project = apps.get_model("api", "Project")
    Project.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0005_uiuserprofile"),
    ]

    operations = [
        migrations.CreateModel(
            name="GitCredential",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(blank=True, default="", max_length=256)),
                ("public_key", models.TextField(help_text="OpenSSH public key (для Deploy keys на GitHub).")),
                ("private_key_encrypted", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Git SSH credential",
                "verbose_name_plural": "Git SSH credentials",
            },
        ),
        migrations.RunPython(delete_legacy_projects, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="project",
            name="config_version",
        ),
        migrations.RemoveField(
            model_name="project",
            name="raw_json",
        ),
        migrations.AddField(
            model_name="project",
            name="git_remote",
            field=models.CharField(default="", help_text="SSH URL, напр. git@github.com:org/repo.git", max_length=512),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="project",
            name="git_default_ref",
            field=models.CharField(default="main", max_length=128),
        ),
        migrations.AddField(
            model_name="project",
            name="last_synced_sha",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="project",
            name="last_synced_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="project",
            name="sync_error",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="project",
            name="git_credential",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="projects",
                to="api.gitcredential",
            ),
        ),
    ]
