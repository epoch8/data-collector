"""Юнит-тесты валидатора конфига проекта (api.project_config_validate)."""

from __future__ import annotations

import copy
from typing import Any

from django.test import SimpleTestCase

from api.project_config_validate import validate_project_payload

PROJECT_ID = "proj-1"


def valid_payload() -> dict[str, Any]:
    """Заведомо корректный конфиг — база для мутаций в тестах."""
    return {
        "id": PROJECT_ID,
        "name": "Test project",
        "version": "1",
        "config": {
            "fields": [
                {
                    "field_id": "f_text",
                    "type": "text_input",
                    "title": "Text",
                    "instructions": "",
                },
                {
                    "field_id": "f_photo",
                    "type": "camera_photo",
                    "title": "Photo",
                    "instructions": "Make a photo",
                },
            ],
            "flow": {
                "steps": [
                    {
                        "id": "s1",
                        "screen": "scroll_form",
                        "field_ids": ["f_text", "f_photo"],
                    },
                    {"id": "s2", "screen": "review"},
                ],
            },
        },
    }


class ValidPayloadTests(SimpleTestCase):
    def test_valid_payload_has_no_errors(self):
        self.assertEqual(validate_project_payload(valid_payload(), PROJECT_ID), [])

    def test_id_optional(self):
        payload = valid_payload()
        del payload["id"]
        self.assertEqual(validate_project_payload(payload, PROJECT_ID), [])

    def test_version_optional(self):
        payload = valid_payload()
        del payload["version"]
        self.assertEqual(validate_project_payload(payload, PROJECT_ID), [])

    def test_screen_aliases_normalized(self):
        payload = valid_payload()
        payload["config"]["flow"]["steps"][0]["screen"] = "Scroll-Form"
        self.assertEqual(validate_project_payload(payload, PROJECT_ID), [])


class RootLevelTests(SimpleTestCase):
    def test_root_must_be_dict(self):
        errs = validate_project_payload(["not", "a", "dict"], PROJECT_ID)  # type: ignore[arg-type]
        self.assertEqual(len(errs), 1)
        self.assertIn("объектом", errs[0])

    def test_id_must_match_project_id(self):
        payload = valid_payload()
        payload["id"] = "other-id"
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any("должно совпадать" in e for e in errs))

    def test_name_required_non_empty(self):
        payload = valid_payload()
        payload["name"] = "   "
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any("name" in e for e in errs))

    def test_version_must_be_string(self):
        payload = valid_payload()
        payload["version"] = 1
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any("version" in e for e in errs))

    def test_config_must_be_object(self):
        payload = valid_payload()
        payload["config"] = "nope"
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any("config должно быть объектом" in e for e in errs))


class FieldsTests(SimpleTestCase):
    def test_fields_must_be_non_empty_list(self):
        payload = valid_payload()
        payload["config"]["fields"] = []
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any("config.fields" in e for e in errs))

    def test_field_needs_field_id(self):
        payload = valid_payload()
        del payload["config"]["fields"][0]["field_id"]
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any("field_id" in e for e in errs))

    def test_duplicate_field_id(self):
        payload = valid_payload()
        payload["config"]["fields"][1]["field_id"] = "f_text"
        payload["config"]["flow"]["steps"][0]["field_ids"] = ["f_text"]
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any("Дублируется field_id" in e for e in errs))

    def test_unknown_field_type(self):
        payload = valid_payload()
        payload["config"]["fields"][0]["type"] = "wat"
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any("неизвестный type" in e for e in errs))

    def test_missing_required_field_keys(self):
        payload = valid_payload()
        del payload["config"]["fields"][0]["instructions"]
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any("instructions" in e for e in errs))

    def test_priority_must_be_number(self):
        payload = valid_payload()
        payload["config"]["fields"][0]["priority"] = "high"
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any("priority" in e for e in errs))

    def test_priority_number_allowed(self):
        payload = valid_payload()
        payload["config"]["fields"][0]["priority"] = 5
        self.assertEqual(validate_project_payload(payload, PROJECT_ID), [])


