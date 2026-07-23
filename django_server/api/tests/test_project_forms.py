"""Тесты discovery форм проекта (api.project_forms)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from api.project_forms import (
    DEFAULT_FORM_ID,
    load_project_forms,
    normalize_manifest_form_id,
)
from api.project_git import CONFIG_REL_PATH, FORMS_REL_DIR, GitProjectError


class ProjectFormsDiscoveryTests(SimpleTestCase):
    def _project(self, project_id: str = "demo") -> MagicMock:
        p = MagicMock()
        p.project_id = project_id
        return p

    def test_legacy_config_becomes_default_form(self):
        project = self._project()
        with patch("api.project_forms.pull"), patch(
            "api.project_forms.repo_dir",
        ) as repo_dir:
            root = Path(self._temp_dir())
            repo_dir.return_value = root
            cfg = root / CONFIG_REL_PATH
            cfg.parent.mkdir(parents=True)
            cfg.write_text(
                json.dumps(
                    {
                        "id": "demo",
                        "name": "Demo Form",
                        "version": "2.0",
                        "config": {"fields": [], "flow": {"steps": []}},
                    },
                ),
                encoding="utf-8",
            )
            forms = load_project_forms(project, fetch_remote=False)
        self.assertEqual(len(forms), 1)
        self.assertEqual(forms[0]["form_id"], DEFAULT_FORM_ID)
        self.assertEqual(forms[0]["name"], "Demo Form")
        self.assertEqual(forms[0]["version"], "2.0")

    def test_forms_dir_preferred_over_legacy(self):
        project = self._project()
        with patch("api.project_forms.pull"), patch(
            "api.project_forms.repo_dir",
        ) as repo_dir:
            root = Path(self._temp_dir())
            repo_dir.return_value = root
            legacy = root / CONFIG_REL_PATH
            legacy.parent.mkdir(parents=True)
            legacy.write_text(
                json.dumps({"id": "demo", "name": "Legacy", "version": "1", "config": {"fields": [], "flow": {"steps": []}}}),
                encoding="utf-8",
            )
            for fid, name in (("default", "Default Form"), ("bull", "Bull")):
                path = root / FORMS_REL_DIR / fid / "config.json"
                path.parent.mkdir(parents=True)
                path.write_text(
                    json.dumps(
                        {
                            "id": "demo",
                            "name": name,
                            "version": "1.0",
                            "config": {"fields": [], "flow": {"steps": []}},
                        },
                    ),
                    encoding="utf-8",
                )
            forms = load_project_forms(project, fetch_remote=False)
        self.assertEqual([f["form_id"] for f in forms], ["default", "bull"])
        self.assertEqual(forms[0]["name"], "Default Form")

    def test_normalize_manifest_form_id(self):
        self.assertEqual(normalize_manifest_form_id({}), DEFAULT_FORM_ID)
        self.assertEqual(normalize_manifest_form_id({"form_id": ""}), DEFAULT_FORM_ID)
        self.assertEqual(normalize_manifest_form_id({"form_id": "bull"}), "bull")
        with self.assertRaises(GitProjectError):
            normalize_manifest_form_id({"form_id": "Bad-Id"})

    def _temp_dir(self) -> str:
        import tempfile

        d = tempfile.mkdtemp(prefix="forms_test_")
        self.addCleanup(lambda: __import__("shutil").rmtree(d, ignore_errors=True))
        return d
