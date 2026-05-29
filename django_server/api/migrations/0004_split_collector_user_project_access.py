from django.db import migrations, models


def copy_mobile_projects_to_admin(apps, schema_editor):
    CollectorUser = apps.get_model("api", "CollectorUser")
    for user in CollectorUser.objects.all():
        user.admin_projects.set(user.mobile_projects.all())


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0003_collectoruser_verbose_names"),
    ]

    operations = [
        migrations.RenameField(
            model_name="collectoruser",
            old_name="projects",
            new_name="mobile_projects",
        ),
        migrations.AlterField(
            model_name="collectoruser",
            name="mobile_projects",
            field=models.ManyToManyField(
                blank=True,
                help_text="Каталог /v1/projects и загрузка пакетов с телефона.",
                related_name="mobile_collector_users",
                to="api.project",
                verbose_name="Доступные проекты (мобильное приложение)",
            ),
        ),
        migrations.AddField(
            model_name="collectoruser",
            name="admin_projects",
            field=models.ManyToManyField(
                blank=True,
                help_text="Веб-админка пакетов /admin-api — просмотр и правка.",
                related_name="admin_collector_users",
                to="api.project",
                verbose_name="Доступные проекты (client-admin)",
            ),
        ),
        migrations.RunPython(copy_mobile_projects_to_admin, migrations.RunPython.noop),
    ]
