# -*- coding: utf-8 -*-
"""
Тесты SHAFTED_TUBE (валовый трубчатый шнек, GitHub Issue #3):

1. Геометрический конфликт (угол 35° против высот пола) — на точных цифрах
   эскиза "Тангенциальная песколовка" (DN100, угол 35°, длина 2515 мм по
   оси, высота загрузки 500 мм, высота выгрузки 1500 мм).
2. Инженерное ядро трубного шнека возвращает честные блокеры, а не
   выдуманные числа, и НЕ использует методику желобчатого шнека.
3. Анкета: SHAFTED_TUBE больше не отклоняется validate_questionnaire(), а
   >20° не блокирует её; SHAFTED_TROUGH — поведение не изменилось.
4. Сквозной прогон конвейера (app.create_project) для SHAFTED_TUBE:
   проект создаётся, документы формируются, сохранение/загрузка не падает.
5. ИСПРАВЛЕНИЕ 17.09.2026 (независимая проверка, см. TASK.md): раньше
   `_sketch_questionnaire()` подставляла ФИКТИВНЫЕ 5.0 т/ч (их не было на
   эскизе) и ошибочно трактовала п.5 эскиза ("привод снизу") как требование
   дренажа. Оба дефекта исправлены здесь; добавлены регрессионные тесты,
   чтобы это не повторилось.
"""

import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from calculator.core.questionnaire import (
    QuestionnaireInput, ConveyorKind, MaterialInput, ProductivityInput, ProductivityUnit,
    GeometryInput, GeometryMode, OperatingProfileInput, OptionalDetails, Abrasiveness,
    validate_questionnaire, unsupported_requirements,
)
from calculator.core.tube_engineering import (
    TubeCalcStatus, GeometryScenario, DriveLocation, TubeEngineeringInput, TubeEngineeringInputError,
    check_geometry_conflict, check_drive_location_conflict, compute_tube_engineering_core,
    TubeMethodology, TubeMethodologyResult, UnconfirmedTubeMethodology,
)
from calculator.core.project import Project
from calculator.core.release_gate import evaluate as evaluate_release_gate
from calculator.core.roles import Role
from calculator.app import create_project, QuestionnaireValidationError


# --- эскиз "Тангенциальная песколовка" -------------------------------------

SKETCH_DN_MM = 100.0
SKETCH_ANGLE_DEG = 35.0
SKETCH_LENGTH_ALONG_AXIS_MM = 2515.0
SKETCH_LOAD_HEIGHT_MM = 500.0
SKETCH_UNLOAD_HEIGHT_MM = 1500.0
SKETCH_MATERIAL_NAME = "вода с песком"  # дословно, как в исходных данных — не переименовывать в "ил с песком"


def _sketch_questionnaire() -> QuestionnaireInput:
    """
    Только ПОДТВЕРЖДЁННЫЕ данные эскиза "Тангенциальная песколовка". Никаких
    выдуманных чисел: производительность/плотность/абразивность/крупность —
    неизвестны, поэтому НЕ заполняются (ProductivityInput() без аргументов —
    value=None, unit=None). Расположение привода — из ТЕКСТА эскиза (п.5,
    "привод снизу"); графическая часть эскиза расположение привода не
    подтверждает в этом фикстуре (см. test_drive_text_vs_graphic_conflict
    для случая, когда оба источника заданы и расходятся).
    """
    return QuestionnaireInput(
        conveyor_kind=ConveyorKind.SHAFTED_TUBE,
        material=MaterialInput(material_name=SKETCH_MATERIAL_NAME),
        productivity=ProductivityInput(),  # value=None, unit=None — не подтверждено заказчиком
        geometry=GeometryInput(
            mode=GeometryMode.AXIS_LENGTH_ANGLE,
            working_length_mm=SKETCH_LENGTH_ALONG_AXIS_MM,
            incline_deg=SKETCH_ANGLE_DEG,
            connection_diameter_mm=SKETCH_DN_MM,
            load_height_from_floor_mm=SKETCH_LOAD_HEIGHT_MM,
            unload_height_from_floor_mm=SKETCH_UNLOAD_HEIGHT_MM,
        ),
        profile=OperatingProfileInput(construction_material="Ст3"),
        optional=OptionalDetails(
            is_slurry_mixture=True,  # инженерная интерпретация названия материала, не исходное значение
            drive_location_text=DriveLocation.LOWER_END.value,
            drive_location_text_source="текст эскиза, п.5 ('привод снизу шнекового транспортёра')",
        ),
    )


