# -*- coding: utf-8 -*-
"""
Модель "подтверждённой проверки" (раздел 1.А задания — исправление
блокировки выпуска).

Раньше `release_gate.py` считал позицию BOM "закрытой по прочности" только
по тому, что у неё выставлен `method != NOT_DONE`, а модуль (привод/CAD/КД/
технология) — только по булеву `done=True`. Это позволяло "разблокировать"
выпуск, просто проставив значения полей, без единого реального числа
расчёта. Это прямо запрещено заданием: "Нельзя разрешить выпуск изменением
набора булевых флагов."

VerificationRecord — то, что ДОЛЖНО существовать, чтобы проверка считалась
выполненной:
- результат расчёта (result_value/result_unit) и критерий (допустимое
  значение и его источник) — иначе это не проверка, а декларация;
- на каких исходных данных считали (input_fingerprint — хэш анкеты/раздела
  проекта на момент расчёта) и для какой ревизии изделия (product_revision) —
  чтобы проверка, посчitанная для старых данных, не выглядела действительной
  после того, как требования изменились (раздел 1.Б);
- версия методики (methodology_version) — на случай, если сама формула
  изменится;
- кто посчитал (computed_by/computed_by_role) и, ОТДЕЛЬНО, кто проверил
  результат (reviewed_by/reviewed_by_role) — раздел 1.А прямо требует
  "техническую проверку другим специалистом", то есть reviewed_by не может
  быть равен computed_by;
- итоговый вердикт (passed) — сам факт наличия числа не означает, что оно
  проходит критерий.

Эта запись используется и для прочности (StrengthItem.verification), и для
модулей (ModuleStatus) через одинаковый принцип: "есть число + критерий +
кто проверил, и это относится к ТЕКУЩИМ данным" — единственное основание
считать пункт закрытым.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Optional

from calculator.core.roles import Role


def _finite_number(value) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


#: Направление критерия — раздел "Реализация и проверка" (продолжение,
#: 17.09.2026): раньше `passed()` жёстко проверял только `result <= limit`,
#: что делает НЕВОЗМОЖНЫМ честно закрыть проверку типа "ресурс подшипника
#: L10h должен быть НЕ МЕНЕЕ требуемого срока" — единственный способ был
#: соврать про смысл числа (напр. записать 1/L10h). CRITERION_AT_MOST —
#: прежнее поведение по умолчанию (обратная совместимость всех уже
#: сохранённых проектов и тестов); CRITERION_AT_LEAST — новое, для
#: критериев вида "не менее" (ресурс, статическая грузоподъёмность,
#: коэффициент запаса устойчивости и т.п.). Значение ВСЕГДА должно быть
#: явно указано вызывающим кодом расчёта — это не эвристика по названию.
CRITERION_AT_MOST = "не_более"
CRITERION_AT_LEAST = "не_менее"
VALID_CRITERION_DIRECTIONS = (CRITERION_AT_MOST, CRITERION_AT_LEAST)


@dataclass
class VerificationRecord:
    # --- что именно проверяли и с каким результатом ---
    criterion_description: str            # что проверяется, напр. "изгибная прочность вала"
    result_value: Optional[float]         # расчётное значение (напр. эквивалентное напряжение)
    result_unit: str
    criterion_limit: Optional[float]      # допустимое значение (предел/критерий)
    criterion_source: str                 # источник критерия: методика/ГОСТ/паспорт — не "уточнить"
    safety_factor: Optional[float] = None
    # "не_более" (по умолчанию, прежнее поведение) — result_value должен быть
    # <= criterion_limit (напряжение, деформация и т.п.); "не_менее" —
    # result_value должен быть >= criterion_limit (ресурс L10h, статическая
    # грузоподъёмность, запас устойчивости и т.п.). Другое значение — ошибка
    # вызывающего кода, а не тихая нормировка задания.
    criterion_direction: str = CRITERION_AT_MOST

    # --- метод и его версия ---
    method: str = "не_указан"             # см. VerificationMethod в strength_coverage.py
    methodology_version: str = "не указана"

    # --- к каким данным и ревизии это относится ---
    input_fingerprint: str = ""           # см. Project.compute_input_fingerprint()
    product_revision: str = ""            # Project.revision на момент расчёта

    # --- кто и когда ---
    computed_by: str = ""
    computed_by_role: Optional[Role] = None
    computed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    reviewed_by: Optional[str] = None
    reviewed_by_role: Optional[Role] = None
    reviewed_at: Optional[str] = None

    notes: Optional[str] = None

    def passed(self) -> bool:
        """
        Результат существует и удовлетворяет критерию. Отсутствие числа или
        критерия — это НЕ пройденная проверка, а невыполненная. Направление
        сравнения — по `criterion_direction` (см. константы выше), а не
        всегда "не более": ресурс/грузоподъёмность/запас устойчивости
        честно проверяются как "не менее", без инверсии смысла числа.

        Codex-замечание (продолжение, 18.09.2026, п.1): если `criterion_
        direction` не является ни "не_более", ни "не_менее" (опечатка,
        повреждённые данные, забытое присвоение), метод НЕ должен молча
        считать это "не более" — иначе проверка типа "ресурс не менее X"
        могла бы тихо объявляться пройденной/непройденной по неверному
        смыслу.

        Независимая проверка (продолжение, 18.09.2026, п.2 «P1»): первая
        версия этого исправления заменяла тихую нормировку на `raise
        ValueError`. Это оказалось НЕ тем контрактом, который требовался:
        `passed()` — простой булев предикат, вызываемый (в т.ч. косвенно,
        через будущий код) в местах, ожидающих bool, а не исключение;
        превращение геттера состояния в операцию, которая может упасть,
        неверно смещает ответственность. Правильное разделение:
        - `passed()` возвращает False для НЕИЗВЕСТНОГО direction — запись
          с испорченным/отсутствующим направлением критерия НЕ СЧИТАЕТСЯ
          пройденной проверкой (это по-прежнему НЕ тихая нормировка к
          "не более": False возвращается для ЛЮБОГО соотношения result/
          limit, включая случаи, где "не более"-умолчание дало бы True);
        - `is_complete_and_valid()` — место, где ошибка ОБЪЯСНЯЕТСЯ явно
          (см. ниже: отдельная запись в `problems`, не молчаливое False).
        """
        if not _finite_number(self.result_value) or not _finite_number(self.criterion_limit):
            return False
        if self.criterion_direction == CRITERION_AT_LEAST:
            return self.result_value >= self.criterion_limit
        if self.criterion_direction == CRITERION_AT_MOST:
            return self.result_value <= self.criterion_limit
        return False

    def reviewed_by_someone_else(self) -> bool:
        """Раздел 1.А: 'техническую проверку другим специалистом'."""
        if not self.reviewed_by or not self.computed_by:
            return False
        return self.reviewed_by.strip().lower() != self.computed_by.strip().lower()

    def is_current_for(self, project_revision: str, input_fingerprint: str) -> bool:
        """Проверка ещё действительна для текущей ревизии и текущих входных данных."""
        return (
            self.product_revision == project_revision
            and self.input_fingerprint == input_fingerprint
            and self.input_fingerprint != ""
        )

    def is_complete_and_valid(self, project_revision: str, input_fingerprint: str) -> tuple[bool, list[str]]:
        """Единая проверка "закрыт ли пункт на самом деле". Возвращает (ок, причины)."""
        problems: list[str] = []
        if not _finite_number(self.result_value):
            problems.append("нет числового результата расчёта (нужно конечное число)")
        if not _finite_number(self.criterion_limit):
            problems.append("не задан критерий (допустимое значение должно быть конечным числом)")
        if not self.criterion_source or self.criterion_source in ("уточнить", "—", ""):
            problems.append("не указан источник критерия")
        if self.methodology_version in ("", "не указана"):
            problems.append("не указана версия методики расчёта")
        if not self.computed_by:
            problems.append("не указан исполнитель расчёта")
        if not self.reviewed_by_someone_else():
            problems.append("расчёт не проверен другим специалистом (раздел 1.А)")
        if not self.is_current_for(project_revision, input_fingerprint):
            problems.append("расчёт относится к другой ревизии/входным данным — устарел (раздел 1.Б)")
        if self.criterion_direction not in VALID_CRITERION_DIRECTIONS:
            problems.append(
                f"не указано или некорректно направление критерия ({self.criterion_direction!r}); "
                f"ожидается одно из {VALID_CRITERION_DIRECTIONS}"
            )
        if (
            self.result_value is not None and self.criterion_limit is not None
            and self.criterion_direction in VALID_CRITERION_DIRECTIONS and not self.passed()
        ):
            comparator = "не удовлетворяет критерию (не более)" if self.criterion_direction == CRITERION_AT_MOST \
                else "не удовлетворяет критерию (не менее)"
            problems.append(
                f"результат ({self.result_value} {self.result_unit}) {comparator} "
                f"({self.criterion_limit} {self.result_unit})"
            )
        return (len(problems) == 0, problems)

    def to_dict(self) -> dict:
        return {
            "criterion_description": self.criterion_description,
            "result_value": self.result_value,
            "result_unit": self.result_unit,
            "criterion_limit": self.criterion_limit,
            "criterion_source": self.criterion_source,
            "criterion_direction": self.criterion_direction,
            "safety_factor": self.safety_factor,
            "method": self.method,
            "methodology_version": self.methodology_version,
            "input_fingerprint": self.input_fingerprint,
            "product_revision": self.product_revision,
            "computed_by": self.computed_by,
            "computed_by_role": self.computed_by_role.value if self.computed_by_role else None,
            "computed_at": self.computed_at,
            "reviewed_by": self.reviewed_by,
            "reviewed_by_role": self.reviewed_by_role.value if self.reviewed_by_role else None,
            "reviewed_at": self.reviewed_at,
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(d: dict) -> "VerificationRecord":
        return VerificationRecord(
            criterion_description=d.get("criterion_description", ""),
            result_value=d.get("result_value"),
            result_unit=d.get("result_unit", ""),
            criterion_limit=d.get("criterion_limit"),
            criterion_source=d.get("criterion_source", "—"),
            criterion_direction=d.get("criterion_direction", CRITERION_AT_MOST),
            safety_factor=d.get("safety_factor"),
            method=d.get("method", "не_указан"),
            methodology_version=d.get("methodology_version", "не указана"),
            input_fingerprint=d.get("input_fingerprint", ""),
            product_revision=d.get("product_revision", ""),
            computed_by=d.get("computed_by", ""),
            computed_by_role=Role(d["computed_by_role"]) if d.get("computed_by_role") else None,
            computed_at=d.get("computed_at", datetime.now(timezone.utc).isoformat()),
            reviewed_by=d.get("reviewed_by"),
            reviewed_by_role=Role(d["reviewed_by_role"]) if d.get("reviewed_by_role") else None,
            reviewed_at=d.get("reviewed_at"),
            notes=d.get("notes"),
        )
