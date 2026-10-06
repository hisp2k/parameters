# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from calculator.core.questionnaire import (
    QuestionnaireInput, ConveyorKind, MaterialInput, ProductivityInput, ProductivityUnit,
    GeometryInput, GeometryMode, OperatingProfileInput, Abrasiveness, validate_questionnaire,
)


def _valid_questionnaire() -> QuestionnaireInput:
    return QuestionnaireInput(
        conveyor_kind=ConveyorKind.SHAFTED_TROUGH,
        material=MaterialInput(
            material_name="песок",
            bulk_density_kg_m3=1500.0,
            max_lump_size_mm=5.0,
            is_sorted_material=False,
            abrasiveness=Abrasiveness.MEDIUM,
        ),
        productivity=ProductivityInput(value=10.0, unit=ProductivityUnit.T_H),
        geometry=GeometryInput(mode=GeometryMode.AXIS_LENGTH_ANGLE, working_length_mm=4000.0, incline_deg=5.0),
        profile=OperatingProfileInput(construction_material="Ст3"),
    )


def test_valid_questionnaire_has_no_issues():
    assert validate_questionnaire(_valid_questionnaire()) == []


def test_missing_density_is_flagged():
    q = _valid_questionnaire()
    q.material.bulk_density_kg_m3 = None
    issues = validate_questionnaire(q)
    assert any("плотность" in i for i in issues)


def test_zero_productivity_is_flagged():
    q = _valid_questionnaire()
    q.productivity.value = 0
    issues = validate_questionnaire(q)
    assert any("производительность" in i.lower() for i in issues)


def test_contradictory_geometry_overall_less_than_working_length():
    q = _valid_questionnaire()
    q.geometry.overall_length_mm = 1000.0  # меньше working_length_mm=4000
    issues = validate_questionnaire(q)
    assert any("противоречивая геометрия" in i for i in issues)


def test_incline_out_of_range_is_flagged():
    q = _valid_questionnaire()
    q.geometry.incline_deg = 45.0
    issues = validate_questionnaire(q)
    assert any("вне диапазона" in i for i in issues)


def test_m3_h_without_density_is_flagged():
    q = _valid_questionnaire()
    q.productivity.unit = ProductivityUnit.M3_H
    q.material.bulk_density_kg_m3 = None
    issues = validate_questionnaire(q)
    assert any("перевод в массовую производительность невозможен" in i for i in issues)


def test_unsupported_conveyor_kind_is_flagged_not_silently_computed():
    q = _valid_questionnaire()
    q.conveyor_kind = ConveyorKind.SHAFTLESS
    issues = validate_questionnaire(q)
    assert any("не реализован" in i for i in issues)


def test_geometry_projection_height_mode_resolves_length_and_angle():
    g = GeometryInput(mode=GeometryMode.PROJECTION_HEIGHT, horizontal_projection_mm=3000.0, height_gain_mm=400.0)
    length, angle = g.resolved_length_angle()
    assert length is not None and angle is not None
    assert length > 3000.0
    assert 0 < angle < 20


def test_geometry_coordinates_mode_resolves_length_and_angle():
    g = GeometryInput(
        mode=GeometryMode.COORDINATES,
        load_point_xyz_mm=(0.0, 0.0, 0.0),
        unload_point_xyz_mm=(3000.0, 0.0, 300.0),
    )
    length, angle = g.resolved_length_angle()
    assert length is not None and angle is not None
    assert length > 3000.0