# --- 1. геометрический конфликт --------------------------------------------

def test_sketch_geometry_is_genuinely_conflicting():
    """
    Угол 35° и длина 2515 мм по оси дают набор высоты ~1442 мм; заявленные
    высоты пола дают ровно 1000 мм. Расхождение ~442 мм — реальное
    несовпадение данных эскиза, оно должно быть обнаружено, а не скрыто.
    """
    report = check_geometry_conflict(
        angle_deg=SKETCH_ANGLE_DEG,
        length_along_axis_mm=SKETCH_LENGTH_ALONG_AXIS_MM,
        load_height_from_floor_mm=SKETCH_LOAD_HEIGHT_MM,
        unload_height_from_floor_mm=SKETCH_UNLOAD_HEIGHT_MM,
    )
    assert report is not None
    expected_from_angle = SKETCH_LENGTH_ALONG_AXIS_MM * math.sin(math.radians(SKETCH_ANGLE_DEG))
    assert math.isclose(report.height_gain_from_angle_mm, expected_from_angle, abs_tol=0.1)
    assert report.height_gain_from_floor_heights_mm == SKETCH_UNLOAD_HEIGHT_MM - SKETCH_LOAD_HEIGHT_MM
    assert report.conflict is True
    assert report.discrepancy_mm is not None and abs(report.discrepancy_mm) > 400
    assert GeometryScenario.SCENARIO_ANGLE.value in report.scenarios
    assert GeometryScenario.SCENARIO_HEIGHTS.value in report.scenarios


def test_consistent_geometry_is_not_flagged_as_conflict():
    # Угол и высоты, которые СОГЛАСОВАНЫ (высота = length*sin(angle)).
    length = 3000.0
    angle = 20.0
    height_gain = length * math.sin(math.radians(angle))
    report = check_geometry_conflict(
        angle_deg=angle, length_along_axis_mm=length,
        load_height_from_floor_mm=500.0,
        unload_height_from_floor_mm=500.0 + height_gain,
    )
    assert report is not None
    assert report.conflict is False


def test_geometry_conflict_returns_none_when_nothing_to_compare():
    report = check_geometry_conflict(
        angle_deg=None, length_along_axis_mm=None,
        load_height_from_floor_mm=None, unload_height_from_floor_mm=None,
    )
    assert report is None


def test_geometry_conflict_rejects_non_finite_input():
    try:
        check_geometry_conflict(
            angle_deg=float("nan"), length_along_axis_mm=1000.0,
            load_height_from_floor_mm=0.0, unload_height_from_floor_mm=100.0,
        )
        assert False, "ожидалась TubeEngineeringInputError"
    except TubeEngineeringInputError:
        pass


# --- 2. инженерное ядро трубного шнека -------------------------------------

def test_tube_core_never_reuses_trough_incline_limit():
    """35° не должно быть отвергнуто как 'вне методики 20°' — это НЕ ошибка ввода здесь."""
    result = compute_tube_engineering_core(TubeEngineeringInput(
        connection_diameter_mm=SKETCH_DN_MM, incline_deg=SKETCH_ANGLE_DEG,
        working_length_mm=SKETCH_LENGTH_ALONG_AXIS_MM,
        load_height_from_floor_mm=SKETCH_LOAD_HEIGHT_MM, unload_height_from_floor_mm=SKETCH_UNLOAD_HEIGHT_MM,
    ))
    assert not any("20°" in b and "методик" in b for b in result.blockers if "не покрыт" in b)
    assert result.status == TubeCalcStatus.BLOCKED


