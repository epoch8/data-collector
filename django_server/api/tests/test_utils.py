"""Юнит-тесты вспомогательных функций (api.utils)."""

from __future__ import annotations

from django.test import SimpleTestCase

from api.utils import (
    collect_blob_refs,
    parse_json_body,
    validate_blob_logical_path,
    weak_etag,
)


class WeakEtagTests(SimpleTestCase):
    def test_weak_etag_format(self):
        etag = weak_etag("hello")
        self.assertTrue(etag.startswith('W/"'))
        self.assertTrue(etag.endswith('"'))
        # 32 hex-символа внутри кавычек.
        self.assertEqual(len(etag), len('W/"') + 32 + len('"'))

    def test_str_and_bytes_match(self):
        self.assertEqual(weak_etag("payload"), weak_etag(b"payload"))

    def test_different_input_different_etag(self):
        self.assertNotEqual(weak_etag("a"), weak_etag("b"))

    def test_deterministic(self):
        self.assertEqual(weak_etag("same"), weak_etag("same"))


class CollectBlobRefsTests(SimpleTestCase):
    def test_collects_from_nested_values(self):
        out: set[str] = set()
        collect_blob_refs(
            {"a": "blobs/one.jpg", "b": {"c": ["blobs/two.png", "x"]}},
            out,
        )
        self.assertEqual(out, {"blobs/one.jpg", "blobs/two.png"})

    def test_collects_from_keys(self):
        out: set[str] = set()
        collect_blob_refs({"blobs/key.bin": 1}, out)
        self.assertIn("blobs/key.bin", out)

    def test_normalizes_backslashes(self):
        out: set[str] = set()
        collect_blob_refs("blobs\\win\\path.jpg", out)
        self.assertIn("blobs/win/path.jpg", out)

    def test_ignores_non_blob_strings(self):
        out: set[str] = set()
        collect_blob_refs(["assets/img.jpg", "blobs/ok.jpg"], out)
        self.assertEqual(out, {"blobs/ok.jpg"})

    def test_empty_input(self):
        out: set[str] = set()
        collect_blob_refs({}, out)
        self.assertEqual(out, set())


class ValidateBlobLogicalPathTests(SimpleTestCase):
    def test_valid_path(self):
        self.assertIsNone(validate_blob_logical_path("blobs/photo.jpg"))

    def test_valid_nested_path(self):
        self.assertIsNone(validate_blob_logical_path("blobs/a/b/c.png"))

    def test_backslash_path_normalized(self):
        self.assertIsNone(validate_blob_logical_path("blobs\\a\\b.png"))

    def test_parent_traversal_rejected(self):
        self.assertEqual(
            validate_blob_logical_path("blobs/../secret"),
            "invalid_blob_path",
        )

    def test_absolute_path_rejected(self):
        self.assertEqual(
            validate_blob_logical_path("/blobs/photo.jpg"),
            "invalid_blob_path",
        )

    def test_missing_prefix_rejected(self):
        self.assertEqual(
            validate_blob_logical_path("photo.jpg"),
            "blob_path_must_start_with_blobs_slash",
        )

    def test_empty_after_prefix_rejected(self):
        self.assertEqual(
            validate_blob_logical_path("blobs/"),
            "blob_path_must_start_with_blobs_slash",
        )


class ParseJsonBodyTests(SimpleTestCase):
    def test_valid_object(self):
        data, err = parse_json_body('{"a": 1}')
        self.assertIsNone(err)
        self.assertEqual(data, {"a": 1})

    def test_invalid_json(self):
        data, err = parse_json_body("{not json}")
        self.assertIsNone(data)
        self.assertEqual(err, "invalid_json")

    def test_non_object_json(self):
        data, err = parse_json_body("[1, 2, 3]")
        self.assertIsNone(data)
        self.assertEqual(err, "expected_object")

    def test_scalar_json(self):
        data, err = parse_json_body("42")
        self.assertIsNone(data)
        self.assertEqual(err, "expected_object")