class FlowTests(SimpleTestCase):
    def test_flow_must_be_object(self):
        payload = valid_payload()
        payload["config"]["flow"] = []
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any("config.flow должен быть объектом" in e for e in errs))

    def test_steps_must_be_non_empty(self):
        payload = valid_payload()
        payload["config"]["flow"]["steps"] = []
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any("flow.steps" in e for e in errs))

    def test_unknown_screen(self):
        payload = valid_payload()
        payload["config"]["flow"]["steps"][0]["screen"] = "legacy_wizard"
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any("Неизвестный или устаревший screen" in e for e in errs))

    def test_review_required(self):
        payload = valid_payload()
        payload["config"]["flow"]["steps"] = [
            {"id": "s1", "screen": "scroll_form", "field_ids": ["f_text", "f_photo"]},
        ]
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any("Нужен шаг review" in e for e in errs))

    def test_review_must_be_single(self):
        payload = valid_payload()
        payload["config"]["flow"]["steps"].append({"id": "s3", "screen": "review"})
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any("review должен быть ровно один" in e for e in errs))

    def test_review_must_be_last(self):
        payload = valid_payload()
        payload["config"]["flow"]["steps"] = [
            {"id": "s0", "screen": "review"},
            {"id": "s1", "screen": "scroll_form", "field_ids": ["f_text", "f_photo"]},
        ]
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any("review должен быть последним" in e for e in errs))

    def test_scroll_form_required(self):
        payload = valid_payload()
        payload["config"]["flow"]["steps"] = [{"id": "s2", "screen": "review"}]
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any("хотя бы один шаг scroll_form" in e for e in errs))

    def test_scroll_form_needs_field_ids(self):
        payload = valid_payload()
        payload["config"]["flow"]["steps"][0]["field_ids"] = []
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any("нужен непустой массив field_ids" in e for e in errs))

    def test_unknown_field_id_in_step(self):
        payload = valid_payload()
        payload["config"]["flow"]["steps"][0]["field_ids"] = ["f_text", "ghost"]
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any('неизвестный field_id "ghost"' in e for e in errs))

    def test_field_assigned_to_two_steps(self):
        payload = valid_payload()
        payload["config"]["flow"]["steps"] = [
            {"id": "s1", "screen": "scroll_form", "field_ids": ["f_text"]},
            {"id": "s1b", "screen": "scroll_form", "field_ids": ["f_text", "f_photo"]},
            {"id": "s2", "screen": "review"},
        ]
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any("только в одном scroll_form" in e for e in errs))

    def test_field_repeated_in_same_step(self):
        payload = valid_payload()
        payload["config"]["flow"]["steps"][0]["field_ids"] = ["f_text", "f_text", "f_photo"]
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any("повторяется в field_ids" in e for e in errs))

    def test_field_not_used_in_any_step(self):
        payload = valid_payload()
        payload["config"]["flow"]["steps"][0]["field_ids"] = ["f_text"]
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any('Поле "f_photo" не указано' in e for e in errs))

    def test_cow_id_hints_requires_field(self):
        payload = valid_payload()
        payload["config"]["flow"]["steps"][0]["cow_id_hints"] = True
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any("cow_id_field_id" in e for e in errs))

    def test_cow_id_field_must_be_in_field_ids(self):
        payload = valid_payload()
        payload["config"]["flow"]["steps"][0]["cow_id_hints"] = True
        payload["config"]["flow"]["steps"][0]["cow_id_field_id"] = "ghost"
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any('должен входить в field_ids' in e for e in errs))

    def test_cow_id_hints_valid(self):
        payload = valid_payload()
        payload["config"]["flow"]["steps"][0]["cow_id_hints"] = True
        payload["config"]["flow"]["steps"][0]["cow_id_field_id"] = "f_text"
        self.assertEqual(validate_project_payload(payload, PROJECT_ID), [])


class UiTests(SimpleTestCase):
    def test_ui_optional_object(self):
        payload = valid_payload()
        payload["config"]["ui"] = {"theme": "dark"}
        self.assertEqual(validate_project_payload(payload, PROJECT_ID), [])

    def test_ui_wrong_type(self):
        payload = valid_payload()
        payload["config"]["ui"] = "dark"
        errs = validate_project_payload(payload, PROJECT_ID)
        self.assertTrue(any("config.ui" in e for e in errs))


class ImmutabilityTests(SimpleTestCase):
    def test_validation_does_not_mutate_input(self):
        payload = valid_payload()
        snapshot = copy.deepcopy(payload)
        validate_project_payload(payload, PROJECT_ID)
        self.assertEqual(payload, snapshot)