def test_tube_core_never_copies_dn_into_body_diameter():
    result = compute_tube_engineering_core(TubeEngineeringInput(connection_diameter_mm=SKETCH_DN_MM))
    assert result.diameter_mm is None
    assert result.connection_diameter_mm == SKETCH_DN_MM
    assert any("НЕ диаметр корпуса" in b or "не диаметр корпуса" in b.lower() for b in result.blockers)


def test_tube_core_does_not_invent_unknown_material_properties():
    result = compute_tube_engineering_core(TubeEngineeringInput(
        material_name="ил с песком", bulk_density_kg_m3=None, abrasiveness=None, max_lump_size_mm=None,
    ))
    assert result.shaft_power_kw is None
    assert result.rotation_speed_rpm is None
    assert result.motor_power_kw is None
    assert any("плотность" in b.lower() for b in result.blockers)
    assert any("абразивность" in b.lower() for b in result.blockers)
    assert any("куска" in b.lower() or "включения" in b.lower() for b in result.blockers)


def test_tube_core_flags_geometry_conflict_as_blocker():
    result = compute_tube_engineering_core(TubeEngineeringInput(
        connection_diameter_mm=SKETCH_DN_MM, incline_deg=SKETCH_ANGLE_DEG,
        working_length_mm=SKETCH_LENGTH_ALONG_AXIS_MM,
        load_height_from_floor_mm=SKETCH_LOAD_HEIGHT_MM, unload_height_from_floor_mm=SKETCH_UNLOAD_HEIGHT_MM,
    ))
    assert result.geometry_conflict is not None and result.geometry_conflict.conflict
    assert any("не самосогласована" in b for b in result.blockers)


def test_tube_core_converts_productivity_units_without_density():
    """
    Числа здесь СИНТЕТИЧЕСКИЕ (проверка арифметики перевода единиц), а НЕ
    значения эскиза — на реальном эскизе производительность не указана
    (см. test_no_fake_productivity_in_sketch_questionnaire ниже).
    """
    result = compute_tube_engineering_core(TubeEngineeringInput(
        productivity_value=5.0, productivity_unit="т/ч",
    ))
    assert result.productivity_required_t_per_h == 5.0

    result_kg = compute_tube_engineering_core(TubeEngineeringInput(
        productivity_value=500.0, productivity_unit="кг/ч",
    ))
    assert result_kg.productivity_required_t_per_h == 0.5


def test_tube_core_slurry_mixture_without_concentration_is_blocked():
    result = compute_tube_engineering_core(TubeEngineeringInput(
        is_slurry_mixture=True, solids_concentration_percent=None,
    ))
    assert any("двухфазная смесь" in b or "концентрация" in b for b in result.blockers)


def test_tube_core_drain_requirement_is_surfaced_as_warning_not_silently_dropped():
    result = compute_tube_engineering_core(TubeEngineeringInput(drain_connection_required=True))
    assert any("дренаж" in w.lower() for w in result.warnings)


# --- 2а. регрессия 17.09.2026: НЕ выдумывать производительность ------------

def test_no_fake_productivity_in_sketch_questionnaire():
    """На эскизе производительность не указана — фикстура не должна её подставлять."""
    q = _sketch_questionnaire()
    assert q.productivity.value is None
    assert q.productivity.unit is None


def test_tube_core_blocks_on_missing_productivity_no_fake_number():
    result = compute_tube_engineering_core(TubeEngineeringInput(
        productivity_value=None, productivity_unit=None,
    ))
    assert result.productivity_required_t_per_h is None
    assert any("Требуемая производительность не задана" in b for b in result.blockers)


def test_sketch_questionnaire_end_to_end_has_no_fake_productivity_value():
    """
    Сквозной прогон (как в проекте TUBE-SAND-001): фиктивные 5.0 т/ч из
    предыдущей реализации не должны просочиться ни в вопросник, ни в
    результат расчёта, ни в блокер о производительности.
    """
    result = compute_tube_engineering_core(TubeEngineeringInput(
        connection_diameter_mm=SKETCH_DN_MM, incline_deg=SKETCH_ANGLE_DEG,
        working_length_mm=SKETCH_LENGTH_ALONG_AXIS_MM,
        load_height_from_floor_mm=SKETCH_LOAD_HEIGHT_MM, unload_height_from_floor_mm=SKETCH_UNLOAD_HEIGHT_MM,
        material_name=SKETCH_MATERIAL_NAME,
        productivity_value=None, productivity_unit=None,
    ))
    assert result.productivity_required_t_per_h is None
    assert any("Требуемая производительность не задана" in b for b in result.blockers)
    assert not any("5.0" in b or "5 т/ч" in b for b in result.blockers)


