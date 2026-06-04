from django.db import models


def _blob_upload_to(instance, filename: str) -> str:
    lid = instance.logical_path.replace("\\", "/").replace("/", "__")
    return f"pkg/{instance.session_id}/{lid}_{filename}"


class CollectorUser(models.Model):
    """Пользователь мобильного приложения (Firebase Auth): UID — ключ, email для списка в админке."""

    firebase_uid = models.CharField("Firebase UID", max_length=128, unique=True, db_index=True)
    email = models.CharField("Email (из токена / для отображения)", max_length=254, blank=True, db_index=True)
    mobile_projects = models.ManyToManyField(
        "Project",
        blank=True,
        related_name="mobile_collector_users",
        verbose_name="Доступные проекты (мобильное приложение)",
        help_text="Каталог /v1/projects и загрузка пакетов с телефона.",
    )
    admin_projects = models.ManyToManyField(
        "Project",
        blank=True,
        related_name="admin_collector_users",
        verbose_name="Доступные проекты (Client-admin)",
        help_text="Веб /ui/packages/ — Firebase-вход, только отмеченные проекты.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["email", "firebase_uid"]
        verbose_name = "Пользователь (Firebase)"
        verbose_name_plural = "Пользователи (Firebase)"

    def __str__(self) -> str:
        if self.email:
            return f"{self.email} ({self.firebase_uid})"
        return self.firebase_uid


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
    uploader_uid = models.CharField(
        max_length=128,
        blank=True,
        default="",
        db_index=True,
        help_text="Firebase UID создателя сессии (первый POST packages).",
    )
    uploader_email = models.CharField(max_length=254, blank=True, default="")
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
