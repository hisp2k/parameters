# -*- coding: utf-8 -*-
"""
Первый работающий сценарий (раздел 3, пункт 6 задания) и общий расчётный
конвейер, которым пользуются и CLI (`run()`/`__main__`), и веб-интерфейс
(раздел 2 задания, `calculator/webapp/`):

    ввод -> проверка данных -> предварительная компоновка (инженерный расчёт)
    -> требования к приводу -> технология -> сохранение проекта ->
    предварительный лист согласования (HTML + PDF)

Запуск CLI:
    cd calculator
    python3 app.py                      # встроенный пример входных данных
    python3 app.py путь/к/input.json    # свои входные данные (см. example_input.json)

ИСПРАВЛЕНИЕ (раздел 2 задания — веб-интерфейс не должен изобретать свой
собственный путь расчёта): раньше вся эта цепочка была зашита внутри одной
функции `run()`, которую мог вызвать только CLI-сценарий (создание НОВОГО
проекта). Теперь расчётная часть вынесена в `recompute_and_save()` — единую
точку для (пере)расчёта уже существующего `Project` (с уже установленной
анкетой), которой пользуются и `create_project()` (для нового проекта), и
`calculator/webapp/pipeline.py` (для редактирования анкеты существующего
проекта через веб-форму) — так что веб-интерфейс не может разойтись с
CLI-сценарием в том, как считаются диаметр/шаг/мощность/требования привода.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # чтобы calculator.* импортировался

from calculator.core.questionnaire import (
    QuestionnaireInput, ConveyorKind, MaterialInput, ProductivityInput, ProductivityUnit,
    GeometryInput, GeometryMode, OperatingProfileInput, OptionalDetails, Abrasiveness,
    validate_questionnaire, unsupported_requirements,
)
from calculator.core.screw_engineering import (
    ScrewEngineeringInput, ScrewEngineeringResult, compute_engineering_core, EngineeringInputError,
)
from calculator.core.tube_engineering import (
    TubeEngineeringInput, TubeEngineeringResult, compute_tube_engineering_core, TubeEngineeringInputError,
)
from calculator.core.project import Project
from calculator.core.roles import Role
from calculator.core.release_gate import evaluate as evaluate_release_gate
from calculator.core.drive_selection import select_drive, DriveSelectionResult
from calculator.core.parameters import ParamStatus
from calculator.core.technology import build_default_technology_package, TechnologyPackage
from calculator.documents.agreement_sheet import build_agreement_sheet_data, render_html, build_pdf

DATA_DIR = Path(__file__).resolve().parent / "data"


class QuestionnaireValidationError(Exception):
    """Раздел 21: анкета не прошла базовую проверку — расчёт не запускается."""

    def __init__(self, issues: list[str]):
        super().__init__("; ".join(issues) or "анкета не прошла проверку")
        self.issues = issues


@dataclasses.dataclass
class PipelineOutcome:
    """
    Всё, что произвёл один прогон конвейера расчёта — для печати (CLI) или
    отображения (веб).

    ИСПРАВЛЕНИЕ (Issue #3 — SHAFTED_TUBE): раньше engineering_result/
    drive_result/technology_package были обязательными (только для желобчатого
    шнека). Для трубного шнека подбор привода и технология СОЗНАТЕЛЬНО не
    выполняются (нет диаметра/шага/мощности — их вычисление заблокировано,
    см. core/tube_engineering.py), поэтому эти три поля стали Optional
    (None для трубного расчёта), а `tube_result` заполняется только для
    SHAFTED_TUBE. Для SHAFTED_TROUGH поведение не изменилось ни на байт —
    engineering_result/drive_result/technology_package всегда заполнены.
    """

    unsupported: list[str]
    project_path: Path
    html_path: Path
    pdf_path: Path
    technology_path: Path
    engineering_result: Optional[ScrewEngineeringResult] = None
    drive_result: Optional[DriveSelectionResult] = None
    technology_package: Optional[TechnologyPackage] = None
    tube_result: Optional[TubeEngineeringResult] = None


def example_questionnaire() -> QuestionnaireInput:
    """
    Пример на реальном порядке величин заказа №2377 (Stage 10, ветка
    claude/director-parametric-pilot): длина 3000 мм, диаметр шнека 200 мм —
    но производительность и плотность здесь ПРИДУМАНЫ для иллюстрации
    (как и в исходном черновике Stage 12), это не перепроверка заказа.
    """
    return QuestionnaireInput(
        conveyor_kind=ConveyorKind.SHAFTED_TROUGH,
        material=MaterialInput(
            material_name="иллюстративный сыпучий груз (не из реального заказа)",
            bulk_density_kg_m3=700.0,
            max_lump_size_mm=15.0,
            is_sorted_material=False,
            abrasiveness=Abrasiveness.MEDIUM,
        ),
        productivity=ProductivityInput(value=5.0, unit=ProductivityUnit.T_H),
        geometry=GeometryInput(
            mode=GeometryMode.AXIS_LENGTH_ANGLE,
            working_length_mm=3000.0,
            incline_deg=0.0,
        ),
        profile=OperatingProfileInput(
            duty_mode="нормальный",
            environment="цех, без агрессивной среды",
            construction_material="Ст3",
            accepted_defaults=["duty_mode=нормальный (по умолчанию)", "environment (по умолчанию)"],
        ),
    )


def load_questionnaire_from_json(path: Path) -> QuestionnaireInput:
    """
    ИСПРАВЛЕНИЕ (раздел 1.Г задания — "потеря входных данных"): раньше эта
    функция не читала ключ "optional" из входного JSON вообще, поэтому
    OptionalDetails всегда оставался пустым по умолчанию — "пуск под
    нагрузкой" и "реверс" из входного файла молча терялись, даже если
    пользователь их явно указал. Теперь секция "optional" читается и
    восстанавливается полностью, как и все остальные секции.
    """
    d = json.loads(path.read_text(encoding="utf-8"))
    material_d = dict(d["material"])
    material_d["abrasiveness"] = (
        Abrasiveness(material_d["abrasiveness"]) if material_d.get("abrasiveness") else None
    )
    productivity_d = d.get("productivity") or {}
    return QuestionnaireInput(
        conveyor_kind=ConveyorKind(d["conveyor_kind"]),
        material=MaterialInput(**material_d),
        productivity=ProductivityInput(
            value=productivity_d.get("value"),
            unit=ProductivityUnit(productivity_d["unit"]) if productivity_d.get("unit") else None,
        ),
        geometry=GeometryInput(**{**d["geometry"], "mode": GeometryMode(d["geometry"]["mode"])}),
        profile=OperatingProfileInput(**d.get("profile", {})),
        optional=OptionalDetails(**d.get("optional", {})),
        forced_diameter_mm=d.get("forced_diameter_mm"),
        forced_step_mm=d.get("forced_step_mm"),
    )


def recompute_and_save(project: Project, data_dir: Path = DATA_DIR) -> PipelineOutcome:
    """
    (Пере)считать инженерное ядро, требования к приводу и технологию для
    проекта, У КОТОРОГО УЖЕ УСТАНОВЛЕНА (и провалидирована вызывающим кодом)
    анкета (`project.questionnaire`), затем сохранить проект и документы.

    Не валидирует анкету заново — это обязанность вызывающего кода (см.
    `create_project()` ниже и `webapp/pipeline.py`), потому что валидация
    должна произойти ДО `project.set_questionnaire()`: иначе невалидное
    редактирование анкеты уже успело бы поднять ревизию и аннулировать
    расчёт существующего проекта прежде, чем мы узнаем, что анкета плоха.
    """
    questionnaire = project.questionnaire
    if questionnaire is None:
        raise ValueError(
            "recompute_and_save() требует project.questionnaire — сначала вызовите "
            "project.set_questionnaire(...)."
        )

    unsupported = unsupported_requirements(questionnaire)

    result: Optional[ScrewEngineeringResult] = None
    drive_result = None
    tech_package = None
    tube_result: Optional[TubeEngineeringResult] = None

    if questionnaire.conveyor_kind == ConveyorKind.SHAFTED_TUBE:
        # Issue #3 — ветка ВАЛОВОГО ТРУБЧАТОГО шнека: отдельная методика
        # (core/tube_engineering.py), НЕ желобчатая (раздел "не использовать
        # методику желобчатого шнека для угла 35°"). Подбор привода и
        # технология здесь сознательно НЕ запускаются — им нужны диаметр/шаг/
        # мощность, а инженерное ядро трубного шнека их честно не вычисляет
        # (см. tube_engineering_result.blockers), а не подставляет фиктивные.
        length, angle = questionnaire.geometry.resolved_length_angle()
        tube_result = compute_tube_engineering_core(TubeEngineeringInput(
            connection_diameter_mm=questionnaire.geometry.connection_diameter_mm,
            incline_deg=angle,
            working_length_mm=length,
            load_height_from_floor_mm=questionnaire.geometry.load_height_from_floor_mm,
            unload_height_from_floor_mm=questionnaire.geometry.unload_height_from_floor_mm,
            material_name=questionnaire.material.material_name,
            bulk_density_kg_m3=questionnaire.material.bulk_density_kg_m3,
            max_lump_size_mm=questionnaire.material.max_lump_size_mm,
            abrasiveness=(
                questionnaire.material.abrasiveness.value if questionnaire.material.abrasiveness else None
            ),
            is_slurry_mixture=bool(questionnaire.optional.is_slurry_mixture),
            solids_concentration_percent=questionnaire.optional.solids_concentration_percent,
            productivity_value=questionnaire.productivity.value,
            productivity_unit=(
                questionnaire.productivity.unit.value if questionnaire.productivity.unit is not None else None
            ),  # productivity.value/unit теперь Optional (исправлено 17.09.2026) — производительность
            # для SHAFTED_TUBE честно может быть неизвестна, не подставляется фиктивным числом
            drain_connection_required=questionnaire.optional.drain_connection_required,
            drive_location_text=questionnaire.optional.drive_location_text,
            drive_location_text_source=questionnaire.optional.drive_location_text_source,
            drive_location_graphic=questionnaire.optional.drive_location_graphic,
            drive_location_graphic_source=questionnaire.optional.drive_location_graphic_source,
        ))  # может выбросить TubeEngineeringInputError на нечисловые/NaN/нераспознанные входные данные

        project.record_tube_engineering_result(tube_result)
        project.warnings_log.extend(unsupported)

        project.drive_selection.invalidate(
            "подбор привода не запускался: диаметр/обороты/мощность не вычислены — инженерное "
            "ядро трубного шнека заблокировано (см. tube_engineering_result.blockers)"
        )
        project.technology.invalidate(
            "технологический пакет не построен: нет диаметра/шага корпуса трубного шнека — "
            "инженерное ядро заблокировано (см. tube_engineering_result.blockers)"
        )
    else:
        length, angle = questionnaire.geometry.resolved_length_angle()
        result = compute_engineering_core(ScrewEngineeringInput(
            productivity_value=questionnaire.productivity.value,
            productivity_unit=questionnaire.productivity.unit.value,
            bulk_density_kg_m3=questionnaire.material.bulk_density_kg_m3,
            max_lump_size_mm=questionnaire.material.max_lump_size_mm,
            is_sorted_material=questionnaire.material.is_sorted_material,
            abrasiveness=questionnaire.material.abrasiveness.value,
            working_length_mm=length,
            incline_deg=angle,
            forced_diameter_mm=questionnaire.forced_diameter_mm,
            forced_step_mm=questionnaire.forced_step_mm,
        ))  # может выбросить EngineeringInputError — вызывающий код решает, как это показать

        project.record_engineering_result(result)
        project.warnings_log.extend(unsupported)

        drive_result = select_drive(result, questionnaire)  # без каталога -> только требования, раздел 11
        req = drive_result.requirement
        project.warnings_log.extend(drive_result.warnings)

        drive_source = "core.drive_selection.compute_requirement (черновой ориентир, не подтверждено поставщиком)"
        project.parameters.put("drive_required_power_kw", req.required_power_kw, "кВт", drive_source,
                                ParamStatus.CALCULATED_PRELIMINARY, "system")
        project.parameters.put("drive_running_torque_nm", req.running_torque_nm, "Н·м", drive_source,
                                ParamStatus.CALCULATED_PRELIMINARY, "system")
        project.parameters.put("drive_starting_torque_nm", req.starting_torque_nm, "Н·м", drive_source,
                                ParamStatus.CALCULATED_PRELIMINARY, "system")
        project.parameters.put("drive_required_gear_ratio", req.required_gear_ratio, "", drive_source,
                                ParamStatus.CALCULATED_PRELIMINARY, "system")
        # ЧЕСТНАЯ ГРАНИЦА: модуль project.drive_selection НЕ помечается done=True здесь —
        # это только требования (раздел 11), а не подобранный по каталогу привод, поэтому
        # release_gate.py по-прежнему честно блокирует выпуск на "Подбор привода не завершён".
        # Как только появится реальный каталог поставщика (core/reference/drive_catalog.py:
        # load_motor_catalog_from_csv), его нужно передать в select_drive(..., motors=..., gearboxes=...)
        # и при успешном подборе вызвать project.drive_selection.mark_done(...,
        # protection_consistent=drive_result.protection_consistent) — сама привязка этого
        # поля к release_gate.py уже реализована (core/project.py, core/release_gate.py).

        tech_package = build_default_technology_package(
            diameter_mm=result.diameter_mm, step_mm=result.step_mm, working_length_mm=length,
        )
        unconfirmed_ops = tech_package.unconfirmed_operations_report()
        project.warnings_log.extend(tech_package.warnings)
        project.technology.note = (
            f"черновой пакет построен: {len(tech_package.parts)} деталей, {len(tech_package.assemblies)} узлов, "
            f"{len(unconfirmed_ops)} операций требуют подтверждения оборудования паспортом (раздел 16) — "
            "не помечено done, т.к. это предварительный ориентир по времени, а не подтверждённая технология."
        )

    designation = project.designation
    data_dir.mkdir(parents=True, exist_ok=True)
    project_path = data_dir / f"{designation}.json"
    project.save(project_path)  # первое сохранение — чтобы issue_document ниже уже видело актуальный revision

    sheet_data = build_agreement_sheet_data(project)
    html = render_html(sheet_data)
    html_path = data_dir / f"{designation}_list_soglasovaniya.html"
    html_path.write_text(html, encoding="utf-8")
    pdf_path = build_pdf(sheet_data, data_dir / f"{designation}_list_soglasovaniya.pdf")
    project.issue_document("лист_согласования_html", str(html_path))
    project.issue_document("лист_согласования_pdf", str(pdf_path))

    tech_path = data_dir / f"{designation}_technology_draft.json"
    if tech_package is not None:
        tech_path.write_text(
            json.dumps(dataclasses.asdict(tech_package), ensure_ascii=False, indent=2), encoding="utf-8",
        )
        project.issue_document("технология_черновик_json", str(tech_path))
    # SHAFTED_TUBE: tech_package остаётся None (нет диаметра/шага для построения
    # техпроцессов) — tech_path здесь только имя файла-кандидата, файл не создаётся
    # и как документ проекта не регистрируется (issue_document не вызывается).

    project.save(project_path)  # пересохраняем — чтобы issued_documents попали в файл проекта

    return PipelineOutcome(
        unsupported=unsupported, engineering_result=result, drive_result=drive_result,
        technology_package=tech_package, tube_result=tube_result, project_path=project_path,
        html_path=html_path, pdf_path=pdf_path, technology_path=tech_path,
    )


def create_project(
    questionnaire: QuestionnaireInput, project_name: str, customer: str, designation: str,
    data_dir: Path = DATA_DIR,
) -> tuple[Project, PipelineOutcome]:
    """Единая точка создания НОВОГО проекта — используется CLI (`run()`) и веб-формой "Новый проект"."""
    issues = validate_questionnaire(questionnaire)
    if issues:
        raise QuestionnaireValidationError(issues)

    project = Project(
        project_name=project_name, customer=customer, designation=designation,
        created_by_role=Role.MANAGER,
    )
    project.set_questionnaire(questionnaire)
    outcome = recompute_and_save(project, data_dir)
    return project, outcome


def run(questionnaire: QuestionnaireInput, project_name: str, customer: str, designation: str) -> Project:
    print("1) Проверка данных...")
    try:
        project, outcome = create_project(questionnaire, project_name, customer, designation)
    except QuestionnaireValidationError as e:
        print("   Найдены проблемы ввода:")
        for i in e.issues:
            print(f"   - {i}")
        raise SystemExit(
            "\nОстановлено: предварительный расчёт не запускается на данных, "
            "не прошедших базовую проверку (раздел 21)."
        )
    except EngineeringInputError as e:
        raise SystemExit(f"Остановлено инженерным ядром: {e}")
    except TubeEngineeringInputError as e:
        raise SystemExit(f"Остановлено инженерным ядром (трубный шнек): {e}")
    print("   OK — базовых проблем не найдено.")

    if outcome.unsupported:
        print("   Требования, не покрытые текущей методикой (раздел 1.Г — показаны явно, не игнорируются):")
        for u in outcome.unsupported:
            print(f"   - {u}")

    if outcome.tube_result is not None:
        # Issue #3 — SHAFTED_TUBE: инженерное ядро честно заблокировано,
        # печатаем геометрию/конфликт и полный список блокеров вместо
        # диаметра/оборотов/мощности (их здесь нет и не подставляются).
        tr = outcome.tube_result
        print("2) Предварительная компоновка (валовый трубчатый шнек, Issue #3)...")
        print(f"   статус: {tr.status.value}")
        if tr.geometry_conflict is not None:
            gc = tr.geometry_conflict
            print(f"   геометрия: конфликт={'ДА' if gc.conflict else 'нет'}")
            for note in gc.notes:
                print(f"   - {note}")
        if tr.productivity_required_t_per_h is not None:
            print(f"   производительность требуется: {tr.productivity_required_t_per_h} т/ч")
        if tr.warnings:
            print("   Предупреждения расчёта:")
            for w in tr.warnings:
                print(f"   - {w}")
        print(f"   Блокеры расчёта ({len(tr.blockers)}):")
        for b in tr.blockers:
            print(f"   - {b}")
        print("2а) Требования к приводу — не вычислены (нет мощности/оборотов, см. блокеры выше).")
        print("3а) Технология — не построена (нет диаметра/шага корпуса, см. блокеры выше).")
    else:
        print("2) Предварительная компоновка (инженерное ядро, ЧЕРНОВИК)...")
        result = outcome.engineering_result
        print(f"   диаметр={result.diameter_mm} мм, шаг={result.step_mm} мм, "
              f"n={result.rotation_speed_rpm} об/мин (допустимо до {result.max_allowed_rotation_speed_rpm}), "
              f"N_вал={result.shaft_power_kw} кВт, "
              f"мотор={'не подобран' if not result.motor_selection_ok else str(result.motor_power_kw) + ' кВт'}")
        print(f"   производительность: требуется {result.productivity_required_t_per_h} т/ч, "
              f"достижимо {result.productivity_achievable_t_per_h} т/ч, "
              f"требование {'ВЫПОЛНЕНО' if result.requirement_met else 'НЕ ВЫПОЛНЕНО'}")
        if result.warnings:
            print("   Предупреждения расчёта:")
            for w in result.warnings:
                print(f"   - {w}")

        print("2а) Требования к приводу (раздел 11) — каталог поставщика не подключён...")
        req = outcome.drive_result.requirement
        print(f"   требуемая мощность={req.required_power_kw} кВт, "
              f"рабочий момент={req.running_torque_nm} Н·м, пусковой момент={req.starting_torque_nm} Н·м, "
              f"требуемое передаточное число~{req.required_gear_ratio}")
        for w in outcome.drive_result.warnings:
            print(f"   - {w}")

        print("3а) Технология (раздел 7) — черновой пакет по типовому составу...")
        tech_package = outcome.technology_package
        print(f"   деталей={len(tech_package.parts)}, узлов={len(tech_package.assemblies)}, "
              f"машинное время={tech_package.total_machine_time_min} мин, "
              f"время рабочего={tech_package.total_labor_time_min} мин, "
              f"продолжительность={tech_package.total_duration_min} мин")
        print(f"   вариантов изготовления спирали: {len(tech_package.flight_methods)} "
              f"({', '.join(m.method_name for m in tech_package.flight_methods)}) — выбор НЕ автоматический")
        print(f"   операций, требующих подтверждения оборудования: {len(tech_package.unconfirmed_operations_report())}")
        for w in tech_package.warnings:
            print(f"   - {w}")
        print(f"   черновик технологии: {outcome.technology_path}")

    print("3) Сохранение проекта...")
    print(f"   сохранено: {outcome.project_path}")

    print("4) Предварительный лист согласования...")
    print(f"   HTML: {outcome.html_path}")
    print(f"   PDF:  {outcome.pdf_path}")

    print("5) Проверка блокировок выпуска (раздел 20)...")
    reasons = evaluate_release_gate(project, requesting_role=Role.HEAD)
    if reasons:
        print(f"   Выпуск ЗАБЛОКИРОВАН ({len(reasons)} причин) — это ОЖИДАЕМО на этом этапе:")
        for r in reasons:
            print(f"   - {r}")
    else:
        print("   Блокировок не найдено (маловероятно на этом этапе — проверьте вручную).")

    return project


if __name__ == "__main__":
    if len(sys.argv) > 1:
        q = load_questionnaire_from_json(Path(sys.argv[1]))
        name = Path(sys.argv[1]).stem
    else:
        q = example_questionnaire()
        name = "example_25sht"
    run(q, project_name=f"Пилот — {name}", customer="Тех-Аэро (внутренний пилот)", designation=name)
