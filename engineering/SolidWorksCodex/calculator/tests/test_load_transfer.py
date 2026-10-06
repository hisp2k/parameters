# -*- coding: utf-8 -*-
"""
Проверка обобщённого объекта передачи нагрузки (core/load_transfer.py,
раздел 2 доп. задания). Синтетические данные — не TUBE-SAND-001.
"""

import dataclasses
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from calculator.core.load_transfer import (
    LoadTransferError, LoadCase, Point3D, LoadVector, LoadCaseSet, ResultantLoad,
)


def test_point3d_rejects_non_finite():
    with pytest.raises(LoadTransferError):
        Point3D(float("nan"), 0.0, 0.0)
    with pytest.raises(LoadTransferError):
        Point3D(0.0, 0.0, True)


def _load(**overrides):
    defaults = dict(
        node_ref="опора_A", point=Point3D(0.0, 0.0, 0.0),
        fx_n=0.0, fy_n=0.0, fz_n=0.0, mx_nmm=0.0, my_nmm=0.0, mz_nmm=0.0,
        load_case=LoadCase.OPERATING, source="synthetic-test",
    )
    defaults.update(overrides)
    return LoadVector(**defaults)


def test_pure_force_transferred_gives_moment_equal_to_r_cross_f_not_negative():
    """
    Классический тест на знак: сила 100 Н вдоль +Y, приложенная в точке
    (1000, 0, 0) мм, перенесённая в начало координат, должна дать момент
    M = r×F, r=(1000,0,0)−(0,0,0)=(1000,0,0), F=(0,100,0):
    r×F = (0*0-0*100, 0*0-1000*0, 1000*100-0*0) = (0, 0, 100000) Н·мм.
    """
    load = _load(point=Point3D(1000.0, 0.0, 0.0), fy_n=100.0)
    transferred = load.transferred_to(Point3D(0.0, 0.0, 0.0))
    assert transferred.fx_n == pytest.approx(0.0)
    assert transferred.fy_n == pytest.approx(100.0)
    assert transferred.fz_n == pytest.approx(0.0)
    assert transferred.mx_nmm == pytest.approx(0.0)
    assert transferred.my_nmm == pytest.approx(0.0)
    assert transferred.mz_nmm == pytest.approx(100000.0)  # НЕ -100000.0


def test_transfer_is_reversible():
    load = _load(point=Point3D(500.0, 200.0, -50.0), fx_n=30.0, fy_n=-70.0, fz_n=10.0,
                 mx_nmm=1000.0, my_nmm=-500.0, mz_nmm=200.0)
    moved = load.transferred_to(Point3D(-100.0, 300.0, 25.0))
    back = moved.transferred_to(load.point)
    assert back.fx_n == pytest.approx(load.fx_n)
    assert back.fy_n == pytest.approx(load.fy_n)
    assert back.fz_n == pytest.approx(load.fz_n)
    assert back.mx_nmm == pytest.approx(load.mx_nmm)
    assert back.my_nmm == pytest.approx(load.my_nmm)
    assert back.mz_nmm == pytest.approx(load.mz_nmm)


def test_transfer_to_same_point_is_identity():
    load = _load(point=Point3D(10.0, 20.0, 30.0), fx_n=5.0, mz_nmm=40.0)
    same = load.transferred_to(Point3D(10.0, 20.0, 30.0))
    assert same.fx_n == pytest.approx(load.fx_n)
    assert same.mz_nmm == pytest.approx(load.mz_nmm)


def test_load_vector_requires_source_and_node_ref():
    with pytest.raises(LoadTransferError):
        _load(source="")
    with pytest.raises(LoadTransferError):
        _load(node_ref="")


def test_load_vector_rejects_non_loadcase():
    with pytest.raises(LoadTransferError):
        _load(load_case="рабочий_режим")  # строка, не LoadCase


# --- LoadCaseSet: разделение случаев, запрет двойного счёта -----------------

def test_load_case_set_rejects_duplicate_addition():
    s = LoadCaseSet()
    s.add(_load(label="реакция_A"))
    with pytest.raises(LoadTransferError):
        s.add(_load(label="реакция_A"))  # тот же node_ref/case/source/label — похоже на двойной счёт


def test_load_case_set_allows_same_source_with_different_label():
    s = LoadCaseSet()
    s.add(_load(label="реакция_A"))
    s.add(_load(label="реакция_B"))  # другая метка — не дубль
    assert len(s.loads) == 2


def test_resultant_requires_explicit_cases_not_default_all():
    s = LoadCaseSet()
    s.add(_load(load_case=LoadCase.SELF_WEIGHT, fz_n=-100.0))
    s.add(_load(load_case=LoadCase.OPERATING, fz_n=-50.0, label="раб"))
    with pytest.raises(LoadTransferError):
        s.resultant_at(Point3D(0, 0, 0), cases=[])


