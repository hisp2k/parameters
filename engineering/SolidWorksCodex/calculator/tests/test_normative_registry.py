# -*- coding: utf-8 -*-
"""
Тесты реестра нормативов (раздел 8 задания): контракт "проверено ≠
подтверждено обозначение из головы модели" — каждая запись со статусом,
начинающимся на "Проверено", обязана иметь непустой источник (реальную
ссылку независимой проверки), а fully_resolved=True разрешается только там,
где применимость подтверждена полностью, а не частично.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from calculator.reference.normative_registry import (
    DEFAULT_REGISTRY, unresolved_entries, CANCELLED_RATE_WARNING,
)


def test_every_checked_entry_has_a_real_source_not_a_bare_dash():
    for doc in DEFAULT_REGISTRY:
        if doc.status.startswith("Проверено"):
            assert doc.source != "—", f"{doc.title}: статус 'Проверено...', но источник не указан."
            assert doc.checked_date, f"{doc.title}: статус 'Проверено...', но дата проверки не указана."


def test_fully_resolved_implies_checked_status():
    for doc in DEFAULT_REGISTRY:
        if doc.fully_resolved:
            assert doc.status.startswith("Проверено"), (
                f"{doc.title}: fully_resolved=True, но статус не 'Проверено...' ({doc.status!r})."
            )


def test_unresolved_entries_excludes_only_fully_resolved():
    unresolved = unresolved_entries()
    unresolved_titles = {d.title for d in unresolved}
    for doc in DEFAULT_REGISTRY:
        if doc.fully_resolved:
            assert doc.title not in unresolved_titles
        else:
            assert doc.title in unresolved_titles


def test_partially_checked_entries_are_not_marked_fully_resolved():
    """
    ЕСКД/ЕСТД записи прошли независимую проверку обозначения, но применимость
    к практике Тех-Аэро не подтверждена — они обязаны оставаться
    unresolved, а не тихо считаться закрытыми только потому, что что-то
    было найдено в вебе.
    """
    partial = [d for d in DEFAULT_REGISTRY if "частично" in d.status]
    assert partial, "ожидались записи с частичной проверкой (ЕСКД/ЕСТД)"
    for d in partial:
        assert d.fully_resolved is False


def test_rejected_screw_conveyor_gost_is_not_silently_adopted():
    """Раздел 8: 'не считай известный номер ГОСТ доказательством актуальности'."""
    entry = next(d for d in DEFAULT_REGISTRY if "screw_engineering.compute_engineering_core" in d.related_checks)
    assert "23976-80" in entry.note
    assert "отменён" in entry.note or "истёк" in entry.note
    assert entry.designation.startswith("уточнить"), (
        "обозначение отклонённого ГОСТ не должно стать 'официальным' обозначением методики"
    )


def test_default_registry_still_has_unresolved_placeholder_categories():
    """Материалы/сварные-болтовые/приводные комплектующие остаются 'уточнить' — не выдуманы."""
    placeholders = [d for d in DEFAULT_REGISTRY if d.designation == "уточнить"]
    assert len(placeholders) >= 3


def test_cancelled_rate_warning_is_a_non_empty_documented_string():
    assert "970" in CANCELLED_RATE_WARNING
    assert "руб" in CANCELLED_RATE_WARNING
