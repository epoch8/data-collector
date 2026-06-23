"""Web UI access: Django User roles and project scope for /ui and /ui/api."""

from django.conf import settings
from django.db import models


class UiUserProfile(models.Model):
    class Role(models.TextChoices):
        CLIENT = "client", "Клиент (веб)"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ui_profile",
    )
    role = models.CharField(
        max_length=16,
        choices=Role.choices,
        default=Role.CLIENT,
    )
    projects = models.ManyToManyField(
        "Project",
        blank=True,
        related_name="ui_client_users",
        verbose_name="Доступные проекты (веб)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Профиль веб-доступа"
        verbose_name_plural = "Профили веб-доступа"

    def __str__(self) -> str:
        return f"{self.user.username} ({self.role})"
