"""Remap legacy default-form packages to bull / young / cow by months + cow_gender."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any, Literal

from .project_git import DEFAULT_FORM_ID

YOUNG_MAX_MONTHS = 24

Sex = Literal["male", "female"]
FormId = Literal["bull", "young", "cow"]

_MALE_TOKENS = frozenset(
    {
        "бык",
        "бычок",
        "bull",
        "male",
        "bull_calf",
    }
)
_FEMALE_TOKENS = frozenset(
    {
        "корова",
        "телка",
        "нетель",
        "cow",
        "heifer",
        "female",
    }
)

# Already on a target form — do not overwrite.
_TARGET_FORMS = frozenset({"bull", "young", "cow"})

_MONTHS_RE = re.compile(r"^\s*(-?\d+(?:[.,]\d+)?)", re.UNICODE)


@dataclass(frozen=True)
class RemapDecision:
    package_id: str
    old_form_id: str
    new_form_id: str | None
    months: int | None
    sex: Sex | None
    raw_gender: str
    status: str  # ok | skip_* | already_*
    skip_reason: str = ""

    @property
    def should_apply(self) -> bool:
        return self.status == "ok" and self.new_form_id is not None


def normalize_gender_token(raw: Any) -> str:
    if raw is None:
        return ""
    s = str(raw).strip().lower().replace("ё", "е")
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_cow_gender(raw: Any) -> Sex | None:
    """Map free-text cow_gender to male/female; unknown → None."""
    token = normalize_gender_token(raw)
    if not token:
        return None
    if token in _MALE_TOKENS:
        return "male"
    if token in _FEMALE_TOKENS:
        return "female"
    return None


def parse_months(raw: Any) -> int | None:
    """Parse age in months from int/float/string; None if missing/unparseable."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        if raw != raw:  # NaN
            return None
        return int(raw)
    s = str(raw).strip().replace(",", ".")
    m = _MONTHS_RE.match(s)
    if not m:
        return None
    try:
        return int(float(m.group(1)))
    except ValueError:
        return None


def current_form_id(manifest: dict[str, Any]) -> str:
    raw = manifest.get("form_id")
    if raw is None or raw == "":
        return DEFAULT_FORM_ID
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return DEFAULT_FORM_ID


def decide_remap(package_id: str, manifest: dict[str, Any]) -> RemapDecision:
    """Decide target form_id for a package manifest (no I/O)."""
    old = current_form_id(manifest)
    data = manifest.get("data")
    if not isinstance(data, dict):
        data = {}

    raw_gender = data.get("cow_gender", "")
    raw_gender_s = "" if raw_gender is None else str(raw_gender)
    sex = normalize_cow_gender(raw_gender)
    months = parse_months(data.get("months"))

    if old in _TARGET_FORMS:
        return RemapDecision(
            package_id=package_id,
            old_form_id=old,
            new_form_id=None,
            months=months,
            sex=sex,
            raw_gender=raw_gender_s,
            status="already_mapped",
            skip_reason=f"already form_id={old}",
        )

    if old != DEFAULT_FORM_ID:
        return RemapDecision(
            package_id=package_id,
            old_form_id=old,
            new_form_id=None,
            months=months,
            sex=sex,
            raw_gender=raw_gender_s,
            status="skip_other_form",
            skip_reason=f"form_id={old} is not default",
        )

    if months is None:
        return RemapDecision(
            package_id=package_id,
            old_form_id=old,
            new_form_id=None,
            months=None,
            sex=sex,
            raw_gender=raw_gender_s,
            status="skip_months",
            skip_reason="months missing or unparseable",
        )

    if months <= YOUNG_MAX_MONTHS:
        return RemapDecision(
            package_id=package_id,
            old_form_id=old,
            new_form_id="young",
            months=months,
            sex=sex,
            raw_gender=raw_gender_s,
            status="ok",
        )

    if sex is None:
        return RemapDecision(
            package_id=package_id,
            old_form_id=old,
            new_form_id=None,
            months=months,
            sex=None,
            raw_gender=raw_gender_s,
            status="skip_gender",
            skip_reason="cow_gender missing or unrecognized for adult animal",
        )

    new_form: FormId = "bull" if sex == "male" else "cow"
    return RemapDecision(
        package_id=package_id,
        old_form_id=old,
        new_form_id=new_form,
        months=months,
        sex=sex,
        raw_gender=raw_gender_s,
        status="ok",
    )


def apply_decision_to_manifest(
    manifest: dict[str, Any],
    decision: RemapDecision,
    *,
    form_name: str | None = None,
    form_version: str | None = None,
) -> dict[str, Any]:
    """Return a shallow-copied manifest with form_id (and young_sex when applicable)."""
    if not decision.should_apply or decision.new_form_id is None:
        raise ValueError(f"Cannot apply decision status={decision.status}")

    out = copy.deepcopy(manifest)
    out["form_id"] = decision.new_form_id
    if form_name:
        out["form_name"] = form_name
    if form_version:
        out["form_version"] = form_version

    data = out.get("data")
    if not isinstance(data, dict):
        data = {}
        out["data"] = data

    if decision.new_form_id == "young" and decision.sex is not None:
        data["young_sex"] = "bull_calf" if decision.sex == "male" else "heifer"

    return out