# --- 2б. регрессия 17.09.2026: наименование среды сохраняется дословно -----

def test_source_material_name_preserved():
    q = _sketch_questionnaire()
    assert q.material.material_name == "вода с песком"
    result = compute_tube_engineering_core(TubeEngineeringInput(
        material_name=q.material.material_name, bulk_density_kg_m3=None,
    ))
    density_blocker = next(b for b in result.blockers if "плотность" in b.lower())
    assert "вода с песком" in density_blocker
    assert "ил с песком" not in density_blocker


# --- 2в. регрессия 17.09.2026: расположение привода — не дренаж ------------

def test_lower_drive_requirement_preserved():
    """Текстовое требование 'привод снизу' сохраняется как DriveLocation.LOWER_END, а не теряется."""
    result = compute_tube_engineering_core(TubeEngineeringInput(
        drive_location_text=DriveLocation.LOWER_END.value,
        drive_location_text_source="текст эскиза, п.5",
    ))
    assert result.drive_location_conflict is not None
    assert result.drive_location_conflict.text_location == DriveLocation.LOWER_END
    assert result.drive_location_conflict.text_source == "текст эскиза, п.5"
    # Только один источник задан — сравнивать не с чем, конфликта нет и блокера нет.
    assert result.drive_location_conflict.conflict is False
    assert not any("Расположение привода не самосогласовано" in b for b in result.blockers)


def test_drive_text_vs_graphic_conflict():
    """
    Текст эскиза (п.5): "привод снизу". Графика эскиза: мотор-редуктор у
    верхнего торца. Это реальное противоречие — ни один вариант не
    выбирается автоматически, выпуск блокируется.
    """
    report = check_drive_location_conflict(
        text_location=DriveLocation.LOWER_END, text_source="текст эскиза, п.5",
        graphic_location=DriveLocation.UPPER_END, graphic_source="графика эскиза",
    )
    assert report is not None
    assert report.conflict is True

    result = compute_tube_engineering_core(TubeEngineeringInput(
        drive_location_text=DriveLocation.LOWER_END.value,
        drive_location_text_source="текст эскиза, п.5",
        drive_location_graphic=DriveLocation.UPPER_END.value,
        drive_location_graphic_source="графика эскиза",
    ))
    assert result.drive_location_conflict is not None and result.drive_location_conflict.conflict
    assert any("Расположение привода не самосогласовано" in b for b in result.blockers)


def test_drain_not_inferred_from_drive_requirement():
    """
    Требование "привод снизу" НЕ должно порождать предупреждение о дренаже —
    это была реальная ошибка предыдущего прогона (п.5 эскиза спутан с
    дренажным патрубком).
    """
    result = compute_tube_engineering_core(TubeEngineeringInput(
        drive_location_text=DriveLocation.LOWER_END.value,
        drive_location_text_source="текст эскиза, п.5",
        drain_connection_required=None,  # не подтверждено отдельно — не выводится из drive_location
    ))
    assert not any("дренаж" in w.lower() for w in result.warnings)
    assert not any("дренаж" in b.lower() for b in result.blockers)


def test_sketch_questionnaire_has_no_drain_requirement_inferred_from_point_5():
    q = _sketch_questionnaire()
    assert q.optional.drain_connection_required is None
    assert q.optional.drive_location_text == DriveLocation.LOWER_END.value


# --- 3. анкета: SHAFTED_TUBE больше не отклоняется -------------------------

def test_sketch_questionnaire_passes_validation_despite_unknown_material():
    q = _sketch_questionnaire()
    issues = validate_questionnaire(q)
    assert issues == [], issues


