"""Unit tests for default → bull/young/cow package remapping."""

from __future__ import annotations

from django.test import SimpleTestCase

from api.package_form_remap import (
    apply_decision_to_manifest,
    decide_remap,
    normalize_cow_gender,
    parse_months,
)


class ParseMonthsTests(SimpleTestCase):
    def test_int_float_string(self):
        self.assertEqual(parse_months(18), 18)
        self.assertEqual(parse_months(18.7), 18)
        self.assertEqual(parse_months("24"), 24)
        self.assertEqual(parse_months("25 мес"), 25)
        self.assertEqual(parse_months("12,5"), 12)

    def test_missing(self):
        self.assertIsNone(parse_months(None))
        self.assertIsNone(parse_months(""))
        self.assertIsNone(parse_months("нет"))
        self.assertIsNone(parse_months(True))


class NormalizeGenderTests(SimpleTestCase):
    def test_male_synonyms(self):
        for raw in ("бык", "Бык", "бычок", "bull", "MALE", "bull_calf"):
            self.assertEqual(normalize_cow_gender(raw), "male", raw)

    def test_female_synonyms(self):
        for raw in ("корова", "телка", "тёлка", "нетель", "cow", "heifer", "female"):
            self.assertEqual(normalize_cow_gender(raw), "female", raw)

    def test_ambiguous(self):
        for raw in ("", None, "теленок", "телёнок", "???", "КРС"):
            self.assertIsNone(normalize_cow_gender(raw), raw)


class DecideRemapTests(SimpleTestCase):
    def _manifest(self, *, form_id=None, months=None, gender=None, extra=None):
        data = {}
        if months is not None:
            data["months"] = months
        if gender is not None:
            data["cow_gender"] = gender
        if extra:
            data.update(extra)
        m = {"package_id": "p1", "data": data}
        if form_id is not None:
            m["form_id"] = form_id
        return m

    def test_missing_form_id_treated_as_default(self):
        d = decide_remap("p1", self._manifest(months=10, gender="бычок"))
        self.assertEqual(d.old_form_id, "default")
        self.assertEqual(d.new_form_id, "young")
        self.assertEqual(d.status, "ok")

    def test_young_threshold(self):
        d24 = decide_remap("p1", self._manifest(form_id="default", months=24, gender="корова"))
        self.assertEqual(d24.new_form_id, "young")
        d25 = decide_remap("p1", self._manifest(form_id="default", months=25, gender="корова"))
        self.assertEqual(d25.new_form_id, "cow")

    def test_adult_bull_and_cow(self):
        bull = decide_remap("p1", self._manifest(form_id="default", months=30, gender="бык"))
        self.assertEqual(bull.new_form_id, "bull")
        cow = decide_remap("p1", self._manifest(form_id="default", months=30, gender="корова"))
        self.assertEqual(cow.new_form_id, "cow")

    def test_skip_months(self):
        d = decide_remap("p1", self._manifest(form_id="default", gender="бык"))
        self.assertEqual(d.status, "skip_months")
        self.assertIsNone(d.new_form_id)

    def test_skip_gender_adult(self):
        d = decide_remap("p1", self._manifest(form_id="default", months=30, gender="теленок"))
        self.assertEqual(d.status, "skip_gender")

    def test_young_without_gender_ok(self):
        d = decide_remap("p1", self._manifest(form_id="default", months=12, gender="теленок"))
        self.assertEqual(d.status, "ok")
        self.assertEqual(d.new_form_id, "young")
        self.assertIsNone(d.sex)

    def test_already_mapped(self):
        d = decide_remap("p1", self._manifest(form_id="bull", months=30, gender="бык"))
        self.assertEqual(d.status, "already_mapped")
        self.assertFalse(d.should_apply)

    def test_other_form_skipped(self):
        d = decide_remap("p1", self._manifest(form_id="cow_inference", months=12, gender="бычок"))
        self.assertEqual(d.status, "skip_other_form")


class ApplyDecisionTests(SimpleTestCase):
    def test_young_sets_young_sex(self):
        manifest = {
            "form_id": "default",
            "data": {"months": "8", "cow_gender": "бычок", "cow_identifier": "X"},
        }
        decision = decide_remap("p1", manifest)
        out = apply_decision_to_manifest(
            manifest,
            decision,
            form_name="Молодняк",
            form_version="2.1",
        )
        self.assertEqual(out["form_id"], "young")
        self.assertEqual(out["form_name"], "Молодняк")
        self.assertEqual(out["form_version"], "2.1")
        self.assertEqual(out["data"]["young_sex"], "bull_calf")
        self.assertEqual(out["data"]["cow_gender"], "бычок")

    def test_young_heifer(self):
        manifest = {"form_id": "default", "data": {"months": 6, "cow_gender": "тёлка"}}
        decision = decide_remap("p1", manifest)
        out = apply_decision_to_manifest(manifest, decision)
        self.assertEqual(out["data"]["young_sex"], "heifer")

    def test_adult_no_young_sex(self):
        manifest = {"form_id": "default", "data": {"months": 40, "cow_gender": "бык"}}
        decision = decide_remap("p1", manifest)
        out = apply_decision_to_manifest(manifest, decision)
        self.assertEqual(out["form_id"], "bull")
        self.assertNotIn("young_sex", out["data"])
