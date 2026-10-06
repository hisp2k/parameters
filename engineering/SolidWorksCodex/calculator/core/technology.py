# -*- coding: utf-8 -*-
"""
Технологические процессы (раздел 7 задания, опирается на разделы 15-17):
подетально, по сборкам и по изделию в целом.

Раздел 16 прямо требует: "не выводи из названия станка неизвестные
возможности" — поэтому КАЖДАЯ операция здесь получает статус через
`reference.equipment_registry.check_operation_feasible()` и явный флаг
`requires_equipment_confirmation`, а не проставляется "годен" по умолчанию:
ни одна позиция реестра оборудования не помечена `verified_by_datasheet=True`
на этом этапе, поэтому "требует подтверждения паспортом" честно верно для
КАЖДОЙ операции сейчас, а не только для непроверенных возможностей
(`UNCONFIRMED_CAPABILITIES` — токарная обработка, листогибка, навивка
спирали), для которых оборудование в реестре просто отсутствует.

Раздел 7 отдельно требует: "обоснуй изготовление спирали шнека отдельно от
простой разбортовки листа" — см. `screw_flight_process()`: это не одна
операция, а явный выбор между двумя технологически разными и НЕ
взаимозаменяемыми вариантами, ни один из которых сейчас не подтверждён
оборудованием предприятия.

Раздел 17 требует различать машинное время, время рабочего и
продолжительность операции — `OperationStep` хранит все три поля отдельно,
а не одно "время операции".

ЧЕСТНАЯ ГРАНИЦА: точные нормы времени (машинное/штучное) этого предприятия
не задокументированы построчно в переданных материалах. Числа ниже —
ОБЩЕИНЖЕНЕРНЫЕ ОРИЕНТИРЫ по порядку величины типовых операций
листообработки/механообработки/сварки, каждое явно помечено
`time_basis` = "ориентир... требует проверки нормативом предприятия", а не
выдаётся за подтверждённый норматив (раздел 17: "не выдумывай нормативные
показатели"). Формула развёртки геликоидной поверхности спирали шнека
намеренно НЕ приводится численно — существующие формулы такого рода легко
перепутать местами, а раздел 8 требует не выдумывать/не путать нормативные
данные; вместо формулы — явное указание, что развёртка требует проверенного
источника (справочник конструктора шнековых конвейеров, ГОСТ или CAD-модуль
разворачивания) перед выпуском в производство.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from calculator.reference.equipment_registry import (
    EQUIPMENT_REGISTRY, UNCONFIRMED_CAPABILITIES, check_operation_feasible,
)


TIME_BASIS_ILLUSTRATIVE = (
    "ориентир по типовым операциям листообработки/механообработки/сварки — "
    "требует проверки действующим нормативом времени предприятия (раздел 17)"
)


@dataclass
class OperationStep:
    """
    Одна операция технологического процесса. Раздел 17: машинное время,
    время рабочего и продолжительность операции — три РАЗНЫХ числа (не
    подразумевают друг друга): напр. для лазерной резки машинное время может
    превышать активное время рабочего (автоматический цикл), а для ручной
    зачистки/сварки — наоборот, активное время рабочего равно или больше
    "машинного" (переносного инструмента).
    """

    name: str
    equipment_id: Optional[str]          # None — оборудование в реестре отсутствует вовсе
    requirement: str                     # что конкретно требуется от оборудования/оснастки
    tooling: str = ""
    control: str = "контроль размеров/визуальный контроль по чертежу"
    machine_time_min: float = 0.0        # автоматический цикл станка
    labor_time_min: float = 0.0          # активное время рабочего
    duration_min: float = 0.0            # продолжительность операции целиком (вкл. наладку/установку)
    time_basis: str = TIME_BASIS_ILLUSTRATIVE
    unconfirmed_capability: Optional[str] = None   # одна из UNCONFIRMED_CAPABILITIES, если применимо
    feasibility_note: str = field(default="", init=False)
    requires_equipment_confirmation: bool = field(default=True, init=False)

    def __post_init__(self) -> None:
        notes: list[str] = []
        if self.unconfirmed_capability:
            if self.unconfirmed_capability not in UNCONFIRMED_CAPABILITIES:
                raise ValueError(
                    f"unconfirmed_capability={self.unconfirmed_capability!r} не входит в "
                    f"UNCONFIRMED_CAPABILITIES={UNCONFIRMED_CAPABILITIES} — не выдумываем новую "
                    "категорию непроверенной возможности мимо реестра оборудования."
                )
            notes.append(
                f"Возможность {self.unconfirmed_capability!r} НЕ подтверждена в реестре оборудования "
                "(reference/equipment_registry.py) — нужен станок/оснастка и подтверждение паспортом "
                "прежде, чем эта операция может считаться выполнимой на этом предприятии."
            )
        if self.equipment_id is not None:
            eq = EQUIPMENT_REGISTRY.get(self.equipment_id)
            if eq is None:
                raise ValueError(f"equipment_id={self.equipment_id!r} отсутствует в EQUIPMENT_REGISTRY.")
            notes.append(check_operation_feasible(self.equipment_id, self.requirement))
            self.requires_equipment_confirmation = not eq.verified_by_datasheet
        else:
            if not self.unconfirmed_capability:
                notes.append(f"Оборудование не назначено для операции {self.requirement!r} — требуется подбор станка.")
            self.requires_equipment_confirmation = True
        self.feasibility_note = " ".join(notes)


@dataclass
class PartProcess:
    """Технология одной детали (раздел 7: материал/заготовка, размеры и припуски, операции, контроль)."""

    bom_position: str
    component_class: str
    material: str
    blank_description: str
    dimensions_note: str
    allowances_note: str
    operations: list[OperationStep] = field(default_factory=list)
    control: str = "контроль размеров по чертежу, визуальный контроль качества поверхности"
    purchased_item: bool = False
    incoming_inspection_note: str = ""

    @property
    def total_machine_time_min(self) -> float:
        return round(sum(op.machine_time_min for op in self.operations), 2)

    @property
    def total_labor_time_min(self) -> float:
        return round(sum(op.labor_time_min for op in self.operations), 2)

    @property
    def total_duration_min(self) -> float:
        return round(sum(op.duration_min for op in self.operations), 2)

    @property
    def unconfirmed_operations(self) -> list[OperationStep]:
        return [op for op in self.operations if op.requires_equipment_confirmation]


@dataclass
class AssemblyProcess:
    """
    Технология узла (раздел 7: сварка узла отдельно от подетальной обработки,
    сборка, контроль).
    """

    name: str
    welding_operations: list[OperationStep] = field(default_factory=list)
    assembly_operations: list[OperationStep] = field(default_factory=list)
    control: str = (
        "визуальный и измерительный контроль сварных швов (ВИК) по чертежу, "
        "проверка соосности/зазоров по сборочному чертежу"
    )

    @property
    def _all_operations(self) -> list[OperationStep]:
        return self.welding_operations + self.assembly_operations

    @property
    def total_machine_time_min(self) -> float:
        return round(sum(op.machine_time_min for op in self._all_operations), 2)

    @property
    def total_labor_time_min(self) -> float:
        return round(sum(op.labor_time_min for op in self._all_operations), 2)

    @property
    def total_duration_min(self) -> float:
        return round(sum(op.duration_min for op in self._all_operations), 2)

    @property
    def unconfirmed_operations(self) -> list[OperationStep]:
        return [op for op in self._all_operations if op.requires_equipment_confirmation]


@dataclass
class ScrewFlightMethod:
    """
    Один из двух НЕ взаимозаменяемых вариантов изготовления спирали шнека —
    раздел 7: обоснование отдельно от простой разбортовки листа.
    """

    method_name: str
    description: str
    justification: str
    equipment_confirmed: bool
    operations: list[OperationStep] = field(default_factory=list)

    @property
    def total_machine_time_min(self) -> float:
        return round(sum(op.machine_time_min for op in self.operations), 2)

    @property
    def total_labor_time_min(self) -> float:
        return round(sum(op.labor_time_min for op in self.operations), 2)

    @property
    def total_duration_min(self) -> float:
        return round(sum(op.duration_min for op in self.operations), 2)


def screw_flight_process(diameter_mm: float, step_mm: float, working_length_mm: float) -> list[ScrewFlightMethod]:
    """
    Раздел 7: изготовление спирали шнека — геликоидная (винтовая) поверхность,
    а НЕ простая разбортовка плоского листа (в отличие от, например, панелей
    корпуса) — поэтому здесь два принципиально разных варианта, и выбор
    между ними НЕ делается автоматически:

    1) "навивка_на_оправке" — непрерывная навивка полосы на оправку с
       растяжкой до нужного шага. Технологически предпочтительна (меньше
       сварных швов на спирали), но соответствующее оборудование (навивочный
       станок/оснастка) в реестре предприятия ОТСУТСТВУЕТ (раздел 16 —
       "навивка/формование спирали шнека" прямо в UNCONFIRMED_CAPABILITIES).

    2) "секторная_сборка_из_плоских_заготовок" — кольцевые секторы (по одному
       на виток или с дроблением под габарит листа лазера) вырезаются
       ПЛОСКИМИ на лазере, затем каждый формуется (растягивается/подгибается)
       до нужного шага и сваривается с соседними в сплошную спираль. Требует
       намного больше сварных швов на самой спирали (каждый виток/сектор —
       отдельный шов), что должно учитываться отдельно в строгости
       требований раздела 10 к позиции "спираль шнека и её крепления"
       (расчёт прочности должен покрывать именно эти сварные швы, а не
       считать спираль монолитной).

    Развёртка плоской заготовки геликоида (радиусы/угол сектора) НЕ считается
    здесь численно: готовой проверенной формулы под рукой нет, а
    приблизительная формула "на глаз" рискует быть перепутанной и выданной за
    подтверждённую (раздел 8 — не путай нормативные данные). Развёртку нужно
    получить из проверенного источника (справочник конструктора шнековых
    конвейеров/ГОСТ, либо инструмент разворачивания листового тела в самой
    CAD-модели после подключения раздела 5) ПЕРЕД выпуском чертежей заготовки.
    """
    if step_mm <= 0:
        raise ValueError("step_mm должен быть положительным для оценки числа витков.")
    n_turns = working_length_mm / step_mm  # простая арифметика, не нормативная величина

    winding = ScrewFlightMethod(
        method_name="навивка_на_оправке",
        description=(
            f"Непрерывная навивка полосы на оправку диаметром ~{diameter_mm} мм с шагом {step_mm} мм "
            f"на длину {working_length_mm} мм (~{n_turns:.1f} витков), растяжка до нужного шага, "
            "минимум сварных швов на самой спирали (только стыки полосы и её крепление к трубе)."
        ),
        justification=(
            "Технологически предпочтительный способ для сплошной спирали, но требует навивочного "
            "станка/оснастки, которых нет в реестре оборудования предприятия — недоступен без "
            "приобретения оборудования или размещения заказа на стороне (раздел 16)."
        ),
        equipment_confirmed=False,
        operations=[
            OperationStep(
                name="Навивка полосы на оправку с растяжкой до шага",
                equipment_id=None,
                requirement="навивка/формование спирали шнека",
                unconfirmed_capability="навивка/формование спирали шнека",
                machine_time_min=0.0, labor_time_min=0.0, duration_min=0.0,
                time_basis="не оценивается — оборудование не подтверждено, оценка времени была бы выдумкой",
            ),
        ],
    )

    n_segments = max(1, round(n_turns))
    sector = ScrewFlightMethod(
        method_name="секторная_сборка_из_плоских_заготовок",
        description=(
            f"~{n_segments} кольцевых секторов (по одному на виток, ~{n_turns:.1f} витков на "
            f"{working_length_mm} мм длины) вырезаются плоскими на лазере, формуются под шаг {step_mm} мм "
            "и последовательно свариваются друг с другом и с трубой — БЕЗ навивочного оборудования."
        ),
        justification=(
            "Доступен на текущем оборудовании (лазерная резка листа + сварочные столы), но даёт "
            f"~{n_segments} дополнительных сварных швов НА САМОЙ СПИРАЛИ (не путать с креплением "
            "спирали к трубе) — раздел 10 требует, чтобы позиция 'спираль шнека и её крепления' "
            "в реестре прочности покрывала именно эти швы, а не считала спираль монолитной деталью. "
            "Развёртка плоского сектора под геликоид требует ПРОВЕРЕННОГО источника перед выпуском "
            "чертежа заготовки — см. docstring screw_flight_process()."
        ),
        equipment_confirmed=True,
        operations=[
            OperationStep(
                name=f"Лазерная резка {n_segments} секторных заготовок",
                equipment_id="laser_sheet_tube", requirement="резка листовых секторных заготовок спирали",
                tooling="программа раскроя листа (развёртка сектора — проверить перед выпуском)",
                machine_time_min=8.0 * n_segments, labor_time_min=2.0 * n_segments, duration_min=9.0 * n_segments,
            ),
            OperationStep(
                name=f"Формовка {n_segments} секторов под шаг {step_mm} мм",
                equipment_id=None, requirement="формование листового сектора под геликоидный шаг",
                tooling="оправка/пресс-форма для растяжки сектора (уточнить оснастку)",
                machine_time_min=0.0, labor_time_min=25.0 * n_segments, duration_min=30.0 * n_segments,
                time_basis="ориентир (ручная/полуручная формовка) — требует проверки нормативом и оснасткой",
            ),
            OperationStep(
                name=f"Сварка {max(0, n_segments - 1)} стыков секторов между собой + приварка к трубе",
                equipment_id="welding_tables", requirement="сварка стыков спирали и приварка к трубе",
                tooling="сварочный полуавтомат/инвертор (не в реестре станочного оборудования отдельно)",
                machine_time_min=0.0, labor_time_min=20.0 * max(1, n_segments), duration_min=25.0 * max(1, n_segments),
            ),
            OperationStep(
                name="Зачистка сварных швов спирали",
                equipment_id="belt_grinder_heden_sf150v", requirement="зачистка сварных швов спирали",
                machine_time_min=0.0, labor_time_min=6.0 * max(1, n_segments), duration_min=7.0 * max(1, n_segments),
            ),
        ],
    )

    return [winding, sector]


@dataclass
class ProductRoute:
    """Раздел 7: маршрут изделия в целом — порядок укрупнённых этапов."""

    steps: list[str] = field(default_factory=lambda: [
        "1. Входной контроль покупных изделий (двигатель, редуктор, подшипники, муфта, крепёж)",
        "2. Заготовительные операции (лазерная/плазменная резка листа и трубы, отрезка на ленточной пиле)",
        "3. Механическая обработка (фрезерная/сверлильная — по позициям, требующим точных отверстий/посадок; "
        "токарная обработка — ТРЕБУЕТ ПОДТВЕРЖДЕНИЯ ОБОРУДОВАНИЯ, раздел 16)",
        "4. Изготовление спирали шнека — по выбранному и подтверждённому варианту (см. screw_flight_process())",
        "5. Сварка узлов (рама, корпус, крепления привода, спираль/труба)",
        "6. Зачистка и электрохимическая очистка сварных швов",
        "7. Сборка узла привода и общая сборка изделия",
        "8. Контроль готового изделия (геометрия, сварные швы, соосность, при необходимости — обкатка привода)",
        "9. Упаковка и подготовка к отгрузке",
    ])


@dataclass
class TechnologyPackage:
    parts: list[PartProcess] = field(default_factory=list)
    assemblies: list[AssemblyProcess] = field(default_factory=list)
    flight_methods: list[ScrewFlightMethod] = field(default_factory=list)
    route: ProductRoute = field(default_factory=ProductRoute)
    warnings: list[str] = field(default_factory=list)

    @property
    def total_machine_time_min(self) -> float:
        return round(
            sum(p.total_machine_time_min for p in self.parts)
            + sum(a.total_machine_time_min for a in self.assemblies),
            2,
        )

    @property
    def total_labor_time_min(self) -> float:
        return round(
            sum(p.total_labor_time_min for p in self.parts)
            + sum(a.total_labor_time_min for a in self.assemblies),
            2,
        )

    @property
    def total_duration_min(self) -> float:
        return round(
            sum(p.total_duration_min for p in self.parts)
            + sum(a.total_duration_min for a in self.assemblies),
            2,
        )

    def unconfirmed_operations_report(self) -> list[str]:
        """Раздел 16/17: явный список всего, что требует подтверждения перед выпуском в производство."""
        report: list[str] = []
        for p in self.parts:
            for op in p.unconfirmed_operations:
                report.append(f"{p.component_class} / {op.name}: {op.feasibility_note}")
        for a in self.assemblies:
            for op in a.unconfirmed_operations:
                report.append(f"{a.name} / {op.name}: {op.feasibility_note}")
        return report


def _laser_cut_op(name: str, requirement: str, minutes: float = 20.0) -> OperationStep:
    return OperationStep(
        name=name, equipment_id="laser_sheet_tube", requirement=requirement,
        machine_time_min=minutes, labor_time_min=minutes * 0.25, duration_min=minutes * 1.15,
    )


def _weld_op(name: str, requirement: str, minutes: float = 30.0) -> OperationStep:
    return OperationStep(
        name=name, equipment_id="welding_tables", requirement=requirement,
        machine_time_min=0.0, labor_time_min=minutes, duration_min=minutes * 1.2,
    )


def _mill_op(name: str, requirement: str, minutes: float = 15.0) -> OperationStep:
    return OperationStep(
        name=name, equipment_id="vmc_850p", requirement=requirement,
        machine_time_min=minutes, labor_time_min=minutes * 0.3, duration_min=minutes * 1.25,
    )


def _turning_op(name: str, requirement: str) -> OperationStep:
    # Раздел 16: токарной обработки НЕТ в реестре оборудования — честно оставляем
    # equipment_id=None и unconfirmed_capability, а не подставляем произвольный станок.
    return OperationStep(
        name=name, equipment_id=None, requirement=requirement,
        unconfirmed_capability="токарная обработка",
        machine_time_min=0.0, labor_time_min=0.0, duration_min=0.0,
        time_basis="не оценивается — оборудование не подтверждено, оценка времени была бы выдумкой",
    )


def _bending_op(name: str, requirement: str) -> OperationStep:
    return OperationStep(
        name=name, equipment_id=None, requirement=requirement,
        unconfirmed_capability="листогибочная операция (гибка листа прессом)",
        machine_time_min=0.0, labor_time_min=0.0, duration_min=0.0,
        time_basis="не оценивается — оборудование не подтверждено, оценка времени была бы выдумкой",
    )


def build_default_technology_package(
    diameter_mm: float, step_mm: float, working_length_mm: float,
) -> TechnologyPackage:
    """
    Технология по типовому составу раздела 10 (core.strength_coverage.
    DEFAULT_TYPICAL_SCOPE), с учётом РЕАЛЬНОГО реестра оборудования — не
    привязана к конкретной подтверждённой BOM-версии сборки (её пока нет,
    см. cad_adapter/interface.py), поэтому bom_position везде
    "уточнить_по_BOM", как и в strength_coverage.py.
    """
    parts: list[PartProcess] = []

    parts.append(PartProcess(
        bom_position="уточнить_по_BOM", component_class="труба/цапфы",
        material="сталь (уточнить марку по чертежу)",
        blank_description="труба стальная, отрезанная в размер",
        dimensions_note=f"длина ~{working_length_mm} мм, диаметр — по чертежу вала",
        allowances_note="припуск на торцовку/обработку цапф — по чертежу",
        operations=[
            OperationStep(
                name="Отрезка трубы в размер", equipment_id="bandsaw_als4040d",
                requirement="отрезка трубы в размер", machine_time_min=6.0, labor_time_min=3.0, duration_min=8.0,
            ),
            _turning_op("Проточка цапф и посадочных поверхностей", "токарная обработка цапф трубы вала"),
            OperationStep(
                name="Сверление/фрезерование крепёжных отверстий под спираль/опоры",
                equipment_id="drill_stalex_shd40", requirement="сверление крепёжных отверстий трубы",
                machine_time_min=10.0, labor_time_min=8.0, duration_min=14.0,
            ),
        ],
    ))

    parts.append(PartProcess(
        bom_position="уточнить_по_BOM", component_class="вал шнека",
        material="сталь (уточнить марку по чертежу)",
        blank_description="круглый прокат/поковка вала",
        dimensions_note="по чертёжным размерам вала (диаметр/длина/шпоночные пазы)",
        allowances_note="припуск под окончательную токарную обработку и шлифовку посадочных мест",
        operations=[
            OperationStep(
                name="Отрезка заготовки вала в размер", equipment_id="bandsaw_als4040d",
                requirement="отрезка круглого проката вала", machine_time_min=5.0, labor_time_min=3.0, duration_min=7.0,
            ),
            _turning_op("Черновая и чистовая токарная обработка вала", "токарная обработка вала под посадочные диаметры"),
            _mill_op("Фрезерование шпоночного паза", "фрезерование шпоночного паза вала", minutes=20.0),
        ],
    ))

    for cls in ("корпус, крышки, патрубки, фланцы", "рама, стойки, плиты", "ограждения", "проушины и транспортные крепления"):
        parts.append(PartProcess(
            bom_position="уточнить_по_BOM", component_class=cls,
            material="листовой прокат Ст3 (уточнить марку/толщину по чертежу)",
            blank_description="плоская заготовка, вырезанная на лазере",
            dimensions_note="по разворотным чертежам детали",
            allowances_note="припуск на сварочную усадку по типовой практике — уточнить для конкретных швов",
            operations=[
                _laser_cut_op(f"Лазерная резка заготовок: {cls}", f"резка листовых заготовок: {cls}", minutes=18.0),
                _bending_op(f"Гибка листовых элементов: {cls}", f"листогибочная операция: {cls}"),
                _weld_op(f"Сварка узла: {cls}", f"сварка листовых элементов: {cls}", minutes=35.0),
                OperationStep(
                    name=f"Зачистка сварных швов: {cls}", equipment_id="belt_grinder_heden_sf150v",
                    requirement=f"зачистка сварных швов: {cls}", machine_time_min=0.0,
                    labor_time_min=12.0, duration_min=14.0,
                ),
            ],
        ))

    for cls in ("крепления привода", "промежуточные опоры"):
        parts.append(PartProcess(
            bom_position="уточнить_по_BOM", component_class=cls,
            material="листовой/сортовой прокат Ст3 (уточнить по чертежу)",
            blank_description="сварная конструкция из лазерных/пильных заготовок",
            dimensions_note="по сборочному чертежу узла крепления",
            allowances_note="припуск под финишную механическую обработку посадочных мест — по чертежу",
            operations=[
                _laser_cut_op(f"Резка заготовок: {cls}", f"резка заготовок: {cls}", minutes=16.0),
                _weld_op(f"Сварка: {cls}", f"сварка: {cls}", minutes=28.0),
                _mill_op(f"Финишная обработка посадочных мест: {cls}", f"фрезерование посадочных мест: {cls}", minutes=18.0),
            ],
        ))

    for cls, item_name in (
        ("подшипники и корпуса подшипников", "подшипниковый узел (покупной подшипник + корпус)"),
        ("муфта/шпонка/шлицы", "муфта (покупная)"),
    ):
        parts.append(PartProcess(
            bom_position="уточнить_по_BOM", component_class=cls,
            material="покупное изделие + собственный корпус/шпонка (уточнить состав по BOM)",
            blank_description="частично покупное изделие",
            dimensions_note="по каталогу поставщика (не подтверждён — см. reference/drive_catalog.py, раздел 11)",
            allowances_note="н/д для покупной части; для собственного корпуса — по чертежу",
            purchased_item=True,
            incoming_inspection_note=(
                f"Входной контроль покупного изделия ({item_name}): комплектность, сертификат/паспорт, "
                "визуальный осмотр на повреждения, соответствие обозначению по спецификации заказа — "
                "перед запуском в сборку."
            ),
            operations=[
                OperationStep(
                    name=f"Механическая обработка корпуса: {cls}", equipment_id="vmc_850p",
                    requirement=f"фрезерование посадочных поверхностей корпуса: {cls}",
                    machine_time_min=22.0, labor_time_min=7.0, duration_min=27.0,
                ),
            ],
        ))

    parts.append(PartProcess(
        bom_position="уточнить_по_BOM", component_class="межсекционные соединения",
        material="листовой/сортовой прокат Ст3 (уточнить по чертежу)",
        blank_description="фланцевые заготовки, вырезанные на лазере",
        dimensions_note="по чертежу фланцевого соединения секций",
        allowances_note="по чертежу",
        operations=[
            _laser_cut_op("Резка фланцевых заготовок межсекционного соединения", "резка фланцевых заготовок", minutes=14.0),
            OperationStep(
                name="Сверление отверстий под болтовое соединение", equipment_id="drill_stalex_shd40",
                requirement="сверление отверстий под болтовое соединение секций",
                machine_time_min=8.0, labor_time_min=6.0, duration_min=11.0,
            ),
            _weld_op("Приварка фланца к трубе секции", "сварка фланца с трубой секции", minutes=22.0),
        ],
    ))

    parts.append(PartProcess(
        bom_position="уточнить_по_BOM", component_class="болтовые соединения",
        material="покупной крепёж (болты/гайки/шайбы, класс прочности — уточнить по чертежу)",
        blank_description="покупное изделие",
        dimensions_note="по спецификации крепежа чертежа",
        allowances_note="н/д",
        purchased_item=True,
        incoming_inspection_note="Входной контроль партии крепежа: маркировка класса прочности, визуальный осмотр, выборочный обмер.",
        operations=[],
    ))

    warnings = [
        "Времена операций — ориентир (см. time_basis у каждой операции), требуют проверки "
        "нормативом времени предприятия перед использованием в производственном планировании (раздел 17).",
        "Токарная обработка и листогибочная операция отмечены как требующие подтверждения оборудования "
        "(раздел 16) — в реестре оборудования предприятия соответствующих станков нет.",
        "bom_position везде 'уточнить_по_BOM' — реальная BOM-версия сборки ещё не подключена (раздел 5/12).",
    ]

    assemblies = [
        AssemblyProcess(
            name="Сборка секции шнека (труба/цапфы + спираль + крепления)",
            welding_operations=[
                OperationStep(
                    name="Приварка спирали к трубе (по выбранному варианту изготовления спирали)",
                    equipment_id="welding_tables", requirement="приварка спирали к трубе вала",
                    machine_time_min=0.0, labor_time_min=45.0, duration_min=55.0,
                ),
            ],
            assembly_operations=[
                OperationStep(
                    name="Контрольная сборка секции с проверкой биения/соосности",
                    equipment_id=None, requirement="контрольная сборка секции шнека",
                    machine_time_min=0.0, labor_time_min=15.0, duration_min=20.0,
                    time_basis="ориентир — ручная контрольная операция, требует проверки нормативом",
                ),
            ],
        ),
        AssemblyProcess(
            name="Общая сборка изделия (рама, корпус, привод, секции шнека)",
            welding_operations=[],
            assembly_operations=[
                OperationStep(
                    name="Установка и центровка привода", equipment_id=None,
                    requirement="монтаж и центровка привода на раме",
                    machine_time_min=0.0, labor_time_min=40.0, duration_min=50.0,
                    time_basis="ориентир — ручная сборочная операция, требует проверки нормативом",
                ),
                OperationStep(
                    name="Общая сборка секций, корпуса и ограждений", equipment_id=None,
                    requirement="общая сборка изделия",
                    machine_time_min=0.0, labor_time_min=60.0, duration_min=80.0,
                    time_basis="ориентир — ручная сборочная операция, требует проверки нормативом",
                ),
            ],
        ),
    ]

    flight_methods = screw_flight_process(diameter_mm, step_mm, working_length_mm)

    return TechnologyPackage(parts=parts, assemblies=assemblies, flight_methods=flight_methods, warnings=warnings)
