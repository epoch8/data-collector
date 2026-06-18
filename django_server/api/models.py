from django.db import models


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


class GitCredential(models.Model):
    """SSH deploy key для одного Git-репозитория проекта."""

    label = models.CharField(max_length=256, blank=True, default="")
    public_key = models.TextField(help_text="OpenSSH public key (для Deploy keys на GitHub).")
    private_key_encrypted = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Git SSH credential"
        verbose_name_plural = "Git SSH credentials"

    def __str__(self) -> str:
        return self.label or f"credential #{self.pk}"


class Project(models.Model):
    """Проект: каталог в Django; конфиг — в Git (collector/config.json)."""

    project_id = models.CharField(max_length=256, primary_key=True)
    name = models.CharField(max_length=512)
    git_remote = models.CharField(
        max_length=512,
        help_text="SSH URL, напр. git@github.com:org/repo.git",
    )
    git_default_ref = models.CharField(max_length=128, default="main")
    git_credential = models.ForeignKey(
        GitCredential,
        on_delete=models.PROTECT,
        related_name="projects",
    )
    last_synced_sha = models.CharField(max_length=64, blank=True, default="")
    last_synced_at = models.DateTimeField(null=True, blank=True)
    sync_error = models.TextField(blank=True, default="")
    media_bucket = models.CharField(
        max_length=256,
        blank=True,
        default="",
        help_text=(
            "Deprecated: используйте storage_uri. GCS-бакет для медиа пакетов (prod)."
        ),
    )
    database_uri = models.CharField(
        max_length=1024,
        blank=True,
        default="",
        help_text=(
            "SQLAlchemy URL для project DB (пакеты + pipeline). "
            "Пусто — SQLite в PROJECT_DB_ROOT/{project_id}/project.sqlite3."
        ),
    )
    storage_uri = models.CharField(
        max_length=1024,
        blank=True,
        default="",
        help_text=(
            "fsspec URI корня blobs пакетов (file:// | gs:// | s3://). "
            "Пусто — папка в PROJECT_MEDIA_ROOT/{project_id}/."
        ),
    )
    storage_options_encrypted = models.TextField(
        blank=True,
        default="",
        help_text=(
            "Зашифрованный JSON с креды/опциями fsspec (например S3 endpoint_url/key/secret). "
            "Редактируется в UI; секрет шифруется Fernet."
        ),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def config_version_label(self) -> str:
        if self.last_synced_sha:
            return self.last_synced_sha[:12]
        return "—"
