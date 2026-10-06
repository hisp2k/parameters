"""Regression checks for the Stage 14 review; all numerical fixtures are synthetic."""
from dataclasses import replace

import pytest

from calculator.cad_adapter.tube_bom_plan import BomPosition, build_bom_from_cad_readback
from calculator.core.project import Project
from calculator.core.release_gate import evaluate
from calculator.core.roles import Role
from calculator.core.strength_coverage import (
    StrengthItem, VerificationMethod, build_strength_registry_from_bom,
    is_fully_covered, item_is_closed, load_case_coverage, required_load_cases,
)
from calculator.core.tube_engineering import (
    DriveLocation, TubeCalcStatus, TubeEngineeringInput, TubeMethodology, TubeMethodologyResult,
    compute_tube_engineering_core,
)
from calculator.core.verification import VerificationRecord
from calculator.tests.test_tube_engineering import _sketch_questionnaire
from calculator.app import create_project


def record(case="torque", **changes):
    return replace(VerificationRecord(
        criterion_description=case, result_value=10.0, result_unit="test",
        criterion_limit=20.0, criterion_source="synthetic test criterion",
        methodology_version="test-1", computed_by="A", reviewed_by="B",
        product_revision="01", input_fingerprint="fp",
    ), **changes)


def shaft():
    return StrengthItem("TEST-SHAFT", "вал шнека", method=VerificationMethod.ANALYTICAL)


def test_single_legacy_record_does_not_close_all_shaft_checks():
    item = shaft()
    item.verification = record()
    assert not item_is_closed(item, "01", "fp")[0]


def test_complete_case_list_closes_item_and_survives_project_roundtrip(tmp_path):
    item = shaft()
    item.verifications = [record(case) for case in required_load_cases(item.component_class)]
    assert item_is_closed(item, "01", "fp") == (True, [])
    project = Project("Test", "Test", "TEST", strength_registry=[item])
    restored = Project.load(project.save(tmp_path / "test.json"))
    assert item_is_closed(restored.strength_registry[0], "01", "fp")[0]


@pytest.mark.parametrize("changes", [
    {"result_value": None}, {"result_value": 30.0}, {"product_revision": "old"},
    {"input_fingerprint": "old"}, {"reviewed_by": "A"},
])
def test_one_bad_case_keeps_item_open_despite_valid_legacy_record(changes):
    item = shaft()
    item.verification = record()
    item.verifications = [record(case) for case in required_load_cases(item.component_class)]
    item.verifications[-1] = replace(item.verifications[-1], **changes)
    assert not item_is_closed(item, "01", "fp")[0]


def test_conflicting_duplicate_case_is_not_hidden_by_first_passing_record():
    item = shaft()
    item.verifications = [record(), record(result_value=30.0)]
    assert not load_case_coverage(item, "01", "fp")["torque"]


def test_unknown_check_catalog_and_placeholder_cannot_close():
    item = StrengthItem("TEST", "крепления привода", method=VerificationMethod.ANALYTICAL,
                        verification=record())
    assert not item_is_closed(item, "01", "fp")[0]
    item = StrengthItem("уточнить_по_BOM", "болтовые соединения",
                        method=VerificationMethod.ANALYTICAL, verification=record("bolts"))
    assert not item_is_closed(item, "01", "fp")[0]


@pytest.mark.parametrize("changes", [
    {"designation": ""}, {"designation": "   "}, {"designation": "уточнить_по_BOM"},
    {"strength_component_class": None}, {"strength_component_class": " "},
    {"source": "план"},
])
def test_incomplete_bom_is_rejected_instead_of_silently_shrinking_coverage(changes):
    pos = BomPosition("TEST", "Shaft", strength_component_class="вал шнека")
    with pytest.raises(ValueError):
        build_strength_registry_from_bom([pos, replace(pos, **changes)])


def test_empty_registry_is_not_full_coverage_and_blocks_release():
    assert not is_fully_covered([], "01", "fp")
    project = Project("Test", "Test", "TEST", strength_registry=[])
    assert any("прочност" in reason.lower() and "пуст" in reason.lower()
               for reason in evaluate(project, Role.HEAD))
    with pytest.raises(ValueError):
        build_strength_registry_from_bom([])


