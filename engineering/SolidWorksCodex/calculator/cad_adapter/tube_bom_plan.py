# -*- coding: utf-8 -*-
"""
Плановая структура CAD-сборки и BOM трубного шнекового транспортёра
(Issue #3, этап "подготовить CAD-стратегию TUBE-SAND-001").

ЭТО НЕ CAD-МОДЕЛЬ И НЕ BOM. Прямое требование задания: "не строить CAD из
выдуманных размеров". Из этой облачной среды `LocalBridgeCadAdapter.can_read()`
подтверждённо возвращает False (нет Windows/PowerShell/SolidWorks — см.
cad_adapter/interface.py), а подтверждённого чертежа/3D-модели TUBE-SAND-001
не существует — значит, размеров, конфигураций, масс и обозначений позиций
взять НЕОТКУДА, и подставлять их здесь запрещено.

Что ЭТО такое: дерево ПЛАНИРУЕМЫХ позиций сборки (структура, а не числа) —
для каждой позиции честно объявлено (1) какие параметры ей нужны, (2)
откуда каждый параметр должен появиться (анкета / инженерный расчёт, когда
появится методика / CAD readback / каталог поставщика), (3) участвует ли
позиция в BOM, (4) участвует ли в реестре прочности и по какому классу
компонента (core/strength_coverage.py::REQUIRED_LOAD_CASES_BY_COMPONENT_CLASS).

Использование:
- как справочник для будущей реальной интеграции (когда появится CAD-модель
  и рабочая станция с SolidWorks) — `build_bom_from_cad_readback()` ниже уже
  реализует честный протокол вызова, но всегда возвращает BLOCKED из этой
  среды, как и остальной CAD bridge (раздел 5/12).
- как источник `strength_component_class` для
  `core/strength_coverage.py::build_strength_registry_from_bom()`, когда
  появится настоящая BOM с обозначениями (`BomPosition.designation`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from calculator.cad_adapter.interface import CadAdapter


class ParamOrigin(str, Enum):
    """Откуда параметр позиции ДОЛЖЕН появиться — честная декларация, не факт."""

    QUESTIONNAIRE = "анкета"                  # напрямую из QuestionnaireInput (подтверждено заказчиком)
    ENGINEERING_CORE = "инженерный_расчёт"     # из core/tube_engineering.py — сейчас BLOCKED, нет методики 35°
    CAD_READBACK = "cad_обратное_чтение"       # из живой сборки SolidWorks через bridge
    CATALOG = "каталог_поставщика"             # подшипники/мотор-редуктор/крепёж по каталогу
    NOT_YET_DEFINED = "не_определено"          # честно: пока не решено, чем закрывать


@dataclass
class TubeCadPlanItem:
    """Одна позиция ПЛАНА сборки — структура и требования, НЕ геометрия."""

    path: str                        # напр. "шнек/вал_труба" — место в дереве (родитель/потомок через "/")
    name: str
    parent_path: Optional[str]
    required_params: list[str] = field(default_factory=list)
    param_origin: list[ParamOrigin] = field(default_factory=list)  # по одному элементу на required_params[i]
    participates_in_bom: bool = True
    participates_in_strength: bool = True
    # Ключ в core/strength_coverage.py::REQUIRED_LOAD_CASES_BY_COMPONENT_CLASS —
    # None означает "эта позиция не проверяется на прочность отдельно" (напр. кожух-обшивка).
    strength_component_class: Optional[str] = None
    notes: str = ""

    def __post_init__(self):
        if len(self.required_params) != len(self.param_origin):
            raise ValueError(
                f"{self.path}: required_params ({len(self.required_params)}) и param_origin "
                f"({len(self.param_origin)}) должны быть одной длины — на каждый требуемый "
                "параметр должен быть явно назван источник, иначе непонятно, кто его посчитает."
            )


# Дерево по прямому заданию (этап 4, Issue #3, продолжение 17.09.2026):
#
# TUBE-SAND-001
# ├── корпус трубный
# │   ├── загрузочный патрубок DN100
# │   └── выгрузочный патрубок
# ├── шнек
# │   ├── вал/труба
# │   ├── спираль
# │   └── цапфы
# ├── подшипниковые узлы
# ├── приводная группа
# ├── опорная рама
# ├── защитные кожухи
# └── крепёж
TUBE_SAND_001_CAD_PLAN: list[TubeCadPlanItem] = [
    TubeCadPlanItem(
        path="корпус_трубный", name="Корпус трубный", parent_path=None,
        required_params=["внутренний_диаметр_корпуса_мм", "толщина_стенки_мм", "материал_корпуса", "рабочая_длина_мм"],
        param_origin=[
            ParamOrigin.ENGINEERING_CORE,  # BLOCKED — нет методики 35° (core/tube_engineering.py)
            ParamOrigin.NOT_YET_DEFINED,   # прочностной расчёт корпуса ещё не имеет методики
            ParamOrigin.QUESTIONNAIRE,     # заказчик пока не подтвердил (сейчас Ст3-допущение)
            ParamOrigin.QUESTIONNAIRE,     # ИЗ ЭСКИЗА: working_length_mm=2515
        ],
        strength_component_class="корпус, крышки, патрубки, фланцы",
        notes="Диаметр НЕ равен DN100 (присоединительный) — см. tube_engineering.py.",
    ),
    TubeCadPlanItem(
        path="корпус_трубный/загрузочный_патрубок", name="Загрузочный патрубок DN100",
        parent_path="корпус_трубный",
        required_params=["dn_присоединения_мм", "высота_загрузки_от_пола_мм"],
        param_origin=[ParamOrigin.QUESTIONNAIRE, ParamOrigin.QUESTIONNAIRE],  # оба ИЗ ЭСКИЗА
        strength_component_class="корпус, крышки, патрубки, фланцы",
    ),
    TubeCadPlanItem(
        path="корпус_трубный/выгрузочный_патрубок", name="Выгрузочный патрубок",
        parent_path="корпус_трубный",
        required_params=["dn_выгрузки_мм", "высота_выгрузки_от_пола_мм"],
        param_origin=[ParamOrigin.NOT_YET_DEFINED, ParamOrigin.QUESTIONNAIRE],  # диаметр выгрузки не задан заказчиком
        strength_component_class="корпус, крышки, патрубки, фланцы",
    ),
    TubeCadPlanItem(
        path="шнек", name="Шнек", parent_path=None,
        required_params=["шаг_витка_мм"],
        param_origin=[ParamOrigin.ENGINEERING_CORE],  # BLOCKED
        strength_component_class=None,  # сама сборка "шнек" не проверяется — проверяются её потомки
    ),
    TubeCadPlanItem(
        path="шнек/вал_труба", name="Вал/труба шнека", parent_path="шнек",
        required_params=["диаметр_вала_мм", "материал_вала", "крутящий_момент_нм"],
        param_origin=[ParamOrigin.ENGINEERING_CORE, ParamOrigin.QUESTIONNAIRE, ParamOrigin.ENGINEERING_CORE],
        strength_component_class="вал шнека",
    ),
    TubeCadPlanItem(
        path="шнек/спираль", name="Спираль шнека", parent_path="шнек",
        required_params=["диаметр_шнека_мм", "шаг_витка_мм", "толщина_витка_мм", "материал_витка"],
        param_origin=[ParamOrigin.ENGINEERING_CORE, ParamOrigin.ENGINEERING_CORE,
                      ParamOrigin.NOT_YET_DEFINED, ParamOrigin.QUESTIONNAIRE],
        strength_component_class="спираль шнека и её крепления",
    ),
    TubeCadPlanItem(
        path="шнек/цапфы", name="Цапфы шнека", parent_path="шнек",
        required_params=["диаметр_цапфы_мм", "материал_цапфы"],
        param_origin=[ParamOrigin.ENGINEERING_CORE, ParamOrigin.QUESTIONNAIRE],
        strength_component_class="труба/цапфы",
    ),
    TubeCadPlanItem(
        path="подшипниковые_узлы", name="Подшипниковые узлы", parent_path=None,
        required_params=["радиальная_нагрузка_н", "осевая_нагрузка_н", "частота_вращения_об_мин"],
        param_origin=[ParamOrigin.ENGINEERING_CORE, ParamOrigin.ENGINEERING_CORE, ParamOrigin.ENGINEERING_CORE],
        strength_component_class="подшипники и корпуса подшипников",
        notes="Типоразмер — из каталога поставщика (CATALOG) после того, как появятся нагрузки/обороты.",
    ),
    TubeCadPlanItem(
        path="приводная_группа", name="Приводная группа (мотор-редуктор)", parent_path=None,
        required_params=["мощность_квт", "передаточное_отношение", "расположение_привода"],
        param_origin=[ParamOrigin.ENGINEERING_CORE, ParamOrigin.ENGINEERING_CORE, ParamOrigin.QUESTIONNAIRE],
        strength_component_class="крепления привода",
        notes=(
            "расположение_привода сейчас в КОНФЛИКТЕ (текст эскиза — низ, графика — верх) — "
            "см. core/tube_engineering.py::DriveLocationConflictReport; компоновка не фиксируется "
            "до подтверждения заказчика."
        ),
    ),
    TubeCadPlanItem(
        path="опорная_рама", name="Опорная рама", parent_path=None,
        required_params=["габарит_рамы_мм", "материал_рамы", "точки_опирания"],
        param_origin=[ParamOrigin.NOT_YET_DEFINED, ParamOrigin.QUESTIONNAIRE, ParamOrigin.NOT_YET_DEFINED],
        strength_component_class="рама, стойки, плиты",
    ),
    TubeCadPlanItem(
        path="защитные_кожухи", name="Защитные кожухи", parent_path=None,
        required_params=["зона_ограждения"],
        param_origin=[ParamOrigin.NOT_YET_DEFINED],
        participates_in_strength=False,  # ограждения — не силовой элемент в типовом составе раздела 10
        strength_component_class="ограждения",
    ),
    TubeCadPlanItem(
        path="крепёж", name="Крепёж (болты/шпильки/гайки)", parent_path=None,
        required_params=["класс_прочности", "количество_комплектов"],
        param_origin=[ParamOrigin.CATALOG, ParamOrigin.CAD_READBACK],
        strength_component_class="болтовые соединения",
    ),
]


def plan_by_path(plan: list[TubeCadPlanItem] = TUBE_SAND_001_CAD_PLAN) -> dict[str, TubeCadPlanItem]:
    return {item.path: item for item in plan}


def validate_plan_tree(plan: list[TubeCadPlanItem] = TUBE_SAND_001_CAD_PLAN) -> list[str]:
    """Проверяет, что у каждого parent_path есть реальный родитель в этом же плане (дерево не порвано)."""
    paths = {item.path for item in plan}
    issues = []
    for item in plan:
        if item.parent_path is not None and item.parent_path not in paths:
            issues.append(f"{item.path}: parent_path={item.parent_path!r} не найден в плане.")
    return issues


@dataclass
class BomPosition:
    """
    Одна строка РЕАЛЬНОЙ BOM — поля по прямому перечислению задания. Только
    для позиций, реально прочитанных из CAD (source=CAD_READBACK); плановые
    позиции (TubeCadPlanItem) в BomPosition не превращаются автоматически —
    designation здесь ВСЕГДА обозначение из чертежа/сборки, никогда
    "уточнить_по_BOM" и никогда не выдумывается.
    """

    designation: str                  # обозначение по чертежу/спецификации — обязательно, не placeholder
    name: str
    configuration: Optional[str] = None
    quantity: Optional[int] = None
    material: Optional[str] = None
    mass_kg: Optional[float] = None
    make_or_buy: str = "неизвестно"    # "изготовление" | "покупное" | "неизвестно"
    parent_assembly: Optional[str] = None
    suppressed: bool = False
    revision: str = ""
    strength_component_class: Optional[str] = None  # для build_strength_registry_from_bom()
    source: str = "cad_обратное_чтение"


@dataclass
class BomReadbackResult:
    ok: bool
    positions: list[BomPosition] = field(default_factory=list)
    blocked_reason: Optional[str] = None


def build_bom_from_cad_readback(adapter: "CadAdapter", plan: list[TubeCadPlanItem] = TUBE_SAND_001_CAD_PLAN) -> BomReadbackResult:
    """
    Единственный законный способ получить РЕАЛЬНУЮ BOM для TUBE-SAND-001 —
    честно проверяет доступность моста (как и весь остальной CAD-адаптер,
    раздел 5/12) и НИКОГДА не подставляет позиции из плана в качестве
    настоящей BOM. `plan` здесь используется только чтобы в сообщении об
    ошибке назвать, сколько позиций ОЖИДАЕТСЯ прочитать, когда мост
    станет доступен — не как источник данных.
    """
    if not adapter.can_read():
        return BomReadbackResult(
            ok=False,
            blocked_reason=(
                "Чтение реальной BOM из CAD недоступно: SolidWorks/коннектор не отвечает из этой "
                "среды (см. cad_adapter.interface.LocalBridgeCadAdapter.can_read()==False). Плановых "
                f"позиций в дереве TUBE-SAND-001: {len(plan)} — они НЕ являются BOM и не используются "
                "как замена. Нужен реальный прогон на рабочей станции с открытой сборкой TUBE-SAND-001."
            ),
        )
    # Живой прогон на рабочей станции — не реализовано в этой сессии (нет самой CAD-модели
    # TUBE-SAND-001, строить которую из выдуманных размеров прямо запрещено заданием).
    return BomReadbackResult(
        ok=False,
        blocked_reason=(
            "Мост отвечает, но чтение фактической BOM этим адаптером ещё не реализовано. "
            "Наличие сборки TUBE-SAND-001, её состав и параметры этим вызовом не проверялись."
        ),
    )
