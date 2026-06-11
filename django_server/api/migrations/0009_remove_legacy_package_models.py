from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0008_project_media_bucket"),
    ]

    operations = [
        migrations.DeleteModel(
            name="PackageFieldChange",
        ),
        migrations.DeleteModel(
            name="UploadedBlob",
        ),
        migrations.DeleteModel(
            name="PackageSession",
        ),
    ]