def test_shafted_tube_steep_angle_not_rejected_by_range_check():
    q = _sketch_questionnaire()
    issues = validate_questionnaire(q)
    assert not any("вне диапазона" in i for i in issues)


def test_shafted_tube_is_flagged_in_unsupported_requirements_but_not_rejected():
    q = _sketch_questionnaire()
    warnings = unsupported_requirements(q)
    assert any("валовый_трубчатый" in w for w in warnings)


def test_shafted_trough_behaviour_is_unchanged_missing_density_still_blocks():
    q = QuestionnaireInput(
        conveyor_kind=ConveyorKind.SHAFTED_TROUGH,
        material=MaterialInput(material_name="песок"),
        productivity=ProductivityInput(value=5.0, unit=ProductivityUnit.T_H),
        geometry=GeometryInput(mode=GeometryMode.AXIS_LENGTH_ANGLE, working_length_mm=3000.0, incline_deg=5.0),
        profile=OperatingProfileInput(construction_material="Ст3"),
    )
    issues = validate_questionnaire(q)
    assert any("плотность" in i.lower() for i in issues)


def test_shafted_trough_angle_over_20_is_still_rejected():
    q = QuestionnaireInput(
        conveyor_kind=ConveyorKind.SHAFTED_TROUGH,
        material=MaterialInput(
            material_name="песок", bulk_density_kg_m3=1500.0, max_lump_size_mm=5.0,
            abrasiveness=Abrasiveness.MEDIUM,
        ),
        productivity=ProductivityInput(value=5.0, unit=ProductivityUnit.T_H),
        geometry=GeometryInput(mode=GeometryMode.AXIS_LENGTH_ANGLE, working_length_mm=3000.0, incline_deg=35.0),
        profile=OperatingProfileInput(construction_material="Ст3"),
    )
    issues = validate_questionnaire(q)
    assert any("вне диапазона" in i for i in issues)


def test_shaftless_is_still_rejected_not_silently_accepted():
    q = _sketch_questionnaire()
    q.conveyor_kind = ConveyorKind.SHAFTLESS
    issues = validate_questionnaire(q)
    assert any("не реализован" in i for i in issues)


def test_shafted_trough_missing_productivity_is_still_rejected():
    """
    ProductivityInput стал Optional (регрессия 17.09.2026 для SHAFTED_TUBE),
    но для SHAFTED_TROUGH производительность остаётся ЖЁСТКО обязательной —
    поведение желобчатого шнека не должно было измениться ни на байт.
    """
    q = QuestionnaireInput(
        conveyor_kind=ConveyorKind.SHAFTED_TROUGH,
        material=MaterialInput(
            material_name="песок", bulk_density_kg_m3=1500.0, max_lump_size_mm=5.0,
            abrasiveness=Abrasiveness.MEDIUM,
        ),
        productivity=ProductivityInput(),  # value=None, unit=None
        geometry=GeometryInput(mode=GeometryMode.AXIS_LENGTH_ANGLE, working_length_mm=3000.0, incline_deg=5.0),
        profile=OperatingProfileInput(construction_material="Ст3"),
    )
    issues = validate_questionnaire(q)
    assert any("не указана требуемая производительность" in i.lower() for i in issues)


# --- 4. сквозной прогон конвейера (создание проекта) ------------------------

def test_create_project_for_sketch_questionnaire_runs_and_returns_blockers():
    q = _sketch_questionnaire()
    with tempfile.TemporaryDirectory() as tmp:
        project, outcome = create_project(
            q, project_name="Пилот — TUBE-SAND-001", customer="Тех-Аэро (внутренний пилот)",
            designation="TUBE-SAND-001-test", data_dir=Path(tmp),
        )
        assert project.engineering_result is None  # желобчатая методика НЕ применялась
        assert outcome.tube_result is not None
        assert outcome.tube_result.status == TubeCalcStatus.BLOCKED
        assert len(outcome.tube_result.blockers) > 0
        assert outcome.project_path.exists()
        assert outcome.html_path.exists()
        assert outcome.pdf_path.exists()
        # Привод/технология не запускались для трубного шнека — честно, без выдуманных чисел.
        assert outcome.drive_result is None
        assert outcome.technology_package is None
        assert not project.drive_selection.done
        assert not project.technology.done