def test_resultant_sums_only_selected_cases_not_all():
    s = LoadCaseSet()
    s.add(_load(load_case=LoadCase.SELF_WEIGHT, fz_n=-100.0, label="вес"))
    s.add(_load(load_case=LoadCase.OPERATING, fz_n=-50.0, label="раб"))
    s.add(_load(load_case=LoadCase.STARTUP, fz_n=-999.0, label="пуск"))
    only_weight = s.resultant_at(Point3D(0, 0, 0), cases=[LoadCase.SELF_WEIGHT])
    assert only_weight.fz_n == pytest.approx(-100.0)
    assert only_weight.contributing_count == 1
    weight_plus_operating = s.resultant_at(Point3D(0, 0, 0), cases=[LoadCase.SELF_WEIGHT, LoadCase.OPERATING])
    assert weight_plus_operating.fz_n == pytest.approx(-150.0)
    assert weight_plus_operating.contributing_count == 2


def test_resultant_transfers_each_load_before_summing_moments():
    s = LoadCaseSet()
    # Две силы по +Y=100Н, в точках x=1000 и x=2000, момент относительно x=0
    # должен быть суммой ОТДЕЛЬНЫХ переносов (100000 + 200000), а не одного
    # переноса из усреднённой/произвольной точки.
    s.add(_load(load_case=LoadCase.OPERATING, point=Point3D(1000.0, 0, 0), fy_n=100.0, label="p1"))
    s.add(_load(load_case=LoadCase.OPERATING, point=Point3D(2000.0, 0, 0), fy_n=100.0, label="p2"))
    result = s.resultant_at(Point3D(0.0, 0.0, 0.0), cases=[LoadCase.OPERATING])
    assert result.fy_n == pytest.approx(200.0)
    assert result.mz_nmm == pytest.approx(100000.0 + 200000.0)


def test_resultant_rejects_unknown_case_value():
    s = LoadCaseSet()
    with pytest.raises(LoadTransferError):
        s.resultant_at(Point3D(0, 0, 0), cases=["рабочий_режим"])


# ---------------------------------------------------------------------------
# Независимая проверка (продолжение, 18.09.2026, п. «P1»): отсутствие
# запрошенного режима в наборе — контролируемая ошибка, не физический ноль.
# ---------------------------------------------------------------------------

def test_resultant_at_missing_requested_case_raises_not_silent_zero():
    s = LoadCaseSet()
    s.add(_load(load_case=LoadCase.OPERATING, fz_n=-50.0))
    with pytest.raises(LoadTransferError):
        s.resultant_at(Point3D(0, 0, 0), cases=[LoadCase.STARTUP])


def test_resultant_at_missing_case_among_several_requested_still_raises():
    s = LoadCaseSet()
    s.add(_load(load_case=LoadCase.OPERATING, fz_n=-50.0))
    with pytest.raises(LoadTransferError):
        s.resultant_at(Point3D(0, 0, 0), cases=[LoadCase.OPERATING, LoadCase.STARTUP])


def test_resultant_at_explicit_zero_load_vector_is_distinguishable_from_missing():
    # Явно подтверждённый ноль: LoadVector с нулевыми компонентами и явным
    # source — это НЕ то же самое, что отсутствие данных о режиме.
    s = LoadCaseSet()
    s.add(_load(load_case=LoadCase.STARTUP, fx_n=0.0, fy_n=0.0, fz_n=0.0,
                source="подтверждено: пуск не нагружает эту опору", label="пуск_ноль"))
    result = s.resultant_at(Point3D(0, 0, 0), cases=[LoadCase.STARTUP])
    assert result.fz_n == pytest.approx(0.0)
    assert result.contributing_count == 1  # отличимо от missing (который вообще не возвращает результат)


def test_resultant_at_allow_missing_cases_opts_out_of_the_error():
    s = LoadCaseSet()
    s.add(_load(load_case=LoadCase.OPERATING, fz_n=-50.0))
    result = s.resultant_at(
        Point3D(0, 0, 0), cases=[LoadCase.OPERATING, LoadCase.STARTUP],
        allow_missing_cases=[LoadCase.STARTUP],
    )
    assert result.fz_n == pytest.approx(-50.0)
    assert result.contributing_count == 1


# ---------------------------------------------------------------------------
# Независимая проверка (продолжение, 18.09.2026, п. «P1»): нельзя молча
# суммировать нагрузки, посчитанные для разных ревизий/снимков входных данных.
# ---------------------------------------------------------------------------

def test_resultant_at_rejects_mixed_product_revisions():
    s = LoadCaseSet()
    s.add(_load(load_case=LoadCase.OPERATING, fz_n=-50.0, label="a", product_revision="rev1"))
    s.add(_load(load_case=LoadCase.OPERATING, fz_n=-30.0, label="b", product_revision="rev2"))
    with pytest.raises(LoadTransferError):
        s.resultant_at(Point3D(0, 0, 0), cases=[LoadCase.OPERATING])


