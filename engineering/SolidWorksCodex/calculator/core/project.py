# -*- coding: utf-8 -*-
"""
Проект (раздел 19 задания): единая ревизия для расчёта, модели, листа
согласования, BOM и технологии; сохранение/загрузка; версии методик.

Формат хранения — JSON-файл на диск (раздел 19: "данные и правила не
зашивай в компоненты интерфейса"; простой поддерживаемый стек для старта).
Каждый Project имеет revision (строка) и общий created_at/updated_at —
все дочерние артефакты (лист согласования, BOM, технология) должны отдавать
именно эту ревизию наружу, а не собственную.

ИСПРАВЛЕНИЕ (раздел 1.Б задания — "устаревшие результаты"): раньше
questionnaire можно было заменить/изменить напрямую (`project.questionnaire =
новая_анкета`), и ничего в проекте не менялось — ревизия, расчёт, статус
подтверждения инженера и модули оставались как были, как будто они всё ещё
относятся к новым данным. Теперь:

- у проекта есть "отпечаток" входных данных (`compute_input_fingerprint`);
- изменение анкеты идёт ТОЛЬКО через `set_questionnaire()`, которое сверяет
  новый отпечаток со отпечатком, на котором был выполнен последний расчёт, и
  если они разошлись — аннулирует расчёт, подтверждение инженера, подбор
  привода, синхронизацию CAD, КД/BOM, технологию и охват прочности, поднимает
  ревизию и пишет запись в историю ревизий;
- `record_engineering_result()` — единственный способ сохранить результат
  расчёта, и он запоминает, для какого именно отпечатка входных данных этот
  результат актуален;
- `issue_document()` регистрирует выгруженный документ (лист согласования,
  BOM и т.п.) с текущей ревизией; `is_document_current()` показывает, что
  документ относится к УЖЕ УСТАРЕВШЕЙ ревизии, а не молча считается новым.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from calculator.core.questionnaire import QuestionnaireInput, ConveyorKind, MaterialInput, \
    ProductivityInput, ProductivityUnit, GeometryInput, GeometryMode, OperatingProfileInput, \
    OptionalDetails, Abrasiveness
from calculator.core.screw_engineering import ScrewEngineeringResult
from calculator.core.tube_engineering import (
    TubeEngineeringResult, TubeCalcStatus, GeometryConflictReport,
    DriveLocationConflictReport, DriveLocation,
)
from calculator.core.strength_coverage import StrengthItem, VerificationMethod, build_default_registry
from calculator.core.roles import Role, require
from calculator.core.verification import VerificationRecord
from calculator.core.parameters import ParameterSet, ParamStatus
from calculator.cad_adapter.section_layout import TroughSectionLayout
from calculator.core.tube_shaft_study import TubeShaftInfluenceStudy


PROJECT_STATUS_DRAFT = "черновик"
PROJECT_STATUS_SUBMITTED = "передан_на_проверку"
PROJECT_STATUS_ENGINEER_CONFIRMED = "подтверждён_инженером"
PROJECT_STATUS_RELEASED = "утверждён_к_выпуску"


@dataclass
class ModuleStatus:
    """
    Честное состояние подсистемы. ИСПРАВЛЕНИЕ (раздел 1.А): раньше
    `done=True` было простым булевым флагом без подтверждения — теперь
    `mark_done()` требует роль, доказательство (evidence) и привязку к
    конкретному отпечатку входных данных/ревизии, а `invalidate()` явно
    сбрасывает done при изменении данных вместо того, чтобы оставлять
    устаревший True.
    """

    implemented: bool = False
    done: bool = False
    note: str = "не реализовано на этом этапе"
    confirmed_by: str = ""
    confirmed_by_role: Optional[Role] = None
    evidence: str = ""
    input_fingerprint: str = ""
    product_revision: str = ""
    # ИСПРАВЛЕНИЕ (раздел 4 задания — "согласованность привода и защиты"):
    # раньше release_gate.py проверял это подстрокой "protection_consistent=False"
    # в текстовом поле evidence — хрупко и легко разошлось бы с реальным текстом.
    # Теперь это отдельное структурированное поле, заполняемое из
    # core/drive_selection.py::DriveSelectionResult.protection_consistent, а не
    # угадываемое по тексту. None = сигнал ещё не вычислен (для модулей, где
    # защита привода не относится к делу, поле просто не используется).
    protection_consistent: Optional[bool] = None

    def mark_done(self, *, confirmed_by: str, confirmed_by_role: Role, evidence: str,
                  input_fingerprint: str, product_revision: str,
                  protection_consistent: Optional[bool] = None) -> None:
        if not confirmed_by or not evidence:
            raise ValueError(
                "Модуль нельзя пометить выполненным без исполнителя и доказательства "
                "(конкретного результата) — простая смена флага done запрещена (раздел 1.А)."
            )
        self.implemented = True
        self.done = True
        self.confirmed_by = confirmed_by
        self.confirmed_by_role = confirmed_by_role
        self.evidence = evidence
        self.input_fingerprint = input_fingerprint
        self.product_revision = product_revision
        self.protection_consistent = protection_consistent
        self.note = f"выполнено: {evidence}"

    def invalidate(self, reason: str) -> None:
        self.done = False
        self.confirmed_by = ""
        self.confirmed_by_role = None
        self.evidence = ""
        self.input_fingerprint = ""
        self.product_revision = ""
        self.protection_consistent = None
        self.note = f"аннулировано: {reason}"

    def is_current(self, project_revision: str, input_fingerprint: str) -> bool:
        return self.done and self.product_revision == project_revision and (
            not input_fingerprint or self.input_fingerprint == input_fingerprint
        )


@dataclass
class TechnicalReview:
    """Раздел 1.А: "техническую проверку другим специалистом" — отдельно от заявления инженера о себе."""

    reviewer_name: str
    reviewer_role: Role
    prepared_by_name: str
    reviewed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    input_fingerprint: str = ""
    product_revision: str = ""
    notes: str = ""

    def is_independent(self) -> bool:
        return self.reviewer_name.strip().lower() != self.prepared_by_name.strip().lower()


@dataclass
class ReleaseApproval:
    """Раздел 1.А: "утверждение руководителем" — отдельная запись, а не факт наличия роли у вызывающего."""

    approved_by_name: str
    approved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    product_revision: str = ""


@dataclass
class RevisionRecord:
    revision: str
    superseded_at: str
    reason: str


@dataclass
class IssuedDocument:
    kind: str
    path: str
    revision: str
    issued_at: str

    def is_current(self, current_revision: str) -> bool:
        return self.revision == current_revision


def _bump_revision(revision: str) -> str:
    """
    Поднимает последнее числовое поле версии на 1, сохраняя произвольный
    текстовый хвост (напр. "-предварительная"). "0.0.1-предварительная" ->
    "0.0.2-предварительная". Если числового поля нет — просто добавляет
    суффикс "+1", чтобы не потерять факт изменения.
    """
    m = re.search(r"(\d+)(?!.*\d)", revision)
    if not m:
        return f"{revision}+1"
    start, end = m.span()
    new_num = str(int(m.group(1)) + 1)
    return revision[:start] + new_num + revision[end:]


@dataclass
class Project:
    project_name: str
    customer: str
    designation: str
    revision: str = "0.0.1-предварительная"
    status: str = PROJECT_STATUS_DRAFT
    created_by_role: Role = Role.MANAGER
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    questionnaire: Optional[QuestionnaireInput] = None
    engineering_result: Optional[ScrewEngineeringResult] = None
    # Отдельное поле для валового ТРУБЧАТОГО шнека (Issue #3) — НЕ переиспользует
    # engineering_result (жёстко типизирован на ScrewEngineeringResult желобчатого
    # шнека, см. record_engineering_result/to_dict/load ниже). Для проекта
    # SHAFTED_TROUGH это поле остаётся None — поведение и сериализация такого
    # проекта не меняются ни на байт.
    tube_engineering_result: Optional[TubeEngineeringResult] = None
    strength_registry: list[StrengthItem] = field(default_factory=build_default_registry)

    drive_selection: ModuleStatus = field(
        default_factory=lambda: ModuleStatus(note="подбор привода (раздел 11) не реализован на этом этапе")
    )
    cad_sync: ModuleStatus = field(
        default_factory=lambda: ModuleStatus(note="синхронизация с SolidWorks недоступна из этой среды")
    )
    kd_bom: ModuleStatus = field(
        default_factory=lambda: ModuleStatus(note="КД и BOM (раздел 14) не реализованы на этом этапе")
    )
    technology: ModuleStatus = field(
        default_factory=lambda: ModuleStatus(note="технология (раздел 15/17) не реализована на этом этапе")
    )
    economics: ModuleStatus = field(
        default_factory=lambda: ModuleStatus(note="себестоимость/цена (раздел 18) не реализованы на этом этапе")
    )

    engineer_confirmed_assumptions: bool = False
    engineer_confirmed_by: str = ""
    warnings_log: list[str] = field(default_factory=list)

    technical_review: Optional[TechnicalReview] = None
    release_approval: Optional[ReleaseApproval] = None

    # Ревизия, для которой актуален engineering_result (раздел 1.Б).
    calc_input_fingerprint: str = ""
    revision_history: list[RevisionRecord] = field(default_factory=list)
    issued_documents: list[IssuedDocument] = field(default_factory=list)

    # Раздел 19 — параметры с происхождением, реально наполняемые (не
    # неиспользуемый каркас): диаметр/шаг/обороты/мощность и т.п. кладутся
    # сюда при каждом расчёте (см. record_engineering_result()).
    parameters: ParameterSet = field(default_factory=ParameterSet)
    cad_layout_readback: ModuleStatus = field(
        default_factory=lambda: ModuleStatus(note="чтение состава желоба ещё не выполнялось")
    )
    trough_section_layout: Optional[dict] = None

    # Issue #3 (продолжение — прочность TUBE-SAND-001): ИССЛЕДОВАТЕЛЬСКИЙ
    # расчёт вала (core/tube_shaft_study.py) — коэффициенты влияния на
    # ПРИНЯТОЙ длине пролёта, НЕ подтверждённая проверка. Специально
    # ОТДЕЛЬНОЕ поле от strength_registry: is_exploratory=True/
    # closes_release_gate_item=False у самого результата гарантируют, что
    # release_gate.py и strength_coverage.py его никогда не увидят —
    # см. record_tube_shaft_study() и test_tube_shaft_study.py::
    # test_shaft_study_never_affects_release_gate.
    tube_shaft_study: Optional[TubeShaftInfluenceStudy] = None

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    # --- ревизии и аннулирование (раздел 1.Б) ------------------------------

    def compute_input_fingerprint(self) -> str:
        """Хэш анкеты — используется, чтобы обнаружить, что данные изменились."""
        if self.questionnaire is None:
            return ""
        q = self.questionnaire
        payload = {
            "conveyor_kind": q.conveyor_kind.value,
            "material": {**asdict(q.material),
                         "abrasiveness": q.material.abrasiveness.value if q.material.abrasiveness else None},
            "productivity": {
                "value": q.productivity.value,
                "unit": q.productivity.unit.value if q.productivity.unit is not None else None,
            },
            "geometry": {**asdict(q.geometry), "mode": q.geometry.mode.value},
            "profile": asdict(q.profile),
            "optional": asdict(q.optional),
            "forced_diameter_mm": q.forced_diameter_mm,
            "forced_step_mm": q.forced_step_mm,
        }
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def set_questionnaire(self, new_questionnaire: QuestionnaireInput, reason: str = "изменение исходных данных") -> bool:
        """
        Единственный поддерживаемый способ заменить анкету проекта.
        Возвращает True, если это привело к аннулированию расчёта (данные
        реально изменились относительно того, на чём был посчитан текущий
        engineering_result).
        """
        # ИСПРАВЛЕНИЕ (Issue #3): для SHAFTED_TUBE engineering_result всегда
        # None (используется tube_engineering_result, см. record_tube_engineering_result) —
        # проверка только по engineering_result никогда не считала бы
        # трубный расчёт "подтверждённым" и изменение анкеты тихо не
        # аннулировало бы его.
        had_confirmed_calc = (
            self.engineering_result is not None or self.tube_engineering_result is not None
        ) and self.calc_input_fingerprint != ""
        old_fingerprint = self.calc_input_fingerprint

        self.questionnaire = new_questionnaire
        new_fingerprint = self.compute_input_fingerprint()

        invalidated = had_confirmed_calc and new_fingerprint != old_fingerprint
        if invalidated:
            self._invalidate_downstream(reason)
        self.touch()
        return invalidated

    def _invalidate_downstream(self, reason: str) -> None:
        old_revision = self.revision
        self.revision = _bump_revision(self.revision)
        self.revision_history.append(RevisionRecord(
            revision=old_revision,
            superseded_at=datetime.now(timezone.utc).isoformat(),
            reason=reason,
        ))
        self.engineering_result = None
        self.tube_engineering_result = None
        self.tube_shaft_study = None
        self.calc_input_fingerprint = ""
        self.engineer_confirmed_assumptions = False
        self.engineer_confirmed_by = ""
        self.technical_review = None
        self.release_approval = None
        self.drive_selection.invalidate(reason)
        self.cad_sync.invalidate(reason)
        self.cad_layout_readback.invalidate(reason)
        self.kd_bom.invalidate(reason)
        self.technology.invalidate(reason)
        for item in self.strength_registry:
            item.verifications.clear()
            if item.method != VerificationMethod.NOT_DONE:
                item.verification = None
                item.method = VerificationMethod.NOT_DONE
                item.result_note = f"аннулировано ({reason}) — требуется пересчёт для новой ревизии {self.revision}"
        self.status = PROJECT_STATUS_DRAFT
        self.warnings_log.append(
            f"Ревизия поднята с {old_revision} на {self.revision}: {reason}. "
            "Расчёт, подтверждение инженера, привод, CAD, КД и технология аннулированы."
        )

    def record_engineering_result(self, result: ScrewEngineeringResult, computed_by_role: Role = Role.ENGINEER) -> None:
        """
        Единственный способ сохранить результат расчёта — привязывает его к
        текущему отпечатку данных И заполняет `self.parameters` (раздел 19:
        параметры с происхождением) реальными числами этого расчёта, а не
        оставляет ParameterSet пустым неиспользуемым каркасом.
        """
        self.engineering_result = result
        self.calc_input_fingerprint = self.compute_input_fingerprint()
        self.warnings_log.extend(result.warnings)

        source = "core.screw_engineering.compute_engineering_core (черновик, не проверено)"
        status = ParamStatus.CALCULATED_PRELIMINARY
        self.parameters.put("diameter_mm", result.diameter_mm, "мм", source, status, computed_by_role.value)
        self.parameters.put("step_mm", result.step_mm, "мм", source, status, computed_by_role.value)
        self.parameters.put("rotation_speed_rpm", result.rotation_speed_rpm, "об/мин", source, status, computed_by_role.value)
        self.parameters.put(
            "max_allowed_rotation_speed_rpm", result.max_allowed_rotation_speed_rpm,
            "об/мин", source, status, computed_by_role.value,
        )
        self.parameters.put("shaft_power_kw", result.shaft_power_kw, "кВт", source, status, computed_by_role.value)
        self.parameters.put(
            "motor_power_kw", result.motor_power_kw, "кВт", source,
            status if result.motor_selection_ok else ParamStatus.MISSING, computed_by_role.value,
        )
        self.parameters.put(
            "productivity_required_t_per_h", result.productivity_required_t_per_h, "т/ч",
            "questionnaire.productivity (введено пользователем)", ParamStatus.USER_INPUT, computed_by_role.value,
        )
        self.parameters.put(
            "productivity_achievable_t_per_h", result.productivity_achievable_t_per_h, "т/ч",
            source, status, computed_by_role.value,
            note="раздел 1.В — может быть меньше требуемой, если ограничены обороты",
        )
        self.parameters.put(
            "requirement_met", result.requirement_met, "", source, status, computed_by_role.value,
        )
        self.touch()

    def record_tube_engineering_result(
        self, result: TubeEngineeringResult, computed_by_role: Role = Role.ENGINEER,
    ) -> None:
        """
        Аналог record_engineering_result() для SHAFTED_TUBE (Issue #3) —
        единственный способ сохранить результат трубного расчёта. Никогда не
        трогает self.engineering_result (тот остаётся None для трубных
        проектов). Параметры кладутся только там, где значение реально
        вычислено (не None) — для заблокированных полей ParameterSet
        честно получает статус MISSING, а не выдуманное число.
        """
        self.tube_engineering_result = result
        self.calc_input_fingerprint = self.compute_input_fingerprint()
        self.warnings_log.extend(result.warnings)
        self.warnings_log.extend(result.blockers)

        source = "core.tube_engineering.compute_tube_engineering_core (геометрия + честные блокеры)"
        status = ParamStatus.CALCULATED_PRELIMINARY
        if result.connection_diameter_mm is not None:
            self.parameters.put(
                "tube_connection_diameter_mm", result.connection_diameter_mm, "мм", source, status,
                computed_by_role.value, note="DN присоединительного патрубка — НЕ диаметр корпуса",
            )
        if result.diameter_mm is not None:
            self.parameters.put("diameter_mm", result.diameter_mm, "мм", source, status, computed_by_role.value)
        else:
            self.parameters.put(
                "diameter_mm", None, "мм", source, ParamStatus.MISSING, computed_by_role.value,
                note="диаметр корпуса трубного шнека не определён — см. tube_engineering_result.blockers",
            )
        if result.productivity_required_t_per_h is not None:
            self.parameters.put(
                "productivity_required_t_per_h", result.productivity_required_t_per_h, "т/ч",
                "questionnaire.productivity (введено пользователем, переведено в т/ч)",
                ParamStatus.USER_INPUT, computed_by_role.value,
            )
        if result.geometry_conflict is not None:
            self.parameters.put(
                "tube_geometry_conflict", result.geometry_conflict.conflict, "", source, status,
                computed_by_role.value,
                note=f"допуск {result.geometry_conflict.tolerance_mm:.0f} мм; см. geometry_conflict.scenarios",
            )
        self.touch()

    def record_tube_shaft_study(self, study: TubeShaftInfluenceStudy) -> None:
        """
        Единственный способ прикрепить исследовательский расчёт вала
        (core/tube_shaft_study.py) к проекту. НЕ вызывает touch()-подобных
        побочных эффектов над strength_registry/release_gate — исследование
        обязано остаться is_exploratory=True/closes_release_gate_item=False
        (нарушение этого — ошибка вызывающего кода, не самого проекта).
        """
        if not study.is_exploratory or study.closes_release_gate_item:
            raise ValueError(
                "tube_shaft_study должен оставаться исследовательским "
                "(is_exploratory=True, closes_release_gate_item=False) — "
                "он никогда не закрывает позицию release_gate напрямую."
            )
        self.tube_shaft_study = study
        self.touch()

    def is_calc_stale(self) -> bool:
        """Раздел 1.Б: расчёт есть, но относится к другим (уже изменённым) входным данным."""
        if self.engineering_result is None and self.tube_engineering_result is None:
            return False
        return self.calc_input_fingerprint != self.compute_input_fingerprint()

    def record_trough_section_layout(
        self, layout: TroughSectionLayout, *, recorded_by: str, recorded_by_role: Role,
    ) -> None:
        """
        Раздел 4 доп. задания ("изменение модели из калькулятора с обратным
        получением фактических размеров"): сохраняет честный снимок
        компоновки желоба, считанный из SolidWorks
        (`cad_adapter.section_layout.read_trough_section_layout()`), в самом
        проекте — с происхождением (раздел 19), а не только в ответе одного
        HTTP-запроса, чтобы он не терялся между обращениями.

        Идемпотентно: повторный вызов с тем же (или свежим) `layout`
        обновляет именованные параметры и cad_layout_readback. Совпадающий
        снимок не поднимает ревизию. Изменённый снимок аннулирует зависимые
        подтверждения; частичное чтение никогда не закрывает cad_sync.
        """
        require(recorded_by_role, "rebuild_cad_project_copy")
        if not recorded_by.strip():
            raise ValueError("Нужно указать исполнителя чтения CAD.")
        snapshot = layout.to_dict()
        # Смена состава/задания/толщины или потеря подтверждённого чтения
        # аннулирует документы и инженерные согласования предыдущего снимка.
        if snapshot != self.trough_section_layout and (
            layout.ok or (self.trough_section_layout or {}).get("ok")
        ):
            self._invalidate_cad_results("изменился снимок компоновки желоба или результат его чтения")
        self.trough_section_layout = snapshot
        for name in list(self.parameters):
            if name.startswith("trough_"):
                del self.parameters[name]
        source = "cad_adapter.section_layout.read_trough_section_layout (считано из SolidWorks)"

        self.parameters.put(
            "trough_target_section_count", layout.target_section_count, "шт",
            "задание/анкета (подтверждено пользователем)", ParamStatus.USER_INPUT, recorded_by,
        )
        self.parameters.put(
            "trough_nominal_section_length_mm", layout.nominal_section_length_mm, "мм",
            "задание/анкета (подтверждено пользователем)", ParamStatus.USER_INPUT, recorded_by,
        )
        self.parameters.put(
            "trough_target_nominal_length_mm", layout.target_nominal_length_mm, "мм",
            "nominal_section_length_mm × target_section_count", ParamStatus.CALCULATED, recorded_by,
        )

        if layout.ok and not layout.errors:
            self.parameters.put(
                "trough_measured_section_count", layout.measured_section_count, "шт",
                source, ParamStatus.CAD_READBACK, recorded_by,
            )
            self.parameters.put(
                "trough_measured_spacer_count", layout.measured_spacer_count, "шт",
                source, ParamStatus.CAD_READBACK, recorded_by,
            )
            if layout.measured_joint_spacer_thickness_mm is not None:
                self.parameters.put(
                    "trough_measured_joint_spacer_thickness_mm", layout.measured_joint_spacer_thickness_mm, "мм",
                    "измерено вручную в SolidWorks (передано в запрос синхронизации)",
                    ParamStatus.USER_INPUT, recorded_by,
                )
            if layout.measured_overall_length_estimate_mm is not None:
                self.parameters.put(
                    "trough_overall_length_estimate_mm", layout.measured_overall_length_estimate_mm, "мм",
                    "nominal_section_length_mm × measured_section_count + "
                    "measured_joint_spacer_thickness_mm × (measured_section_count - 1)",
                    ParamStatus.CALCULATED_PRELIMINARY,
                    recorded_by,
                    note="оценка по номиналу секции и измеренной толщине проставки — "
                         "НЕ прямой обмер габарита сборки (overall_length_is_estimate=True)",
                )
            evidence = (
                f"sw_components: секций {layout.measured_section_count} (цель {layout.target_section_count}), "
                f"проставок {layout.measured_spacer_count}, connector_write_allowed="
                f"{layout.connector_write_allowed}"
            )
            self.cad_layout_readback.mark_done(
                confirmed_by=recorded_by,
                confirmed_by_role=recorded_by_role,
                evidence=evidence,
                input_fingerprint=self.compute_input_fingerprint(),
                product_revision=self.revision,
            )
            self.cad_sync.invalidate(
                "прочитан только состав желоба; не подтверждены посадки проставок, коллизии, "
                "полная компоновка шнека/привода и актуальность BOM"
            )
        else:
            reason = "; ".join(layout.errors) if layout.errors else "чтение компоновки CAD не удалось"
            self.cad_layout_readback.invalidate(reason)
            self.cad_sync.invalidate(reason)
        self.touch()

    def _invalidate_cad_results(self, reason: str) -> None:
        old_revision = self.revision
        self.revision = _bump_revision(self.revision)
        self.revision_history.append(RevisionRecord(
            revision=old_revision, superseded_at=datetime.now(timezone.utc).isoformat(), reason=reason,
        ))
        self.technical_review = None
        self.release_approval = None
        self.tube_shaft_study = None
        self.engineer_confirmed_assumptions = False
        self.engineer_confirmed_by = ""
        self.status = PROJECT_STATUS_DRAFT
        for module in (self.drive_selection, self.cad_sync, self.cad_layout_readback,
                       self.kd_bom, self.technology, self.economics):
            module.invalidate(reason)
        for item in self.strength_registry:
            item.verification = None
            item.verifications.clear()
            item.justification_approved_by = ""
            item.justification_approved_by_role = None
        self.warnings_log.append(reason + "; требуется сверка CAD с анкетой и повторная проверка.")
        self.touch()

    def issue_document(self, kind: str, path: str) -> IssuedDocument:
        doc = IssuedDocument(kind=kind, path=str(path), revision=self.revision,
                              issued_at=datetime.now(timezone.utc).isoformat())
        self.issued_documents.append(doc)
        return doc

    def stale_issued_documents(self) -> list[IssuedDocument]:
        return [d for d in self.issued_documents if not d.is_current(self.revision)]

    # --- сериализация -----------------------------------------------------

    def to_dict(self) -> dict:
        d = {
            "project_name": self.project_name,
            "customer": self.customer,
            "designation": self.designation,
            "revision": self.revision,
            "status": self.status,
            "created_by_role": self.created_by_role.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "engineer_confirmed_assumptions": self.engineer_confirmed_assumptions,
            "engineer_confirmed_by": self.engineer_confirmed_by,
            "warnings_log": self.warnings_log,
            "calc_input_fingerprint": self.calc_input_fingerprint,
            "drive_selection": _module_status_to_dict(self.drive_selection),
            "cad_sync": _module_status_to_dict(self.cad_sync),
            "cad_layout_readback": _module_status_to_dict(self.cad_layout_readback),
            "trough_section_layout": self.trough_section_layout,
            "kd_bom": _module_status_to_dict(self.kd_bom),
            "technology": _module_status_to_dict(self.technology),
            "economics": _module_status_to_dict(self.economics),
            "strength_registry": [_strength_item_to_dict(item) for item in self.strength_registry],
            "revision_history": [asdict(r) for r in self.revision_history],
            "issued_documents": [asdict(dc) for dc in self.issued_documents],
            "parameters": self.parameters.to_dict(),
            "technical_review": (
                {**asdict(self.technical_review), "reviewer_role": self.technical_review.reviewer_role.value}
                if self.technical_review else None
            ),
            "release_approval": asdict(self.release_approval) if self.release_approval else None,
        }
        if self.questionnaire is not None:
            q = self.questionnaire
            d["questionnaire"] = {
                "conveyor_kind": q.conveyor_kind.value,
                "material": asdict(q.material),
                "productivity": {
                "value": q.productivity.value,
                "unit": q.productivity.unit.value if q.productivity.unit is not None else None,
            },
                "geometry": {**asdict(q.geometry), "mode": q.geometry.mode.value},
                "profile": asdict(q.profile),
                "optional": asdict(q.optional),
                "forced_diameter_mm": q.forced_diameter_mm,
                "forced_step_mm": q.forced_step_mm,
            }
            if q.material.abrasiveness is not None:
                d["questionnaire"]["material"]["abrasiveness"] = q.material.abrasiveness.value
        if self.engineering_result is not None:
            d["engineering_result"] = asdict(self.engineering_result)
        if self.tube_engineering_result is not None:
            d["tube_engineering_result"] = _tube_result_to_dict(self.tube_engineering_result)
        if self.tube_shaft_study is not None:
            d["tube_shaft_study"] = self.tube_shaft_study.to_dict()
        return d

    def save(self, path: Path | str) -> Path:
        self.touch()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return path

    @staticmethod
    def load(path: Path | str) -> "Project":
        path = Path(path)
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)

        q = None
        if d.get("questionnaire"):
            qd = d["questionnaire"]
            material_d = dict(qd["material"])
            if material_d.get("abrasiveness"):
                material_d["abrasiveness"] = Abrasiveness(material_d["abrasiveness"])
            geometry_d = dict(qd["geometry"])
            geometry_d["mode"] = GeometryMode(geometry_d["mode"])
            if geometry_d.get("load_point_xyz_mm") is not None:
                geometry_d["load_point_xyz_mm"] = tuple(geometry_d["load_point_xyz_mm"])
            if geometry_d.get("unload_point_xyz_mm") is not None:
                geometry_d["unload_point_xyz_mm"] = tuple(geometry_d["unload_point_xyz_mm"])
            q = QuestionnaireInput(
                conveyor_kind=ConveyorKind(qd["conveyor_kind"]),
                material=MaterialInput(**material_d),
                productivity=ProductivityInput(
                    value=qd["productivity"]["value"],
                    unit=ProductivityUnit(qd["productivity"]["unit"]) if qd["productivity"].get("unit") else None,
                ),
                geometry=GeometryInput(**geometry_d),
                profile=OperatingProfileInput(**qd["profile"]),
                optional=OptionalDetails(**qd.get("optional", {})),
                forced_diameter_mm=qd.get("forced_diameter_mm"),
                forced_step_mm=qd.get("forced_step_mm"),
            )

        er = None
        if d.get("engineering_result"):
            er = ScrewEngineeringResult(**d["engineering_result"])

        tube_er = None
        if d.get("tube_engineering_result"):
            tube_er = _tube_result_from_dict(d["tube_engineering_result"])

        tube_shaft_study = None
        if d.get("tube_shaft_study"):
            tube_shaft_study = TubeShaftInfluenceStudy.from_dict(d["tube_shaft_study"])

        strength_registry = [_strength_item_from_dict(item) for item in d.get("strength_registry", [])]

        technical_review = None
        if d.get("technical_review"):
            trd = dict(d["technical_review"])
            trd["reviewer_role"] = Role(trd["reviewer_role"])
            technical_review = TechnicalReview(**trd)

        release_approval = ReleaseApproval(**d["release_approval"]) if d.get("release_approval") else None

        proj = Project(
            project_name=d["project_name"],
            customer=d["customer"],
            designation=d["designation"],
            revision=d["revision"],
            status=d["status"],
            created_by_role=Role(d["created_by_role"]),
            created_at=d["created_at"],
            updated_at=d["updated_at"],
            questionnaire=q,
            engineering_result=er,
            tube_engineering_result=tube_er,
            tube_shaft_study=tube_shaft_study,
            strength_registry=strength_registry or build_default_registry(),
            drive_selection=_module_status_from_dict(d["drive_selection"]),
            cad_sync=_module_status_from_dict(d["cad_sync"]),
            cad_layout_readback=_module_status_from_dict(d.get("cad_layout_readback", {})),
            trough_section_layout=d.get("trough_section_layout"),
            kd_bom=_module_status_from_dict(d["kd_bom"]),
            technology=_module_status_from_dict(d["technology"]),
            economics=_module_status_from_dict(d["economics"]),
            engineer_confirmed_assumptions=d.get("engineer_confirmed_assumptions", False),
            engineer_confirmed_by=d.get("engineer_confirmed_by", ""),
            warnings_log=d.get("warnings_log", []),
            technical_review=technical_review,
            release_approval=release_approval,
            calc_input_fingerprint=d.get("calc_input_fingerprint", ""),
            revision_history=[RevisionRecord(**r) for r in d.get("revision_history", [])],
            issued_documents=[IssuedDocument(**dc) for dc in d.get("issued_documents", [])],
            parameters=ParameterSet.from_dict(d.get("parameters", {})),
        )
        if "cad_layout_readback" not in d and any(k.startswith("trough_") for k in proj.parameters):
            proj._invalidate_cad_results("миграция: прежний подсчёт секций не подтверждает готовность CAD")
        return proj


def _geometry_conflict_to_dict(g: GeometryConflictReport) -> dict:
    return asdict(g)


def _geometry_conflict_from_dict(d: dict) -> GeometryConflictReport:
    return GeometryConflictReport(**d)


def _drive_location_conflict_to_dict(g: DriveLocationConflictReport) -> dict:
    d = asdict(g)
    d["text_location"] = g.text_location.value if g.text_location is not None else None
    d["graphic_location"] = g.graphic_location.value if g.graphic_location is not None else None
    return d


def _drive_location_conflict_from_dict(d: dict) -> DriveLocationConflictReport:
    d = dict(d)
    d["text_location"] = DriveLocation(d["text_location"]) if d.get("text_location") else None
    d["graphic_location"] = DriveLocation(d["graphic_location"]) if d.get("graphic_location") else None
    return DriveLocationConflictReport(**d)


def _tube_result_to_dict(r: TubeEngineeringResult) -> dict:
    d = asdict(r)
    d["status"] = r.status.value if isinstance(r.status, TubeCalcStatus) else r.status
    d["geometry_conflict"] = (
        _geometry_conflict_to_dict(r.geometry_conflict) if r.geometry_conflict is not None else None
    )
    d["drive_location_conflict"] = (
        _drive_location_conflict_to_dict(r.drive_location_conflict)
        if r.drive_location_conflict is not None else None
    )
    return d


def _tube_result_from_dict(d: dict) -> TubeEngineeringResult:
    d = dict(d)
    d["status"] = TubeCalcStatus(d["status"]) if d.get("status") else TubeCalcStatus.BLOCKED
    gc = d.get("geometry_conflict")
    d["geometry_conflict"] = _geometry_conflict_from_dict(gc) if gc else None
    dlc = d.get("drive_location_conflict")
    d["drive_location_conflict"] = _drive_location_conflict_from_dict(dlc) if dlc else None
    return TubeEngineeringResult(**d)


def _module_status_to_dict(m: ModuleStatus) -> dict:
    d = asdict(m)
    d["confirmed_by_role"] = m.confirmed_by_role.value if m.confirmed_by_role else None
    return d


def _module_status_from_dict(d: dict) -> ModuleStatus:
    d = dict(d)
    if d.get("confirmed_by_role"):
        d["confirmed_by_role"] = Role(d["confirmed_by_role"])
    return ModuleStatus(**d)


def _strength_item_to_dict(item: StrengthItem) -> dict:
    return {
        "bom_position": item.bom_position,
        "component_class": item.component_class,
        "method": item.method.value,
        "justification": item.justification,
        "load_cases_checked": item.load_cases_checked,
        "result_note": item.result_note,
        "verification": item.verification.to_dict() if item.verification else None,
        "verifications": [v.to_dict() for v in item.verifications],
        "justification_approved_by": item.justification_approved_by,
        "justification_approved_by_role": (
            item.justification_approved_by_role.value if item.justification_approved_by_role else None
        ),
    }


def _strength_item_from_dict(d: dict) -> StrengthItem:
    return StrengthItem(
        bom_position=d["bom_position"],
        component_class=d["component_class"],
        method=VerificationMethod(d["method"]),
        justification=d.get("justification"),
        load_cases_checked=d.get("load_cases_checked", []),
        result_note=d.get("result_note"),
        verification=VerificationRecord.from_dict(d["verification"]) if d.get("verification") else None,
        verifications=[VerificationRecord.from_dict(v) for v in d.get("verifications", [])],
        justification_approved_by=d.get("justification_approved_by"),
        justification_approved_by_role=(
            Role(d["justification_approved_by_role"]) if d.get("justification_approved_by_role") else None
        ),
    )