def test_project_save_and_load_roundtrip_preserves_tube_result():
    q = _sketch_questionnaire()
    with tempfile.TemporaryDirectory() as tmp:
        project, outcome = create_project(
            q, project_name="Пилот — TUBE-SAND-001", customer="Тех-Аэро (внутренний пилот)",
            designation="TUBE-SAND-001-roundtrip", data_dir=Path(tmp),
        )
        reloaded = Project.load(outcome.project_path)
        assert reloaded.tube_engineering_result is not None
        assert reloaded.tube_engineering_result.status == TubeCalcStatus.BLOCKED
        assert reloaded.tube_engineering_result.geometry_conflict.conflict is True
        assert reloaded.engineering_result is None
        assert reloaded.is_calc_stale() is False


def test_tube_fields_preserved_in_json():
    """
    Issue #3, продолжение 17.09.2026: поля, добавленные для веб-формы/анкеты
    (connection_diameter_mm, load/unload_height_from_floor_mm, is_slurry_mixture,
    solids_concentration_percent, drive_location_*, drain_connection_required)
    должны пережить сохранение/загрузку проекта дословно, не только "не упасть".
    """
    q = _sketch_questionnaire()
    q.optional.solids_concentration_percent = 12.5
    q.optional.duty_hours_per_day = 16.0
    q.optional.starts_per_day = 6
    q.optional.corrosion_requirements = "нержавеющая сталь по контакту со средой"
    with tempfile.TemporaryDirectory() as tmp:
        project, outcome = create_project(
            q, project_name="Пилот — TUBE-SAND-001", customer="Тех-Аэро (внутренний пилот)",
            designation="TUBE-SAND-001-fields", data_dir=Path(tmp),
        )
        reloaded = Project.load(outcome.project_path)
        rq = reloaded.questionnaire
        assert rq.geometry.connection_diameter_mm == SKETCH_DN_MM
        assert rq.geometry.load_height_from_floor_mm == SKETCH_LOAD_HEIGHT_MM
        assert rq.geometry.unload_height_from_floor_mm == SKETCH_UNLOAD_HEIGHT_MM
        assert rq.optional.is_slurry_mixture is True
        assert rq.optional.solids_concentration_percent == 12.5
        assert rq.optional.duty_hours_per_day == 16.0
        assert rq.optional.starts_per_day == 6
        assert rq.optional.corrosion_requirements == "нержавеющая сталь по контакту со средой"
        assert rq.optional.drive_location_text == DriveLocation.LOWER_END.value
        assert rq.optional.drive_location_text_source == "текст эскиза, п.5 ('привод снизу шнекового транспортёра')"
        assert rq.optional.drain_connection_required is None
        assert rq.material.material_name == "вода с песком"
        assert reloaded.tube_engineering_result.drive_location_conflict is not None
        assert reloaded.tube_engineering_result.drive_location_conflict.text_location == DriveLocation.LOWER_END


def test_no_fake_tube_dimensions():
    """
    Ни при каких входных данных compute_tube_engineering_core() не должен
    придумывать диаметр/шаг/обороты/мощность/момент — их вычисление зависит
    от неподтверждённой методики для угла ~35° (BLOCKED, а не число).
    """
    result = compute_tube_engineering_core(TubeEngineeringInput(
        connection_diameter_mm=SKETCH_DN_MM, incline_deg=SKETCH_ANGLE_DEG,
        working_length_mm=SKETCH_LENGTH_ALONG_AXIS_MM,
        load_height_from_floor_mm=SKETCH_LOAD_HEIGHT_MM, unload_height_from_floor_mm=SKETCH_UNLOAD_HEIGHT_MM,
        material_name=SKETCH_MATERIAL_NAME, bulk_density_kg_m3=1200.0, abrasiveness="средняя",
        max_lump_size_mm=2.0, productivity_value=5.0, productivity_unit="т/ч",
    ))
    # Даже когда ВСЁ остальное задано (плотность/абразивность/крупность/производительность),
    # диаметр корпуса/шаг/обороты/момент/мощность остаются None — нет методики для 35°.
    assert result.diameter_mm is None
    assert result.step_mm is None
    assert result.rotation_speed_rpm is None
    assert result.shaft_power_kw is None
    assert result.motor_power_kw is None
    assert result.status == TubeCalcStatus.BLOCKED
    assert any("методика" in b.lower() and "35" in b for b in result.blockers)


