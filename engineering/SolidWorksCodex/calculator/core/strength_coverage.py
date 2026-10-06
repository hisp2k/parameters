# -*- coding: utf-8 -*-
"""
Реестр охвата прочности по BOM (раздел 10 задания).

"Ни одна позиция не должна оставаться без способа подтверждения
работоспособности" — реестр существует именно для того, чтобы это было
видно, а не подразумевалось. На этом этапе фактического BOM из CAD ещё нет
(нет подключения к SolidWorks из этой среды и нет утверждённой BOM-версии
сборки — см. QUESTIONS_FOR_DMITRY_ALEXANDROVICH_RU.md, вопрос №2), поэтому
реестр строится по типовому составу узлов из задания (раздел 10, список
"Проверяй") со статусом "не выполнено" — это ЧЕСТНОЕ состояние на старте
проекта, а не заглушка для отображения.

ИСПРАВЛЕНИЕ (раздел 1.А задания): раньше `method != NOT_DONE` само по себе
означало "позиция закрыта" — то есть простая смена enum-значения на
ANALYTICAL, без единого реального числа расчёта, "разблокировала" выпуск.
Теперь позиция считается закрытой, только если у неё есть `verification`
(см. core/verification.py) с числовым результатом, критерием, источником,
проверкой другим специалистом и это всё относится к ТЕКУЩЕЙ ревизии и
текущим входным данным проекта. Само поле `method` теперь означает только
"каким способом планируется/выполнена проверка", а не факт её выполнения.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from calculator.core.verification import VerificationRecord
from calculator.core.roles import Role


class VerificationMethod(str, Enum):
    ANALYTICAL = "аналитический_расчёт"
    FEA = "расчёт_кэ"
    CATALOG = "каталожная_проверка"
    TEST = "испытание"
    COMBINED = "сочетание_методов"
    NOT_APPLICABLE = "неприменимо_с_обоснованием"
    NOT_DONE = "не_выполнено"


@dataclass
class StrengthItem:
    bom_position: str          # обозначение позиции BOM (пока placeholder, пока нет CAD BOM)
    component_class: str       # напр. "вал", "спираль", "корпус"
    method: VerificationMethod = VerificationMethod.NOT_DONE
    justification: str | None = None   # обязателен, если method == NOT_APPLICABLE
    load_cases_checked: list[str] = field(default_factory=list)
    result_note: str | None = None
    verification: Optional[VerificationRecord] = None
    # Issue #3, этап 6 ("прочностная архитектура"): ОДНА позиция BOM обычно требует
    # НЕСКОЛЬКО отдельных проверок (напр. вал — torque/bending/combined_stress/deflection/
    # critical_speed). `verification` (единственное число) оставлен как есть для обратной
    # совместимости с уже сохранёнными проектами SHAFTED_TROUGH; новый код должен читать/
    # писать `verifications` (список) — см. required_load_cases()/uncovered_load_cases() ниже.
    verifications: list[VerificationRecord] = field(default_factory=list)
    # Для NOT_APPLICABLE обоснование должно быть кем-то утверждено — иначе
    # "обоснованное исключение" превращается в способ обойти проверку молча.
    justification_approved_by: str | None = None
    justification_approved_by_role: Optional[Role] = None


# Типовой состав по разделу 10 — на старте у КАЖДОЙ позиции метод "не
# выполнено". BOM_position оставлен как placeholder до подключения реальной
# BOM-версии сборки из CAD.
DEFAULT_TYPICAL_SCOPE: list[str] = [
    "вал шнека",
    "труба/цапфы",
    "спираль шнека и её крепления",
    "межсекционные соединения",
    "муфта/шпонка/шлицы",
    "подшипники и корпуса подшипников",
    "промежуточные опоры",
    "корпус, крышки, патрубки, фланцы",
    "рама, стойки, плиты",
    "крепления привода",
    "сварные соединения",
    "болтовые соединения",
    "ограждения",
    "проушины и транспортные крепления",
]


def build_default_registry() -> list[StrengthItem]:
    return [
        StrengthItem(bom_position="уточнить_по_BOM", component_class=cls)
        for cls in DEFAULT_TYPICAL_SCOPE
    ]


# Issue #3, этап 6 ("прочностная архитектура") — какие отдельные проверки
# (load cases) требуются для каждого класса компонента, по прямому
# перечислению задания. Ключи — те же строки component_class, что и в
# DEFAULT_TYPICAL_SCOPE, чтобы одна и та же позиция (generic ИЛИ из реальной
# BOM) знала свой полный список обязательных проверок. Каждый load case —
# это отдельный VerificationRecord (criterion_description=<код load case>)
# внутри StrengthItem.verifications, а НЕ единственноеverification.
REQUIRED_LOAD_CASES_BY_COMPONENT_CLASS: dict[str, list[str]] = {
    "вал шнека": ["torque", "bending", "combined_stress", "deflection", "critical_speed"],
    "труба/цапфы": ["bending", "torsion", "stress_concentration"],
    "подшипники и корпуса подшипников": ["radial_load", "axial_load", "equivalent_load", "l10_life"],
    "спираль шнека и её крепления": ["weld", "local_load", "deformation", "wear_verification_method"],
    "корпус, крышки, патрубки, фланцы": ["bending_between_supports", "local_nozzle_loads", "drive_group_load"],
    "рама, стойки, плиты": ["beams", "posts", "braces", "base_plates"],
    "сварные соединения": ["welds"],
    "болтовые соединения": ["bolts"],
    "проушины и транспортные крепления": ["anchors"],
    "муфта/шпонка/шлицы": ["coupling_key_spline"],
    # Остальные классы DEFAULT_TYPICAL_SCOPE (межсекционные соединения, промежуточные
    # опоры, ограждения) намеренно не перечислены здесь — задание не называло для них
    # load case'ы; required_load_cases() честно вернёт [] вместо выдуманного списка.
}


def required_load_cases(component_class: str) -> list[str]:
    """Пустой список — НЕ 'не проверяется', а 'каталог для этого класса ещё не определён'."""
    return list(REQUIRED_LOAD_CASES_BY_COMPONENT_CLASS.get(component_class, []))


def load_case_coverage(
    item: StrengthItem, project_revision: str, input_fingerprint: str
) -> dict[str, bool]:
    """Для каждого обязательного load case этого класса — закрыт ли он реальной проверкой."""
    result: dict[str, bool] = {}
    for case in required_load_cases(item.component_class):
        records = [v for v in item.verifications if v.criterion_description == case]
        # Legacy record can prove only its named check, never every check of a node.
        if not records and item.verification is not None and item.verification.criterion_description == case:
            records = [item.verification]
        # Conflicting/repeated records require resolution; list order is not evidence.
        result[case] = len(records) == 1 and records[0].is_complete_and_valid(
            project_revision, input_fingerprint
        )[0]
    return result


def uncovered_load_cases(item: StrengthItem, project_revision: str, input_fingerprint: str) -> list[str]:
    coverage = load_case_coverage(item, project_revision, input_fingerprint)
    return [case for case, closed in coverage.items() if not closed]


def build_strength_registry_from_bom(bom: list) -> list[StrengthItem]:
    """
    Issue #3, этап 5/6: реестр строится из РЕАЛЬНОЙ BOM (настоящие
    обозначения позиций), а НЕ из общего списка "уточнить_по_BOM"
    (build_default_registry() выше). `bom` — список
    `cad_adapter.tube_bom_plan.BomPosition` (не импортируется здесь напрямую,
    чтобы не создавать цикл core->cad_adapter->core; принимается любой
    объект с атрибутами designation/strength_component_class).

    Вся BOM отклоняется с ValueError, если хотя бы у одной позиции нет
    реального designation (пусто / "уточнить_по_BOM") или не задан
    strength_component_class (неизвестно, какие проверки выполнять).
    Эти поля должны быть заполнены у каждой позиции. Молчаливый пропуск
    сокращает охват прочности и может скрыть непроверенный узел.
    Источник каждой строки должен быть CAD_READBACK, а не план сборки.
    """
    items: list[StrengthItem] = []
    if not bom:
        raise ValueError("BOM пуста — реестр прочности не сформирован.")
    for index, pos in enumerate(bom, 1):
        designation = getattr(pos, "designation", None)
        component_class = getattr(pos, "strength_component_class", None)
        if (not isinstance(designation, str) or not designation.strip()
                or designation.strip() == "уточнить_по_BOM"):
            raise ValueError(f"BOM, строка {index}: нет реального обозначения позиции.")
        if not isinstance(component_class, str) or not component_class.strip():
            raise ValueError(f"BOM {designation}: не задан класс проверки прочности.")
        if getattr(pos, "source", None) != "cad_обратное_чтение":
            raise ValueError(f"BOM {designation}: источник не является обратным чтением CAD.")
        items.append(StrengthItem(bom_position=designation, component_class=component_class))
    return items


def item_is_closed(item: StrengthItem, project_revision: str, input_fingerprint: str) -> tuple[bool, list[str]]:
    """
    Единая проверка "эта позиция реально закрыта", а не просто помечена.
    Возвращает (закрыта_ли, список_причин_если_нет).
    """
    if item.method == VerificationMethod.NOT_DONE:
        return False, ["проверка не выполнена"]

    if not item.bom_position.strip() or item.bom_position.strip() == "уточнить_по_BOM":
        return False, ["нет реального обозначения позиции BOM"]

    if item.method == VerificationMethod.NOT_APPLICABLE:
        problems = []
        if not item.justification or not item.justification.strip():
            problems.append("исключение 'неприменимо' заявлено без обоснования")
        if not item.justification_approved_by:
            problems.append("обоснование исключения не утверждено ответственным лицом")
        return (len(problems) == 0), problems

    if not required_load_cases(item.component_class):
        return False, ["каталог обязательных проверок для класса прочности не определён"]
    missing = uncovered_load_cases(item, project_revision, input_fingerprint)
    return not missing, [f"нет единственного актуального подтверждения проверки: {case}" for case in missing]


def uncovered(
    registry: list[StrengthItem],
    project_revision: str | None = None,
    input_fingerprint: str | None = None,
) -> list[StrengthItem]:
    """
    Позиции, которые НЕ закрыты по-настоящему (не только method == NOT_DONE).

    project_revision/input_fingerprint необязательны для обратной
    совместимости вызовов, где ревизия не важна (напр. простой подсчёт по
    method), но тогда проверка актуальности данных не выполняется — при
    вызове из release_gate.py эти параметры ОБЯЗАТЕЛЬНО передаются.
    """
    if project_revision is None or input_fingerprint is None:
        return [item for item in registry if item.method == VerificationMethod.NOT_DONE]
    result = []
    for item in registry:
        closed, _ = item_is_closed(item, project_revision, input_fingerprint)
        if not closed:
            result.append(item)
    return result


def coverage_report(
    registry: list[StrengthItem], project_revision: str, input_fingerprint: str
) -> list[tuple[StrengthItem, bool, list[str]]]:
    """Полный отчёт по каждой позиции — для интерфейса и отчёта пользователю."""
    return [
        (item, *item_is_closed(item, project_revision, input_fingerprint))
        for item in registry
    ]


def is_fully_covered(registry: list[StrengthItem], project_revision: str, input_fingerprint: str) -> bool:
    return bool(registry) and len(uncovered(registry, project_revision, input_fingerprint)) == 0
