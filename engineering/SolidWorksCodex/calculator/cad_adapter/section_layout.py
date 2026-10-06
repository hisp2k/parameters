# -*- coding: utf-8 -*-
"""
Обратное считывание фактической компоновки желоба ("Отсек" + межсекционная
"Резиновая проставка отсеков") из SolidWorks в калькулятор (раздел 4
дополнительного задания: "изменение модели из калькулятора с обратным
получением фактических размеров"; раздел 19 — "откуда это число").

ЧЕСТНАЯ ГРАНИЦА (см. cad_adapter/interface.py, разделы 5/12 задания):

1. Запись в сборку этим модулем НЕ реализована. На реальной сборке
   25.SHT.G.00.00.00.00 (независимая копия заказа №2377, 17.09.2026)
   `sw_status`/`sw_components` вернули `connector_write_allowed: false` —
   коннектор в этой редакции не пишет в сборки. Количество секций меняется
   ТОЛЬКО вручную в SolidWorks штатным «Линейный массив компонентов»
   (см. отчёт по сборке); этот модуль только читает результат такого
   изменения обратно в калькулятор.

2. Формат ответа `sw_components`, разбираемый ниже, — РЕАЛЬНО ПРОВЕРЕННЫЙ
   на той же сборке в этой же сессии (не "правдоподобный, но неподтверждённый",
   как разбор в interface.py::rebuild_project_copy() для sw_features/
   sw_properties): `resp.result == {"ok": bool, "data": {"context": {...,
   "connector_write_allowed": bool, ...}, "data": {"scope":
   "TOP_LEVEL_INSTANCES", "items": [{"name": str, ...}, ...], "total": int,
   "offset": int, "next_offset": int|None, "truncated": bool, ...},
   "issues": [...], ...}}`. Двойная вложенность "data" сохранена такой,
   какая она есть в реальном ответе, а не сглажена и не угадана.
   `limit` у `sw_components` не может быть произвольно большим — вызов с
   `limit=500` вернул `INVALID_ARGUMENTS`; отсюда постраничный обход с
   `page_limit<=50` и `next_offset`/`truncated`.

3. Толщина проставки в стыке (`measured_joint_spacer_thickness_mm`) НЕ
   считывается автоматически: единственный проверенный в этой сессии вызов
   `sw_part` не принимал фильтрующих аргументов (только `{}` на активном
   документе), а раздел 5 прямо запрещает "выдумывать методы, свойства или
   результаты вызовов" — придумывать сигнатуру вида `sw_part(path=...)`
   для выбора конкретной детали недопустимо. Поэтому значение передаётся
   вызывающей стороной как результат отдельного, вручную выполненного и
   задокументированного измерения в SolidWorks, а не считывается здесь.
   Если оно не передано — `measured_overall_length_estimate_mm` не
   вычисляется вовсе (не приблизительно, а никак), чтобы не подменить
   отсутствующий обмер тихим допущением.

4. Итоговая длина (`measured_overall_length_estimate_mm`), когда толщина
   проставки известна, — это ОЦЕНКА (номинал секции × количество + толщина
   проставки × число стыков), а не прямой обмер габарита сборки: прямого
   подтверждённого вызова для обмера общего габарита в этой сессии не было
   (см. `overall_length_is_estimate=True`, которое всегда стоит рядом).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Optional

from calculator.cad_adapter.bridge_transport import BridgeTransport, BridgeError


# Префиксы имён компонентов, подтверждённые на сборке 25.SHT.G.00.00.00.00
# (независимая копия заказа №2377) 17.09.2026 через sw_components.
DEFAULT_SECTION_NAME_PREFIX = "25.SHT.G.01.00.00.00"  # "Отсек"
DEFAULT_SPACER_NAME_PREFIX = "25.SHT.G.00.00.00.09"   # "Резиновая проставка отсеков"

DEFAULT_PAGE_LIMIT = 50   # limit=500 отклонён коннектором как INVALID_ARGUMENTS — см. docstring модуля
DEFAULT_MAX_PAGES = 20    # защита от зацикливания, если truncated никогда не снимется


@dataclass
class TroughSectionLayout:
    """
    Честный снимок фактической компоновки желоба на момент опроса моста,
    рядом с целевыми/номинальными значениями — раздел 19: "покажи, откуда
    число и можно ли ему верить", а не подменяй номинал фактом или наоборот.
    """

    ok: bool
    nominal_section_length_mm: float
    target_section_count: int
    target_nominal_length_mm: float

    measured_section_count: Optional[int] = None
    measured_spacer_count: Optional[int] = None
    measured_joint_spacer_thickness_mm: Optional[float] = None
    measured_overall_length_estimate_mm: Optional[float] = None
    overall_length_is_estimate: bool = True

    count_matches_target: Optional[bool] = None
    connector_write_allowed: Optional[bool] = None
    write_supported: bool = False
    write_unsupported_reason: str = (
        "Коннектор не пишет в сборки в этой редакции (connector_write_allowed=false, "
        "подтверждено 17.09.2026 на 25.SHT.G.00.00.00.00). Количество секций меняется "
        "вручную в SolidWorks штатным «Линейный массив компонентов», не через этот адаптер."
    )

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    section_instances: list[str] = field(default_factory=list)
    spacer_instances: list[str] = field(default_factory=list)
    source_context: dict = field(default_factory=dict)
    raw_steps: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "nominal_section_length_mm": self.nominal_section_length_mm,
            "target_section_count": self.target_section_count,
            "target_nominal_length_mm": self.target_nominal_length_mm,
            "measured_section_count": self.measured_section_count,
            "measured_spacer_count": self.measured_spacer_count,
            "measured_joint_spacer_thickness_mm": self.measured_joint_spacer_thickness_mm,
            "measured_overall_length_estimate_mm": self.measured_overall_length_estimate_mm,
            "overall_length_is_estimate": self.overall_length_is_estimate,
            "count_matches_target": self.count_matches_target,
            "connector_write_allowed": self.connector_write_allowed,
            "write_supported": self.write_supported,
            "write_unsupported_reason": self.write_unsupported_reason,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "section_instances": list(self.section_instances),
            "spacer_instances": list(self.spacer_instances),
            "source_context": dict(self.source_context),
        }


def validate_layout_inputs(nominal_section_length_mm, target_section_count,
                           measured_joint_spacer_thickness_mm=None,
                           page_limit=DEFAULT_PAGE_LIMIT, max_pages=DEFAULT_MAX_PAGES) -> None:
    for name, value in (("nominal_section_length_mm", nominal_section_length_mm),
                        ("measured_joint_spacer_thickness_mm", measured_joint_spacer_thickness_mm)):
        if value is None and name == "measured_joint_spacer_thickness_mm":
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name}: требуется конечное положительное число.")
    for name, value in (("target_section_count", target_section_count),
                        ("page_limit", page_limit), ("max_pages", max_pages)):
        if type(value) is not int or value <= 0:
            raise ValueError(f"{name}: требуется положительное целое число.")
    if page_limit > DEFAULT_PAGE_LIMIT:
        raise ValueError(f"page_limit не должен превышать {DEFAULT_PAGE_LIMIT}.")
    try:
        length_is_finite = math.isfinite(nominal_section_length_mm * target_section_count)
    except OverflowError:
        length_is_finite = False
    if not length_is_finite:
        raise ValueError("Номинальная длина выходит за числовой диапазон.")


def read_trough_section_layout(
    transport: BridgeTransport,
    *,
    nominal_section_length_mm: float,
    target_section_count: int,
    section_name_prefix: str = DEFAULT_SECTION_NAME_PREFIX,
    spacer_name_prefix: str = DEFAULT_SPACER_NAME_PREFIX,
    measured_joint_spacer_thickness_mm: Optional[float] = None,
    page_limit: int = DEFAULT_PAGE_LIMIT,
    max_pages: int = DEFAULT_MAX_PAGES,
) -> TroughSectionLayout:
    """
    Опрашивает мост (`sw_status`, затем постранично `sw_components`) и
    строит честный снимок компоновки. Только чтение — ничего не пишет в
    SolidWorks (запись для этой сборки не реализована, см. docstring
    модуля и `write_supported`/`write_unsupported_reason`).

    Идемпотентно: повторный вызов с теми же аргументами не меняет модель и
    просто возвращает свежий снимок (раздел 4 доп. задания — "идемпотентно").
    """
    validate_layout_inputs(nominal_section_length_mm, target_section_count,
                           measured_joint_spacer_thickness_mm, page_limit, max_pages)
    if not section_name_prefix or not spacer_name_prefix or section_name_prefix == spacer_name_prefix:
        raise ValueError("Нужны разные непустые префиксы секций и проставок.")

    target_nominal_length_mm = nominal_section_length_mm * target_section_count
    result = TroughSectionLayout(
        ok=False,
        nominal_section_length_mm=nominal_section_length_mm,
        target_section_count=target_section_count,
        target_nominal_length_mm=target_nominal_length_mm,
        measured_joint_spacer_thickness_mm=measured_joint_spacer_thickness_mm,
    )

    try:
        status_resp = transport.call("sw_status", {}, timeout_s=15.0)
    except BridgeError as e:
        result.errors.append(f"Мост недоступен: {e}")
        return result
    result.raw_steps["sw_status"] = status_resp.raw
    if not status_resp.ok or (isinstance(status_resp.result, dict) and status_resp.result.get("ok") is False):
        result.errors.append(f"sw_status вернул ошибку: {status_resp.error}")
        return result

    section_count = 0
    spacer_count = 0
    offset = 0
    connector_write_allowed: Optional[bool] = None
    pages_read = 0
    expected_total = None
    expected_context = None
    seen_names: set[str] = set()
    sections: list[str] = []
    spacers: list[str] = []

    while True:
        if pages_read >= max_pages:
            result.errors.append(
                f"Остановлено после {max_pages} страниц sw_components (offset={offset}) — "
                "похоже на незавершающуюся пагинацию (truncated не снимается); подсчёт неполный "
                "и намеренно НЕ публикуется как факт."
            )
            break
        try:
            resp = transport.call("sw_components", {"limit": page_limit, "offset": offset}, timeout_s=30.0)
        except BridgeError as e:
            result.errors.append(f"sw_components не удался (offset={offset}): {e}")
            break
        result.raw_steps[f"sw_components@{offset}"] = resp.raw
        pages_read += 1
        if not resp.ok:
            result.errors.append(f"sw_components вернул ошибку (offset={offset}): {resp.error}")
            break

        outer = resp.result if isinstance(resp.result, dict) else {}
        page_data = outer.get("data") if isinstance(outer.get("data"), dict) else {}
        inner = page_data.get("data") if isinstance(page_data.get("data"), dict) else {}
        context = page_data.get("context")
        items = inner.get("items")
        total = inner.get("total")
        truncated = inner.get("truncated")
        next_offset = inner.get("next_offset")
        if (outer.get("ok") is not True or not isinstance(context, dict)
                or inner.get("scope") != "TOP_LEVEL_INSTANCES"
                or not isinstance(items, list) or type(total) is not int or total < 0
                or type(inner.get("offset")) is not int or inner["offset"] != offset
                or type(truncated) is not bool or len(items) > page_limit):
            result.errors.append(f"Некорректный/неполный ответ sw_components (offset={offset}).")
            break
        if page_data.get("issues"):
            result.errors.append(f"sw_components сообщил замечания: {page_data['issues']}")
            break
        if expected_total is None:
            expected_total, expected_context = total, dict(context)
            connector_write_allowed = context.get("connector_write_allowed")
        elif total != expected_total or context != expected_context:
            result.errors.append("Состав или контекст сборки изменился между страницами; повторите чтение.")
            break
        end_offset = offset + len(items)
        if (end_offset > total or (truncated and (
                not items or type(next_offset) is not int or next_offset != end_offset or next_offset >= total))
                or (not truncated and (end_offset != total or next_offset is not None))):
            result.errors.append(f"Неполная/противоречивая пагинация sw_components (offset={offset}).")
            break
        for item in items:
            name = item.get("name") if isinstance(item, dict) else None
            if not isinstance(name, str) or not name.strip() or name in seen_names:
                result.errors.append("Неверное или повторное имя экземпляра sw_components.")
                break
            seen_names.add(name)
            if name.startswith(section_name_prefix + " ") or name.startswith(section_name_prefix + "-"):
                section_count += 1
                sections.append(name)
            elif name.startswith(spacer_name_prefix + " ") or name.startswith(spacer_name_prefix + "-"):
                spacer_count += 1
                spacers.append(name)
        if result.errors or not truncated:
            break
        offset = next_offset

    result.connector_write_allowed = connector_write_allowed
    result.write_supported = False  # запись сборки этим модулем не реализована — см. docstring

    if result.errors:
        return result

    if section_count == 0:
        result.errors.append("Секции указанного изделия не найдены; проверьте открытую сборку и префиксы.")
        return result

    result.measured_section_count = section_count
    result.measured_spacer_count = spacer_count
    result.section_instances = sections
    result.spacer_instances = spacers
    result.source_context = expected_context or {}
    result.count_matches_target = (section_count == target_section_count)
    if not result.count_matches_target:
        result.warnings.append(f"Количество секций {section_count} не соответствует цели {target_section_count}.")
    joint_count = max(section_count - 1, 0)
    if spacer_count != joint_count:
        result.warnings.append(
            f"Проставок верхнего уровня найдено {spacer_count}; стыков {joint_count}. "
            "Вложенные проставки и посадку нужно подтвердить отдельно; недостающие экземпляры не добавлены к счётчику."
        )
    result.warnings.append("Подсчёт экземпляров не подтверждает посадку, отсутствие коллизий, компоновку шнека, привод и BOM.")

    if measured_joint_spacer_thickness_mm is not None and spacer_count == joint_count:
        result.measured_overall_length_estimate_mm = (
            nominal_section_length_mm * section_count
            + measured_joint_spacer_thickness_mm * joint_count
        )
        if not math.isfinite(result.measured_overall_length_estimate_mm):
            result.measured_overall_length_estimate_mm = None
            result.errors.append("Оценка длины выходит за числовой диапазон.")
            return result
        result.overall_length_is_estimate = True

    result.ok = True
    return result
