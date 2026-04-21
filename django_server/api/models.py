from django.db import models


def _blob_upload_to(instance, filename: str) -> str:
    lid = instance.logical_path.replace("\\", "/").replace("/", "__")
    return f"pkg/{instance.session_id}/{lid}_{filename}"


class Project(models.Model):
    """Проект: полный JSON конфига и версия (спека 09)."""

    project_id = models.CharField(max_length=256, primary_key=True)
    name = models.CharField(max_length=512)
    config_version = models.CharField(max_length=128)
    raw_json = models.TextField(help_text="Full project JSON for clients (Project.fromJson).")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class PackageSession(models.Model):
    """Сессия приёма пакета (спека 08)."""

    class Phase(models.TextChoices):
        AWAITING_BLOBS = "awaiting_blobs", "awaiting_blobs"
        READY_TO_COMMIT = "ready_to_commit", "ready_to_commit"
        COMPLETED = "completed", "completed"
        FAILED = "failed", "failed"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="packages")
    package_id = models.CharField(max_length=512, db_index=True)
    phase = models.CharField(
        max_length=32,
        choices=Phase.choices,
        default=Phase.AWAITING_BLOBS,
    )
    manifest_json = models.TextField(blank=True, default="")
    failure_reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "package_id"],
                name="unique_package_per_project",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.project.project_id}:{self.package_id}"


class UploadedBlob(models.Model):
    """Принятый бинарный объект по логическому пути (как в манифесте)."""

    session = models.ForeignKey(
        PackageSession,
        on_delete=models.CASCADE,
        related_name="blobs",
    )
    logical_path = models.CharField(
        max_length=1024,
        help_text="Например blobs/img_0001.jpg",
    )
    size_bytes = models.PositiveBigIntegerField(default=0)
    file = models.FileField(upload_to=_blob_upload_to)
    sha256 = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "logical_path"],
                name="unique_blob_path_per_session",
            ),
        ]
