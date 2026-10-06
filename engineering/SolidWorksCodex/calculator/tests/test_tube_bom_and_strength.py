# -*- coding: utf-8 -*-
"""
Тесты CAD-стратегии/BOM-плана и прочностной архитектуры для трубного шнека
(Issue #3, продолжение 17.09.2026, этапы 4-6):

1. План сборки (cad_adapter/tube_bom_plan.py) — дерево не порвано, каждая
   позиция честно называет источник каждого требуемого параметра.
2. build_bom_from_cad_readback() никогда не подставляет план как BOM — из
   этой среды всегда BLOCKED с понятной причиной.
3. build_strength_registry_from_bom() строит реестр из НАСТОЯЩИХ обозначений
   BOM, а не из placeholder "уточнить_по_BOM" — и требует реального BOM,
   прежде чем что-либо в реестре можно закрыть (не просто объявить).
4. VerificationRecord (core/verification.py, уже существовал до этого среза)
   не даёт "PASS" без настоящего result_value/criterion — здесь добавлены
   тесты именно под связку с реальной позицией BOM.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from calculator.cad_adapter.tube_bom_plan import (
    TUBE_SAND_001_CAD_PLAN, BomPosition, BomReadbackResult,
    build_bom_from_cad_readback, validate_plan_tree, plan_by_path, ParamOrigin,
)
from calculator.cad_adapter.interface import LocalBridgeCadAdapter
from calculator.cad_adapter.bridge_transport import FakeBridgeTransport, BridgeResponse
from calculator.core.strength_coverage import (
    StrengthItem, VerificationMethod, REQUIRED_LOAD_CASES_BY_COMPONENT_CLASS,
    required_load_cases, load_case_coverage, uncovered_load_cases,
    build_strength_registry_from_bom, build_default_registry, item_is_closed,
)
from calculator.core.verification import VerificationRecord
from calculator.core.roles import Role


# --- 1. план сборки ----------------------------------------------------------

def test_tube_cad_plan_tree_is_not_broken():
    issues = validate_plan_tree(TUBE_SAND_001_CAD_PLAN)
    assert issues == [], issues


def test_tube_cad_plan_every_item_names_source_for_every_required_param():
    for item in TUBE_SAND_001_CAD_PLAN:
        assert len(item.required_params) == len(item.param_origin), item.path
        for origin in item.param_origin:
            assert isinstance(origin, ParamOrigin)


def test_tube_cad_plan_shaft_maps_to_strength_component_class_with_load_cases():
    shaft = plan_by_path()["шнек/вал_труба"]
    assert shaft.strength_component_class == "вал шнека"
    assert set(required_load_cases(shaft.strength_component_class)) == {
        "torque", "bending", "combined_stress", "deflection", "critical_speed",
    }


# --- 2. чтение BOM из CAD всегда честно BLOCKED в этой среде -----------------

def test_build_bom_from_cad_readback_is_blocked_when_bridge_unreachable():
    transport = FakeBridgeTransport(responses={})  # sw_status не настроен -> UNEXPECTED_TOOL -> ok=False
    adapter = LocalBridgeCadAdapter(transport)
    result = build_bom_from_cad_readback(adapter)
    assert result.ok is False
    assert result.positions == []
    assert result.blocked_reason is not None and "недоступно" in result.blocked_reason.lower()


def test_build_bom_from_cad_readback_never_returns_plan_items_as_bom():
    """Даже если мост ОТВЕЧАЕТ, план — не BOM, пока нет реальной сборки (диаметр корпуса не рассчитан)."""
    transport = FakeBridgeTransport(responses={
        "sw_status": BridgeResponse(ok=True, tool="sw_status", result={}, raw={}),
    })
    adapter = LocalBridgeCadAdapter(transport)
    result = build_bom_from_cad_readback(adapter)
    assert result.ok is False
    assert result.positions == []


# --- 3. реестр прочности из реальной BOM (не generic) -------------------------

def test_build_strength_registry_from_bom_uses_real_designations_not_placeholder():
    bom = [
        BomPosition(designation="TUBE-SAND-001.02.00", name="Вал шнека", strength_component_class="вал шнека"),
        BomPosition(designation="TUBE-SAND-001.01.00", name="Корпус", strength_component_class="корпус, крышки, патрубки, фланцы"),
    ]
    registry = build_strength_registry_from_bom(bom)
    positions = {item.bom_position for item in registry}
    assert positions == {"TUBE-SAND-001.02.00", "TUBE-SAND-001.01.00"}
    assert all(p != "уточнить_по_BOM" for p in positions)


def test_build_strength_registry_from_bom_differs_from_generic_default():
    generic = build_default_registry()
    assert all(item.bom_position == "уточнить_по_BOM" for item in generic)

    bom = [BomPosition(designation="TUBE-SAND-001.02.00", name="Вал", strength_component_class="вал шнека")]
    real = build_strength_registry_from_bom(bom)
    assert real[0].bom_position != "уточнить_по_BOM"


def test_cad_bom_required_before_strength_closure():
    """
    Этап 5/6: без реальной BOM (designation) реестр из build_strength_registry_from_bom
    попросту не создаётся для позиции — а generic-реестр создаётся, но НИ ОДНА его
    позиция не может считаться закрытой без VerificationRecord (это не новое
    поведение — item_is_closed уже это проверяет, здесь подтверждается для
    трубного случая явно).
    """
    generic = build_default_registry()
    shaft_item = next(item for item in generic if item.component_class == "вал шнека")
    closed, problems = item_is_closed(shaft_item, project_revision="0.0.1", input_fingerprint="abc")
    assert closed is False
    assert "не выполнена" in problems[0]

    # Даже если БЫ появилась настоящая BOM-позиция, без VerificationRecord'ов
    # по каждому load case реестр всё равно не закрыт.
    bom = [BomPosition(designation="TUBE-SAND-001.02.00", name="Вал", strength_component_class="вал шнека")]
    real_registry = build_strength_registry_from_bom(bom)
    real_item = real_registry[0]
    uncovered = uncovered_load_cases(real_item, project_revision="0.0.1", input_fingerprint="abc")
    assert set(uncovered) == set(required_load_cases("вал шнека"))


# --- 4. VerificationRecord не даёт PASS без настоящего result_value ----------

def test_verification_record_requires_real_bom_position():
    """
    StrengthItem без реальной BOM-позиции (placeholder "уточнить_по_BOM")
    в принципе не может появиться из build_strength_registry_from_bom() —
    см. test_build_strength_registry_from_bom_uses_real_designations_not_placeholder.
    Здесь дополнительно проверяется, что САМА проверка (VerificationRecord)
    не считается пройденной без числового результата, даже если её
    привязали к позиции с настоящим обозначением.
    """
    bom_position = "TUBE-SAND-001.02.00"
    item = StrengthItem(bom_position=bom_position, component_class="вал шнека", method=VerificationMethod.ANALYTICAL)

    # (а) вообще нет VerificationRecord — не закрыто.
    closed, problems = item_is_closed(item, project_revision="0.0.2", input_fingerprint="fp1")
    assert closed is False

    # (б) VerificationRecord БЕЗ result_value — тоже не закрыто (не "PASS по умолчанию").
    empty_record = VerificationRecord(
        criterion_description="torque", result_value=None, result_unit="Н·м",
        criterion_limit=200.0, criterion_source="ГОСТ 25.021-78",
        computed_by="Инженер И.И.", methodology_version="1.0",
        input_fingerprint="fp1", product_revision="0.0.2",
    )
    item.verifications.append(empty_record)
    assert empty_record.passed() is False
    ok, reasons = empty_record.is_complete_and_valid("0.0.2", "fp1")
    assert ok is False
    assert any("нет числового результата" in r for r in reasons)

    # (в) полноценный VerificationRecord с числом — закрывает конкретно этот load case.
    real_record = VerificationRecord(
        criterion_description="torque", result_value=120.0, result_unit="Н·м",
        criterion_limit=200.0, criterion_source="ГОСТ 25.021-78", safety_factor=1.67,
        computed_by="Инженер И.И.", methodology_version="1.0",
        input_fingerprint="fp1", product_revision="0.0.2",
        reviewed_by="Инженер П.П.",
    )
    item.verifications = [real_record]
    coverage = load_case_coverage(item, project_revision="0.0.2", input_fingerprint="fp1")
    assert coverage["torque"] is True
    # Остальные load case для вала (bending/combined_stress/deflection/critical_speed) всё ещё открыты.
    assert set(uncovered_load_cases(item, "0.0.2", "fp1")) == {
        "bending", "combined_stress", "deflection", "critical_speed",
    }