def test_no_fake_tube_drive():
    """Без ЯВНОГО ввода расположения привода ни один вариант не подставляется по умолчанию."""
    result = compute_tube_engineering_core(TubeEngineeringInput(
        connection_diameter_mm=SKETCH_DN_MM, incline_deg=SKETCH_ANGLE_DEG,
        working_length_mm=SKETCH_LENGTH_ALONG_AXIS_MM,
    ))
    assert result.drive_location_conflict is None
    assert not any("расположение привода" in b.lower() for b in result.blockers)

    q = QuestionnaireInput(
        conveyor_kind=ConveyorKind.SHAFTED_TUBE,
        material=MaterialInput(material_name="вода с песком"),
        productivity=ProductivityInput(),
        geometry=GeometryInput(mode=GeometryMode.AXIS_LENGTH_ANGLE, working_length_mm=2515.0, incline_deg=35.0),
        profile=OperatingProfileInput(construction_material="Ст3"),
    )
    assert q.optional.drive_location_text is None
    assert q.optional.drive_location_graphic is None


def test_default_methodology_is_unconfirmed_and_matches_no_methodology_arg():
    """
    compute_tube_engineering_core() без methodology= и с явным
    methodology=UnconfirmedTubeMethodology() должны давать одинаковый
    результат — подтверждает, что UnconfirmedTubeMethodology() реально
    подставляется по умолчанию, а не просто существует как класс.
    """
    inp = TubeEngineeringInput(
        connection_diameter_mm=SKETCH_DN_MM, incline_deg=SKETCH_ANGLE_DEG,
        working_length_mm=SKETCH_LENGTH_ALONG_AXIS_MM,
        load_height_from_floor_mm=SKETCH_LOAD_HEIGHT_MM, unload_height_from_floor_mm=SKETCH_UNLOAD_HEIGHT_MM,
        material_name=SKETCH_MATERIAL_NAME, bulk_density_kg_m3=1200.0, abrasiveness="средняя",
        max_lump_size_mm=2.0, productivity_value=5.0, productivity_unit="т/ч",
    )
    default_result = compute_tube_engineering_core(inp)
    explicit_result = compute_tube_engineering_core(inp, methodology=UnconfirmedTubeMethodology())
    assert default_result.status == explicit_result.status == TubeCalcStatus.BLOCKED
    assert default_result.blockers == explicit_result.blockers
    assert default_result.methodology_name == explicit_result.methodology_name == "методика_не_подтверждена"


