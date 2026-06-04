"""Базовый контракт плагина визуализации (collector/viz.json → SQLite → UI)."""

from __future__ import annotations

from typing import Any, Protocol


class VizPlugin(Protocol):
    """Один plugin id = одна папка в api/viz_plugins/."""

    plugin_id: str
    allowed_tables: frozenset[str]
    requires_palette: bool

    def validate_layer(self, layer: dict[str, Any], layer_id: str, index: int) -> list[str]:
        """Проверка полей слоя в collector/viz.json."""
        ...

    def layer_options_for_api(self, layer: dict[str, Any]) -> dict[str, Any]:
        """Доп. поля слоя в ответе GET …/viz-data/ (опции отрисовки)."""
        ...

    def fetch(self, project_id: str, package_id: str, table: str) -> list[dict[str, Any]]:
        """Строки для package_id из таблицы SQLite."""
        ...
