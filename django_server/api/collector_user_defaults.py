"""Назначение проектов новым CollectorUser (первый вход / импорт из Firebase)."""

from __future__ import annotations

import logging

from django.conf import settings

from .models import CollectorUser, Project

logger = logging.getLogger(__name__)


def assign_default_collector_project(user: CollectorUser) -> None:
    """
    Добавляет проект из DEFAULT_COLLECTOR_PROJECT_ID, если запись есть в БД.
    Безопасно вызывать повторно (M2M не дублирует связь).
    """
    pid = (getattr(settings, "DEFAULT_COLLECTOR_PROJECT_ID", None) or "").strip()
    if not pid:
        return
    proj = Project.objects.filter(project_id=pid).first()
    if proj is None:
        logger.warning(
            "DEFAULT_COLLECTOR_PROJECT_ID=%r: проекта нет в БД, доступ не назначен",
            pid,
        )
        return
    user.projects.add(proj)