def test_resultant_at_rejects_mixed_input_fingerprints():
    s = LoadCaseSet()
    s.add(_load(load_case=LoadCase.OPERATING, fz_n=-50.0, label="a", input_fingerprint="fp1"))
    s.add(_load(load_case=LoadCase.OPERATING, fz_n=-30.0, label="b", input_fingerprint="fp2"))
    with pytest.raises(LoadTransferError):
        s.resultant_at(Point3D(0, 0, 0), cases=[LoadCase.OPERATING])


def test_resultant_at_allows_mixing_when_revision_untracked_on_some_loads():
    # Нагрузка без указанной ревизии не блокирует суммирование — иначе
    # большинство синтетических/исследовательских расчётов ложно ломались бы.
    s = LoadCaseSet()
    s.add(_load(load_case=LoadCase.OPERATING, fz_n=-50.0, label="a", product_revision="rev1"))
    s.add(_load(load_case=LoadCase.OPERATING, fz_n=-30.0, label="b"))  # ревизия не указана
    result = s.resultant_at(Point3D(0, 0, 0), cases=[LoadCase.OPERATING])
    assert result.fz_n == pytest.approx(-80.0)
    assert result.product_revision == "rev1"


def test_resultant_at_same_revision_and_fingerprint_are_accepted_and_propagated():
    s = LoadCaseSet()
    s.add(_load(load_case=LoadCase.OPERATING, fz_n=-50.0, label="a",
                product_revision="rev1", input_fingerprint="fp1"))
    s.add(_load(load_case=LoadCase.OPERATING, fz_n=-30.0, label="b",
                product_revision="rev1", input_fingerprint="fp1"))
    result = s.resultant_at(Point3D(0, 0, 0), cases=[LoadCase.OPERATING])
    assert result.product_revision == "rev1"
    assert result.input_fingerprint == "fp1"


# ---------------------------------------------------------------------------
# Независимая проверка (продолжение, 18.09.2026, п. «P1»): защита от дублей
# работает независимо от способа создания набора, и её нельзя обойти
# косметической сменой label или прямым редактированием списка.
# ---------------------------------------------------------------------------

def test_constructor_with_initial_loads_still_deduplicates():
    duplicate = _load(label="реакция_A")
    with pytest.raises(LoadTransferError):
        LoadCaseSet(loads=[duplicate, duplicate])


def test_constructor_with_initial_loads_populates_set_when_valid():
    a = _load(label="a", fz_n=-10.0)
    b = _load(label="b", fz_n=-20.0)
    s = LoadCaseSet(loads=[a, b])
    assert len(s.loads) == 2


def test_loads_property_is_read_only_direct_append_does_not_mutate_set():
    s = LoadCaseSet()
    s.add(_load(label="a"))
    with pytest.raises(AttributeError):
        s.loads.append(_load(label="сквозь_обход"))
    assert len(s.loads) == 1


def test_add_rejects_identical_nonzero_vector_reused_under_a_new_label():
    s = LoadCaseSet()
    s.add(_load(label="реакция_A", fz_n=-100.0))
    with pytest.raises(LoadTransferError):
        s.add(_load(label="реакция_A_повтор", fz_n=-100.0))  # тот же вектор, другая метка


def test_add_allows_identical_zero_vector_under_different_labels():
    # Явные подтверждённые нули под разными метками — законный случай,
    # не должен ложно отклоняться защитой от переименованных дублей.
    s = LoadCaseSet()
    s.add(_load(label="ноль_1"))
    s.add(_load(label="ноль_2"))
    assert len(s.loads) == 2


# ---------------------------------------------------------------------------
# Независимая проверка коммита c24d42b, раздел 2: LoadVector/ResultantLoad
# должны быть НЕИЗМЕНЯЕМЫМИ снимками (repro: `s.loads[0].fz_n = -999` менял
# уже принятую в набор нагрузку на месте, без пересчёта дублей/ревизии).
# ---------------------------------------------------------------------------

def test_load_vector_is_immutable():
    load = _load(fz_n=-100.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        load.fz_n = -999.0


def test_load_case_set_stored_vector_cannot_be_mutated_in_place():
    # Repro из независимой проверки: `s.loads[0].fz_n = -999` больше не
    # работает физически (LoadVector теперь frozen), поэтому набор не
    # может незаметно "изменить" уже принятую нагрузку в обход add().
    s = LoadCaseSet()
    s.add(_load(label="реакция_A", fz_n=-100.0))
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.loads[0].fz_n = -999.0
    assert s.loads[0].fz_n == pytest.approx(-100.0)


def test_resultant_load_is_immutable():
    s = LoadCaseSet()
    s.add(_load(label="a", fz_n=-100.0))
    result = s.resultant_at(Point3D(0.0, 0.0, 0.0), cases=[LoadCase.OPERATING])
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.fz_n = 12345.0