@pytest.mark.parametrize("field", ["result_value", "criterion_limit"])
@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan"), True, "10"])
def test_verification_requires_finite_numbers(field, value):
    rec = record(**{field: value})
    assert not rec.passed()
    assert not rec.is_complete_and_valid("01", "fp")[0]


def test_zero_is_a_valid_numerical_verification_result():
    assert record(result_value=0.0).is_complete_and_valid("01", "fp")[0]


# ---------------------------------------------------------------------------
# Codex-замечание (продолжение, 18.09.2026, п.1) + независимая проверка
# (продолжение, 18.09.2026, п.2 «P1»): criterion_direction не должен молча
# нормироваться к "не более" — см. VerificationRecord.passed(). Первая
# версия этого исправления заменяла молчаливую нормировку на `raise
# ValueError`; независимая проверка потребовала другой контракт — `passed()`
# должен возвращать False (простой булев предикат, не бросающий исключение),
# а `is_complete_and_valid()` — явно ОБЪЯСНЯТЬ причину непройденной проверки.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_direction", ["", "не более", "at_most", "NOT_MORE_THAN", None, "мусор"])
def test_passed_rejects_unknown_criterion_direction_instead_of_defaulting(bad_direction):
    rec = record(result_value=25.0, criterion_limit=20.0, criterion_direction=bad_direction)
    # result_value(25) > criterion_limit(20): under the old silent "не более"
    # default this would deterministically report False (failed) anyway, so
    # this case alone would not prove the default was avoided. passed() must
    # not raise (see test_passed_never_raises_for_unknown_direction below for
    # the case that WOULD distinguish "silently не более" from "rejected").
    assert rec.passed() is False


@pytest.mark.parametrize("bad_direction", ["", "at_most", None, "мусор"])
def test_passed_never_raises_for_unknown_direction_and_never_defaults_to_at_most(bad_direction):
    # result_value(10) <= criterion_limit(20): if the unknown direction were
    # silently treated as "не более" (the old, pre-Codex-fix bug), this would
    # wrongly report True. It must report False instead — proving there is
    # no silent default, without raising an exception either.
    rec = record(result_value=10.0, criterion_limit=20.0, criterion_direction=bad_direction)
    assert rec.passed() is False


def test_is_complete_and_valid_reports_unknown_direction_without_raising():
    rec = record(result_value=25.0, criterion_limit=20.0, criterion_direction="мусор")
    ok, problems = rec.is_complete_and_valid("01", "fp")
    assert ok is False
    assert any("направлен" in p.lower() for p in problems)


def test_is_complete_and_valid_does_not_double_report_via_passed_for_unknown_direction():
    # is_complete_and_valid() must explain the broken direction exactly once
    # (via the dedicated "направление критерия" problem), not also emit a
    # second, misleading "does not satisfy criterion" line derived from
    # passed()==False for an undefined comparison.
    rec = record(result_value=10.0, criterion_limit=20.0, criterion_direction="мусор")
    ok, problems = rec.is_complete_and_valid("01", "fp")
    assert ok is False
    direction_problems = [p for p in problems if "направлен" in p.lower()]
    criterion_problems = [p for p in problems if "не удовлетворяет критерию" in p.lower()]
    assert len(direction_problems) == 1
    assert len(criterion_problems) == 0


def test_passed_still_works_for_both_known_directions():
    at_most_ok = record(result_value=10.0, criterion_limit=20.0, criterion_direction="не_более")
    at_most_bad = record(result_value=30.0, criterion_limit=20.0, criterion_direction="не_более")
    at_least_ok = record(result_value=30.0, criterion_limit=20.0, criterion_direction="не_менее")
    at_least_bad = record(result_value=10.0, criterion_limit=20.0, criterion_direction="не_менее")
    assert at_most_ok.passed() is True
    assert at_most_bad.passed() is False
    assert at_least_ok.passed() is True
    assert at_least_bad.passed() is False


class TestMethodology(TubeMethodology):
    __test__ = False
    name = "synthetic-test"
    version = "test-1"

    def __init__(self, result):
        self.result = result

    def compute(self, inp):
        return self.result


