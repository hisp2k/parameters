# -*- coding: utf-8 -*-
"""
Контрактные тесты обратного считывания компоновки желоба (раздел 4 доп.
задания). Как и test_cad_adapter.py — весь транспорт подменён
`FakeBridgeTransport`, реального обращения к SolidWorks здесь нет. Формат
ответа `sw_components`, который здесь имитируется, — РЕАЛЬНО ПРОВЕРЕННЫЙ
на сборке 25.SHT.G.00.00.00.00 17.09.2026 (см. docstring
cad_adapter/section_layout.py), а не придуманный для удобства теста.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from calculator.cad_adapter.bridge_transport import BridgeResponse, FakeBridgeTransport
from calculator.cad_adapter.section_layout import (
    DEFAULT_SECTION_NAME_PREFIX,
    DEFAULT_SPACER_NAME_PREFIX,
    read_trough_section_layout,
)


def _ok(tool: str, result: dict | None = None) -> BridgeResponse:
    return BridgeResponse(ok=True, tool=tool, result=result, raw={"ok": True, "tool": tool, "result": result})


def _fail(tool: str, message: str = "ошибка") -> BridgeResponse:
    return BridgeResponse(
        ok=False, tool=tool, result=None,
        raw={"ok": False, "tool": tool},
        error={"code": "FAIL", "message": message},
    )


def _components_page(items: list[dict], *, next_offset=None, truncated=False,
                      connector_write_allowed: bool = False, total=None, offset=0) -> BridgeResponse:
    """Строит ответ sw_components в РЕАЛЬНО ПРОВЕРЕННОЙ форме (двойная вложенность data)."""
    return _ok("sw_components", {
        "ok": True,
        "data": {
            "context": {"connector_write_allowed": connector_write_allowed},
            "data": {
                "scope": "TOP_LEVEL_INSTANCES",
                "items": items,
                "total": len(items) if total is None else total,
                "offset": offset,
                "next_offset": next_offset,
                "truncated": truncated,
            },
            "issues": [],
        },
    })


def _item(name: str) -> dict:
    return {"name": name}


def _four_sections_three_spacers_page() -> BridgeResponse:
    items = (
        [_item(f"{DEFAULT_SECTION_NAME_PREFIX} Отсек-{i}") for i in range(1, 5)]
        + [_item(f"{DEFAULT_SPACER_NAME_PREFIX} Резиновая проставка отсеков-{i}") for i in (1, 2, 3)]
        + [_item("25.SHT.G.02.00.00.00 СБ Шнек с осями-1")]  # не должен попасть ни в один счётчик
    )
    return _components_page(items, connector_write_allowed=False)


# ---------------------------------------------------------------------------
# базовые ошибки моста
# ---------------------------------------------------------------------------

def test_returns_not_ok_when_bridge_unavailable():
    transport = FakeBridgeTransport(responses={})  # sw_status не настроен -> UNEXPECTED_TOOL
    result = read_trough_section_layout(
        transport, nominal_section_length_mm=3000.0, target_section_count=4,
    )
    assert result.ok is False
    assert result.errors
    assert result.measured_section_count is None


def test_returns_not_ok_when_sw_status_fails():
    transport = FakeBridgeTransport(responses={"sw_status": _fail("sw_status", "SolidWorks не запущен")})
    result = read_trough_section_layout(
        transport, nominal_section_length_mm=3000.0, target_section_count=4,
    )
    assert result.ok is False
    assert any("sw_status" in e for e in result.errors)


def test_returns_not_ok_when_sw_components_fails():
    transport = FakeBridgeTransport(responses={
        "sw_status": _ok("sw_status"),
        "sw_components": _fail("sw_components", "не удалось перечислить компоненты"),
    })
    result = read_trough_section_layout(
        transport, nominal_section_length_mm=3000.0, target_section_count=4,
    )
    assert result.ok is False
    assert any("sw_components" in e for e in result.errors)


# ---------------------------------------------------------------------------
# успешный путь — счёт секций/проставок и целевые значения
# ---------------------------------------------------------------------------

def test_counts_sections_and_spacers_from_real_response_shape():
    transport = FakeBridgeTransport(responses={
        "sw_status": _ok("sw_status"),
        "sw_components": _four_sections_three_spacers_page(),
    })
    result = read_trough_section_layout(
        transport, nominal_section_length_mm=3000.0, target_section_count=4,
    )
    assert result.ok is True
    assert result.errors == []
    assert result.measured_section_count == 4
    assert result.measured_spacer_count == 3
    assert result.count_matches_target is True
    assert result.target_nominal_length_mm == 12000.0
    assert result.connector_write_allowed is False
    assert result.write_supported is False


def test_flags_mismatch_when_measured_count_differs_from_target():
    transport = FakeBridgeTransport(responses={
        "sw_status": _ok("sw_status"),
        "sw_components": _four_sections_three_spacers_page(),  # фактически 4 секции
    })
    result = read_trough_section_layout(
        transport, nominal_section_length_mm=3000.0, target_section_count=5,  # цель — 5
    )
    assert result.ok is True
    assert result.measured_section_count == 4
    assert result.count_matches_target is False


def test_paginates_across_multiple_pages():
    page1 = _components_page(
        [_item(f"{DEFAULT_SECTION_NAME_PREFIX} Отсек-{i}") for i in range(1, 3)],
        next_offset=2, truncated=True, total=7,
    )
    page2 = _components_page(
        [_item(f"{DEFAULT_SECTION_NAME_PREFIX} Отсек-{i}") for i in range(3, 5)]
        + [_item(f"{DEFAULT_SPACER_NAME_PREFIX} Резиновая проставка отсеков-{i}") for i in (1, 2, 3)],
        next_offset=None, truncated=False, total=7, offset=2,
    )
    calls = {"n": 0}

    def handler(args):
        calls["n"] += 1
        return page1 if args["offset"] == 0 else page2

    transport = FakeBridgeTransport(responses={"sw_status": _ok("sw_status"), "sw_components": handler})
    result = read_trough_section_layout(
        transport, nominal_section_length_mm=3000.0, target_section_count=4,
    )
    assert result.ok is True
    assert result.measured_section_count == 4
    assert result.measured_spacer_count == 3
    assert calls["n"] == 2


def test_stops_after_max_pages_and_reports_incomplete_not_fabricated():
    def handler(args):
        offset = args["offset"]
        return _components_page([_item(f"прочий-{offset}")], total=100, offset=offset,
                                next_offset=offset + 1, truncated=True)

    transport = FakeBridgeTransport(responses={"sw_status": _ok("sw_status"), "sw_components": handler})
    result = read_trough_section_layout(
        transport, nominal_section_length_mm=3000.0, target_section_count=4, max_pages=3,
    )
    assert result.ok is False
    assert any("Остановлено после" in e for e in result.errors)
    assert result.measured_section_count is None  # незавершённый подсчёт не публикуется как факт


# ---------------------------------------------------------------------------
# толщина проставки и оценка общей длины (раздел 4 — "измерь результат")
# ---------------------------------------------------------------------------

def test_no_overall_length_estimate_without_measured_spacer_thickness():
    transport = FakeBridgeTransport(responses={
        "sw_status": _ok("sw_status"),
        "sw_components": _four_sections_three_spacers_page(),
    })
    result = read_trough_section_layout(
        transport, nominal_section_length_mm=3000.0, target_section_count=4,
    )
    assert result.measured_joint_spacer_thickness_mm is None
    assert result.measured_overall_length_estimate_mm is None  # не выдумываем без обмера


def test_overall_length_estimate_uses_measured_spacer_thickness_not_nominal():
    transport = FakeBridgeTransport(responses={
        "sw_status": _ok("sw_status"),
        "sw_components": _four_sections_three_spacers_page(),  # 4 секции -> 3 стыка
    })
    result = read_trough_section_layout(
        transport, nominal_section_length_mm=3000.0, target_section_count=4,
        measured_joint_spacer_thickness_mm=2.0,  # фактически измеренная, не номинальная толщина
    )
    assert result.measured_overall_length_estimate_mm == 4 * 3000.0 + 3 * 2.0
    assert result.overall_length_is_estimate is True


# ---------------------------------------------------------------------------
# запись не поддерживается — явно, а не молчаливым отказом
# ---------------------------------------------------------------------------

def test_write_is_explicitly_unsupported_with_reason():
    transport = FakeBridgeTransport(responses={
        "sw_status": _ok("sw_status"),
        "sw_components": _four_sections_three_spacers_page(),
    })
    result = read_trough_section_layout(
        transport, nominal_section_length_mm=3000.0, target_section_count=4,
    )
    assert result.write_supported is False
    assert result.write_unsupported_reason  # непустая явная причина, а не пустая строка


# ---------------------------------------------------------------------------
# входные значения
# ---------------------------------------------------------------------------

def test_rejects_non_positive_nominal_length():
    transport = FakeBridgeTransport(responses={"sw_status": _ok("sw_status")})
    try:
        read_trough_section_layout(transport, nominal_section_length_mm=0.0, target_section_count=4)
        assert False, "должно было вызвать ValueError"
    except ValueError:
        pass


def test_rejects_non_positive_target_section_count():
    transport = FakeBridgeTransport(responses={"sw_status": _ok("sw_status")})
    try:
        read_trough_section_layout(transport, nominal_section_length_mm=3000.0, target_section_count=0)
        assert False, "должно было вызвать ValueError"
    except ValueError:
        pass
