"""Compatibility tests for package rows after the production DB migration."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from django.test import TestCase

from api import project_db, project_packages
from api.models import GitCredential, Project


class PackageSchemaCompatibilityTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.credential = GitCredential.objects.create(
            label="test",
            public_key="test",
            private_key_encrypted="test",
        )

    def database_uri(self, name: str) -> str:
        path = Path(self.tmp.name) / f"{name}.sqlite3"
        return "sqlite:///" + path.as_posix()

    def create_project(self, project_id: str, database_uri: str) -> Project:
        return Project.objects.create(
            project_id=project_id,
            name=project_id,
            git_remote="git@example.invalid:test.git",
            git_credential=self.credential,
            database_uri=database_uri,
        )

    def test_dedicated_database_keeps_stale_project_rows_visible(self):
        self.create_project("korovas", self.database_uri("dedicated"))
        project_packages.get_or_create_session("korovas", "pkg-legacy")
        with project_db.connect("korovas") as conn:
            conn.execute(
                "UPDATE package_session SET project_id = ? WHERE package_id = ?",
                ("old-korovas", "pkg-legacy"),
            )

        sessions = project_packages.list_sessions("korovas")

        self.assertEqual([session.package_id for session in sessions], ["pkg-legacy"])
        self.assertIsNotNone(project_packages.get_session("korovas", "pkg-legacy"))

    def test_shared_database_keeps_strict_project_isolation(self):
        uri = self.database_uri("shared")
        self.create_project("korovas", uri)
        project_packages.get_or_create_session("korovas", "pkg-legacy")
        with project_db.connect("korovas") as conn:
            conn.execute(
                "UPDATE package_session SET project_id = ? WHERE package_id = ?",
                ("old-korovas", "pkg-legacy"),
            )
        self.create_project("other", uri)

        self.assertEqual(project_packages.list_sessions("korovas"), [])
        self.assertIsNone(project_packages.get_session("korovas", "pkg-legacy"))

    def test_new_inference_schema_resolves_uploaded_blob_path(self):
        self.create_project("korovas", self.database_uri("new-schema"))
        project_packages.get_or_create_session("korovas", "pkg-1")
        with project_db.connect("korovas") as conn:
            conn.execute(
                """
                INSERT INTO uploaded_blob (
                    package_id, logical_path, size_bytes, sha256,
                    storage_path, created_at
                ) VALUES (?, ?, 1, 'sha', ?, 'now')
                """,
                ("pkg-1", "blobs/image.jpg", "packages/pkg-1/blobs/image.jpg"),
            )

        project_db.insert_inference(
            "korovas",
            package_id="pkg-1",
            manifest_blob_key="blobs/image.jpg",
            source_export="test",
            image_size={"width": 10, "height": 20},
            inference={"keypoints": []},
        )

        rows = project_db.list_inference("korovas", "pkg-1")

        self.assertEqual([row["manifest_blob_key"] for row in rows], ["blobs/image.jpg"])

    def test_legacy_inference_schema_remains_supported(self):
        uri = self.database_uri("legacy-schema")
        path = Path(uri.removeprefix("sqlite:///"))
        with sqlite3.connect(path) as conn:
            conn.execute(
                """
                CREATE TABLE cow_inference_result (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_id TEXT NOT NULL,
                    manifest_blob_key TEXT NOT NULL,
                    source_export TEXT NOT NULL,
                    image_width INTEGER NOT NULL,
                    image_height INTEGER NOT NULL,
                    inference_json TEXT NOT NULL,
                    depth_blob_key TEXT,
                    depth_format TEXT NOT NULL,
                    depth_unit TEXT NOT NULL,
                    depth_width INTEGER,
                    depth_height INTEGER,
                    created_at TEXT NOT NULL,
                    UNIQUE(package_id, manifest_blob_key)
                )
                """,
            )
        self.create_project("korovas", uri)

        project_db.insert_inference(
            "korovas",
            package_id="pkg-1",
            manifest_blob_key="blobs/image.jpg",
            source_export="test",
            image_size={"width": 10, "height": 20},
            inference={"keypoints": []},
        )

        rows = project_db.list_inference("korovas", "pkg-1")

        self.assertEqual([row["manifest_blob_key"] for row in rows], ["blobs/image.jpg"])