def valid_method_result():
    return TubeMethodologyResult(
        resolved=True, diameter_mm=219, step_mm=180, rotation_speed_rpm=45,
        shaft_power_kw=3.2, motor_power_kw=4, motor_selection_ok=True,
        torque_nm=680, starting_torque_nm=1020, gear_ratio=25,
        bearing_load_radial_n=4200, bearing_load_axial_n=0, mass_kg=310,
        productivity_achievable_t_per_h=5.2, requirement_met=True,
    )


def compute(result):
    return compute_tube_engineering_core(TubeEngineeringInput(
        working_length_mm=2515, incline_deg=35, bulk_density_kg_m3=1200,
        abrasiveness="средняя", max_lump_size_mm=2,
        productivity_value=5, productivity_unit="т/ч",
    ), methodology=TestMethodology(result))


@pytest.mark.parametrize("changes", [
    {"diameter_mm": None}, {"step_mm": float("nan")}, {"rotation_speed_rpm": 0},
    {"mass_kg": -1}, {"torque_nm": True}, {"shaft_power_kw": float("inf")},
    {"motor_selection_ok": False}, {"requirement_met": False},
    {"productivity_achievable_t_per_h": 1},
])
def test_methodology_cannot_report_computed_with_invalid_or_failed_results(changes):
    result = compute(replace(valid_method_result(), **changes))
    assert result.status == TubeCalcStatus.BLOCKED
    assert result.blockers


def test_resolved_flag_alone_does_not_mean_calculated():
    result = compute(TubeMethodologyResult(resolved=True))
    assert result.status == TubeCalcStatus.BLOCKED
    assert result.blockers


def test_unresolved_method_cannot_publish_numbers():
    result = compute(replace(valid_method_result(), resolved=False))
    assert result.status == TubeCalcStatus.BLOCKED
    assert result.diameter_mm is None
    assert result.torque_nm is None
    assert result.blockers


def test_valid_synthetic_method_result_is_computed():
    assert compute(valid_method_result()).status == TubeCalcStatus.COMPUTED


def test_bom_stub_does_not_claim_unobserved_model_is_absent():
    class ReachableAdapter:
        def can_read(self):
            return True
    result = build_bom_from_cad_readback(ReachableAdapter())
    assert not result.ok
    assert "не реализовано" in result.blocked_reason
    assert "ещё не существует" not in result.blocked_reason


def test_tube_rerun_keeps_nine_blockers_and_questionnaire_change_clears_checks(tmp_path):
    q = _sketch_questionnaire()
    q.optional.drive_location_graphic = DriveLocation.UPPER_END.value
    q.optional.drive_location_graphic_source = "графика эскиза, привод сверху"
    project, outcome = create_project(
        q, project_name="Test", customer="Test",
        designation="TEST-STAGE14", data_dir=tmp_path,
    )
    assert outcome.tube_result.status == TubeCalcStatus.BLOCKED
    assert len(outcome.tube_result.blockers) == 9
    item = shaft()
    item.verifications = [record()]
    project.strength_registry = [item]
    updated = _sketch_questionnaire()
    updated.optional.starts_per_day = 12
    assert project.set_questionnaire(updated)
    assert not item.verifications


def test_cad_revision_change_clears_multiple_strength_checks():
    item = shaft()
    item.verifications = [record()]
    project = Project("Test", "Test", "TEST", strength_registry=[item])
    project._invalidate_cad_results("test CAD revision")
    assert not item.verifications


def test_release_gate_uses_full_multi_check_coverage():
    item = shaft()
    project = Project("Test", "Test", "TEST", questionnaire=_sketch_questionnaire(), strength_registry=[item])
    fp = project.compute_input_fingerprint()
    item.verification = record(product_revision=project.revision, input_fingerprint=fp)
    assert any("BOM без подтверждённого" in r for r in evaluate(project, Role.HEAD))
    item.verifications = [record(case, product_revision=project.revision, input_fingerprint=fp)
                          for case in required_load_cases(item.component_class)]
    assert not any("BOM без подтверждённого" in r for r in evaluate(project, Role.HEAD))