def test_pluggable_methodology_fills_core_parameters_without_touching_project_or_app():
    """
    Ключевая проверка этапа "стратегия методики" (17.09.2026): если завтра
    появится подтверждённая методика для трубного шнека на ~35°, она
    подключается через параметр methodology=... к ТОЙ ЖЕ функции
    compute_tube_engineering_core(), которую уже вызывают app.py/webapp —
    им не нужно меняться. Здесь методика — тестовый двойник (не настоящая
    инженерная методика), только чтобы доказать механизм подключения.
    """

    class _FakeConfirmedMethodology(TubeMethodology):
        name = "тестовая_подтверждённая_методика"
        version = "1.0-test"

        def compute(self, inp: TubeEngineeringInput) -> TubeMethodologyResult:
            return TubeMethodologyResult(
                resolved=True,
                diameter_mm=219.0, step_mm=180.0, rotation_speed_rpm=45.0,
                shaft_power_kw=3.2, motor_power_kw=4.0, motor_selection_ok=True,
                torque_nm=680.0, starting_torque_nm=1020.0, gear_ratio=25.0,
                bearing_load_radial_n=4200.0, bearing_load_axial_n=1500.0, mass_kg=310.0,
                productivity_achievable_t_per_h=5.2, requirement_met=True,
            )

    # ВАЖНО: высоты пола здесь намеренно НЕ заданы (в отличие от реального
    # эскиза TUBE-SAND-001, где 35°/2515мм расходятся с высотами 500/1500мм) —
    # иначе честный geometry_conflict-блокер остался бы независимо от
    # методики, и статус не мог бы дойти до COMPUTED. Этот тест проверяет
    # ТОЛЬКО механизм подключения методики, а не реальные данные сценария.
    inp = TubeEngineeringInput(
        connection_diameter_mm=SKETCH_DN_MM, incline_deg=SKETCH_ANGLE_DEG,
        working_length_mm=SKETCH_LENGTH_ALONG_AXIS_MM,
        material_name=SKETCH_MATERIAL_NAME, bulk_density_kg_m3=1200.0, abrasiveness="средняя",
        max_lump_size_mm=2.0, productivity_value=5.0, productivity_unit="т/ч",
    )
    result = compute_tube_engineering_core(inp, methodology=_FakeConfirmedMethodology())

    assert result.status == TubeCalcStatus.COMPUTED
    assert result.diameter_mm == 219.0
    assert result.torque_nm == 680.0
    assert result.starting_torque_nm == 1020.0
    assert result.gear_ratio == 25.0
    assert result.bearing_load_radial_n == 4200.0
    assert result.mass_kg == 310.0
    assert result.methodology_name == "тестовая_подтверждённая_методика"
    assert not any("методика" in b.lower() and "отсутствует" in b.lower() for b in result.blockers)


def test_pluggable_methodology_that_still_lacks_data_stays_blocked_not_faked():
    """Методика подключена, но САМА решает, что данных не хватает — статус остаётся BLOCKED, числа не подставляются."""

    class _FakeMethodologyStillMissingData(TubeMethodology):
        name = "тестовая_методика_неполные_данные"
        version = "0.1-test"

        def compute(self, inp: TubeEngineeringInput) -> TubeMethodologyResult:
            return TubeMethodologyResult(
                resolved=False,
                blockers=["Тестовая методика: недостаточно данных о твёрдой фазе для расчёта диаметра."],
            )

    result = compute_tube_engineering_core(
        TubeEngineeringInput(
            connection_diameter_mm=SKETCH_DN_MM, incline_deg=SKETCH_ANGLE_DEG,
            working_length_mm=SKETCH_LENGTH_ALONG_AXIS_MM,
            bulk_density_kg_m3=1200.0, abrasiveness="средняя", max_lump_size_mm=2.0,
            productivity_value=5.0, productivity_unit="т/ч",
        ),
        methodology=_FakeMethodologyStillMissingData(),
    )
    assert result.status == TubeCalcStatus.BLOCKED
    assert result.diameter_mm is None
    assert any("недостаточно данных о твёрдой фазе" in b for b in result.blockers)


def test_release_gate_reports_tube_specific_blockers_not_generic_message():
    q = _sketch_questionnaire()
    with tempfile.TemporaryDirectory() as tmp:
        project, _outcome = create_project(
            q, project_name="Пилот — TUBE-SAND-001", customer="Тех-Аэро (внутренний пилот)",
            designation="TUBE-SAND-001-gate", data_dir=Path(tmp),
        )
        reasons = evaluate_release_gate(project, requesting_role=Role.HEAD)
        assert any("трубного шнека заблокировано" in r for r in reasons)


def test_changing_questionnaire_invalidates_tube_result_same_as_trough():
    q = _sketch_questionnaire()
    with tempfile.TemporaryDirectory() as tmp:
        project, _outcome = create_project(
            q, project_name="Пилот — TUBE-SAND-001", customer="Тех-Аэро (внутренний пилот)",
            designation="TUBE-SAND-001-invalidate", data_dir=Path(tmp),
        )
        assert project.tube_engineering_result is not None
        q2 = _sketch_questionnaire()
        q2.productivity.value = 9.0
        invalidated = project.set_questionnaire(q2, reason="тест изменения анкеты")
        assert invalidated is True
        assert project.tube_engineering_result is None
