# -*- coding: utf-8 -*-
"""
Общий 3D-решатель пространственной рамы методом перемещений (метод конечных
элементов, балочный элемент с 6 степенями свободы на узел) — раздел 3-4
доп. задания: "корпус — расчёт на РЕАЛЬНЫХ опорах... полноценный решатель
для ПРОИЗВОЛЬНОГО/статически неопределимого числа опор" и "рама — с
изгибной+осевой+крутильной жёсткостью, а не тихое допущение шарнирной
фермы".

ПОЧЕМУ ОДИН ОБЩИЙ РЕШАТЕЛЬ ДЛЯ КОРПУСА И РАМЫ. Метод перемещений (метод
конечных элементов) РАВНО применим к статически определимой и статически
неопределимой схеме — количество опор/связей не требует разного алгоритма,
только разного размера системы уравнений. Поэтому и "корпус как балка на
точках крепления к раме" (обычно цепочка узлов вдоль одной оси), и "рама
как пространственная конструкция" (узлы в 3D, элементы в разных
направлениях, опоры на полу/фундаменте) — это ОДНА и та же модель
`FrameModel`, применённая дважды с разной геометрией и разным набором
опор. Не два отдельных, отдельно проверяемых решателя.

МЕТОД. Классический метод конечных элементов для пространственного
стержня (12 степеней свободы на элемент: 6 на каждый узел — 3 перемещения
+ 3 поворота). Локальная матрица жёсткости — без сдвиговой поправки
(Эйлер–Бернулли по обеим плоскостям изгиба + осевая жёсткость EA/L +
крутильная жёсткость GJ/L) — тот же уровень допущения, что и в
core/shaft_beam_model.py (см. его докстринг про L/D≥10 как ПРЕДВАРИТЕЛЬНЫЙ
фильтр, не доказательство) — здесь то же самое допущение переносится на
раму/корпус явно, а не молча.

ОГРАНИЧЕНИЕ ЭТОЙ ВЕРСИИ (честно, не скрыто): нагрузки принимаются ТОЛЬКО
в узлах (сосредоточенные силы/моменты). Распределённая нагрузка вдоль
элемента (напр. собственный вес длинного участка корпуса) сюда войти
может только через ЭКВИВАЛЕНТНЫЕ УЗЛОВЫЕ нагрузки, посчитанные вызывающим
кодом (напр. разбить длинный элемент на несколько между промежуточными
узлами и приложить в них сосредоточенные доли веса — стандартный приём
дискретизации, а не пренебрежение весом). Модуль явно ХРАНИТ список
элементов БЕЗ распределённой нагрузки как факт схемы, не подставляя
скрытое приближение "распределённая нагрузка = 0" без предупреждения —
см. `FrameModel.known_limitations()`.

ПРОВЕРКА РЕШАТЕЛЯ. `calculator/tests/test_frame_model.py`:
- консоль (одна жёсткая заделка) с торцевой силой — сверка с закрытой
  формулой PL³/3EI, PL²/2EI (учебник сопромата);
- балка на двух шарнирных опорах, смоделированная как цепочка элементов —
  сверка с core/shaft_beam_model.py (два НЕЗАВИСИМЫХ решателя должны дать
  одно и то же число для одной и той же классической задачи);
- статически НЕОПРЕДЕЛИМАЯ схема (защемлённо-опёртая балка/"propped
  cantilever" с точечной силой в середине) — сверка с табличным решением
  (R_опоры=5P/16, момент заделки=3PL/16) — это ПРЯМАЯ проверка того, что
  решатель корректно работает для статически неопределимой схемы, не
  только для определимой.
- проверка равновесия: сумма реакций + приложенных нагрузок = 0 по силам
  и моментам относительно произвольной точки — на КАЖДОМ решённом случае,
  не только в тестах решателя (см. `FrameSolution.equilibrium_residual`).

Источники метода: Przemieniecki J.S., "Theory of Matrix Structural
Analysis"; McGuire/Gallagher/Ziemian, "Matrix Structural Analysis" —
локальная матрица жёсткости пространственного стержневого элемента.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from calculator.core.linalg_dense import LinAlgError, solve_linear_system, zeros, zeros_vector
from calculator.core.load_transfer import LoadCase, LoadVector, Point3D, ResultantLoad

DOF_PER_NODE = 6
DOF_NAMES = ("ux", "uy", "uz", "rx", "ry", "rz")


class FrameModelError(ValueError):
    pass


def _finite(name: str, value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FrameModelError(f"{name}: ожидалось число, получено {type(value).__name__} ({value!r}).")
    if not math.isfinite(value):
        raise FrameModelError(f"{name}: значение должно быть конечным числом, получено {value!r}.")
    return float(value)


# --------------------------------------------------------------------------
# Векторная алгебра (минимум, без numpy — см. core/linalg_dense.py)
# --------------------------------------------------------------------------

def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(a):
    return math.sqrt(_dot(a, a))


def _normalize(a, what: str):
    n = _norm(a)
    if n < 1e-9:
        raise FrameModelError(f"{what}: нулевой вектор нельзя нормировать.")
    return (a[0] / n, a[1] / n, a[2] / n)


# --------------------------------------------------------------------------
# Узлы, опоры, элементы
# --------------------------------------------------------------------------

@dataclass
class FrameNode:
    node_id: str
    point: Point3D
    label: str = ""

    def __post_init__(self) -> None:
        if not self.node_id:
            raise FrameModelError("node_id обязателен.")


@dataclass
class Support:
    """
    Опора узла — ПРОИЗВОЛЬНАЯ комбинация закреплённых степеней свободы
    (раздел задания: "не назначай обеим опорам полную заделку молча" —
    здесь наоборот, любая комбинация ЯВНО перечисляется, ничего не
    подразумевается по умолчанию, кроме удобных именованных пресетов).
    """

    node_id: str
    restrained: tuple  # tuple[bool,...] длиной 6, порядок DOF_NAMES
    label: str = ""

    def __post_init__(self) -> None:
        if len(self.restrained) != DOF_PER_NODE:
            raise FrameModelError(f"restrained должен содержать ровно {DOF_PER_NODE} значений (по числу DOF).")
        if not any(self.restrained):
            raise FrameModelError("Опора без единой закреплённой степени свободы — это не опора.")

    @staticmethod
    def fixed(node_id: str, label: str = "") -> "Support":
        """Полная жёсткая заделка — все 6 DOF закреплены."""
        return Support(node_id=node_id, restrained=(True,) * 6, label=label)

    @staticmethod
    def pinned(node_id: str, label: str = "") -> "Support":
        """Шарнирная опора — все 3 перемещения закреплены, все 3 поворота свободны."""
        return Support(node_id=node_id, restrained=(True, True, True, False, False, False), label=label)

    @staticmethod
    def roller(node_id: str, free_translation: str, label: str = "") -> "Support":
        """
        Каток — закреплены 2 из 3 перемещений, поворот свободен. `free_translation`
        — какое перемещение ('ux'|'uy'|'uz') остаётся свободным.
        """
        if free_translation not in ("ux", "uy", "uz"):
            raise FrameModelError("free_translation должен быть одним из 'ux','uy','uz'.")
        restrained = [True, True, True, False, False, False]
        restrained[DOF_NAMES.index(free_translation)] = False
        return Support(node_id=node_id, restrained=tuple(restrained), label=label)


@dataclass
class SectionProperties:
    """
    Жёсткостные характеристики элемента — ВСЕГДА явный вход (не выводятся
    из "типового" профиля без источника, см. общую политику репозитория
    "не выдумывай числа"). Для полого круглого сечения удобно построить из
    core.shaft_beam_model.HollowCircularSection (area_mm2/moment_of_inertia_mm4/
    polar_moment_of_inertia_mm4) — этот класс НЕ дублирует ту геометрию,
    только хранит уже посчитанные жёсткости плюс модуль сдвига G.
    """

    e_mpa: float
    g_mpa: float
    area_mm2: float
    iy_mm4: float
    iz_mm4: float
    j_mm4: float
    source: str = "UNKNOWN"

    def __post_init__(self) -> None:
        for name in ("e_mpa", "g_mpa", "area_mm2", "iy_mm4", "iz_mm4", "j_mm4"):
            value = _finite(name, getattr(self, name))
            if value <= 0:
                raise FrameModelError(f"{name} должен быть больше нуля, получено {value}.")
            setattr(self, name, value)


@dataclass
class FrameMember:
    """
    Пространственный стержневой элемент между двумя узлами. `reference_up`
    — вектор, задающий ориентацию локальных осей y/z (не должен быть
    параллелен оси элемента) — ЯВНОЕ ДОПУЩЕНИЕ о повороте сечения вокруг
    собственной оси, если не задано вызывающим кодом (см. FrameModel._
    local_axes — допущение по умолчанию: глобальный Z, либо глобальный X
    для вертикальных элементов), поэтому по умолчанию помечается как
    ДОПУЩЕНИЕ, а не факт конструкции.
    """

    member_id: str
    node_i: str
    node_j: str
    section: SectionProperties
    reference_up: Optional[tuple] = None
    label: str = ""


# --------------------------------------------------------------------------
# Локальная матрица жёсткости пространственного стержня (12×12)
# --------------------------------------------------------------------------

def _local_stiffness_matrix(length_mm: float, sec: SectionProperties) -> list:
    length = length_mm
    e, g, a = sec.e_mpa, sec.g_mpa, sec.area_mm2
    iy, iz, j = sec.iy_mm4, sec.iz_mm4, sec.j_mm4
    l2, l3 = length ** 2, length ** 3

    k = zeros(12, 12)

    # Осевая жёсткость: [u1, u2] = индексы [0, 6]
    axial = e * a / length
    k[0][0] += axial; k[0][6] -= axial
    k[6][0] -= axial; k[6][6] += axial

    # Крутильная жёсткость: [rx1, rx2] = индексы [3, 9]
    tor = g * j / length
    k[3][3] += tor; k[3][9] -= tor
    k[9][3] -= tor; k[9][9] += tor

    # Изгиб в плоскости xy (перемещение uy, поворот rz) — индексы [1,5,7,11], жёсткость EIz
    ez = e * iz
    kb = [
        [12 * ez / l3, 6 * ez / l2, -12 * ez / l3, 6 * ez / l2],
        [6 * ez / l2, 4 * ez / length, -6 * ez / l2, 2 * ez / length],
        [-12 * ez / l3, -6 * ez / l2, 12 * ez / l3, -6 * ez / l2],
        [6 * ez / l2, 2 * ez / length, -6 * ez / l2, 4 * ez / length],
    ]
    idx_xy = [1, 5, 7, 11]
    for a_i, gi in enumerate(idx_xy):
        for a_j, gj in enumerate(idx_xy):
            k[gi][gj] += kb[a_i][a_j]

    # Изгиб в плоскости xz (перемещение uz, поворот ry) — индексы [2,4,8,10], жёсткость EIy.
    # Знаки смежных членов инвертированы относительно xy-плоскости — стандартный
    # результат правостороннего правила для поворота вокруг ДРУГОЙ оси (см. источники модуля).
    ey = e * iy
    kb2 = [
        [12 * ey / l3, -6 * ey / l2, -12 * ey / l3, -6 * ey / l2],
        [-6 * ey / l2, 4 * ey / length, 6 * ey / l2, 2 * ey / length],
        [-12 * ey / l3, 6 * ey / l2, 12 * ey / l3, 6 * ey / l2],
        [-6 * ey / l2, 2 * ey / length, 6 * ey / l2, 4 * ey / length],
    ]
    idx_xz = [2, 4, 8, 10]
    for a_i, gi in enumerate(idx_xz):
        for a_j, gj in enumerate(idx_xz):
            k[gi][gj] += kb2[a_i][a_j]

    return k


def _local_axes(node_i: Point3D, node_j: Point3D, reference_up: Optional[tuple]) -> tuple:
    """
    Строит правый ортонормированный базис (local_x, local_y, local_z) по
    оси элемента и опорному вектору "верх". Если reference_up не задан —
    ДОПУЩЕНИЕ по умолчанию: глобальный Z (0,0,1), а для элементов, почти
    параллельных Z (типично колонны/вертикальные связи), запасной вариант —
    глобальный X (1,0,0). Это стандартная инженерная практика КЭ-программ,
    но именно ДОПУЩЕНИЕ об ориентации сечения вокруг своей оси, если оно
    физически не задано (напр. непрямоугольная/несимметричная форма
    сечения, для которой поворот вокруг оси важен) — см. FrameMember.
    """
    local_x = _normalize(_sub(node_j.as_tuple(), node_i.as_tuple()), "ось элемента (node_j - node_i)")
    if reference_up is None:
        candidate = (0.0, 0.0, 1.0)
        if abs(_dot(local_x, candidate)) > 0.999:
            candidate = (1.0, 0.0, 0.0)
        reference_up = candidate
    else:
        reference_up = _normalize(reference_up, "reference_up")
        if abs(_dot(local_x, reference_up)) > 0.999:
            raise FrameModelError(
                "reference_up почти параллелен оси элемента — ориентация локальных осей неоднозначна; "
                "укажите другой опорный вектор."
            )
    local_y = _normalize(_cross(reference_up, local_x), "local_y")
    local_z = _cross(local_x, local_y)
    return local_x, local_y, local_z


def _transformation_matrix(local_x, local_y, local_z) -> list:
    """
    12×12 блочно-диагональная матрица поворота (4 блока 3×3 — по числу
    трёхкомпонентных величин: перемещение/поворот на каждом из двух узлов).
    """
    r3 = [list(local_x), list(local_y), list(local_z)]
    t = zeros(12, 12)
    for block in range(4):
        base = block * 3
        for i in range(3):
            for j in range(3):
                t[base + i][base + j] = r3[i][j]
    return t


def _matT_mat_mat(t: list, k_local: list) -> list:
    """T^T · K_local · T без зависимостей — размеры всегда 12×12 здесь."""
    from calculator.core.linalg_dense import matmul, transpose
    return matmul(matmul(transpose(t), k_local), t)


# --------------------------------------------------------------------------
# Модель и решение
# --------------------------------------------------------------------------

def _points_match(a: "Point3D", b: "Point3D", *, tol_mm: float = 1e-6) -> bool:
    return (
        abs(a.x_mm - b.x_mm) <= tol_mm and abs(a.y_mm - b.y_mm) <= tol_mm and abs(a.z_mm - b.z_mm) <= tol_mm
    )


@dataclass(frozen=True)
class NodalLoad:
    """
    Сосредоточенная узловая нагрузка. `source`/`load_cases`/
    `product_revision`/`input_fingerprint` (продолжение, 18.09.2026, п.
    «P1») — НЕ обязательные для ручного `NodalLoad(...)` (так уже писались
    все тесты решателя на закрытых формулах, где дисциплина происхождения
    не нужна), но ОБЯЗАТЕЛЬНО заполняются при переносе из
    core/load_transfer.py через `from_load_vector()`/`from_resultant()` —
    раньше при таком переносе (см. вызовы NodalLoad(fz_n=transferred.fz_n,
    ...) в синтетическом примере) источник, режим нагружения, ревизия и
    fingerprint терялись: в FrameModel попадали голые числа, без
    возможности проверить, из какого расчёта/режима/снимка входных данных
    они взяты.

    НЕИЗМЕНЯЕМ (`frozen=True`, независимая проверка коммита c24d42b,
    раздел 2, та же причина, что и `load_transfer.LoadVector`) — узловая
    нагрузка, уже переданная в `FrameModel`, не должна быть изменяемой
    задним числом в обход пересчёта.
    """

    node_id: str
    fx_n: float = 0.0
    fy_n: float = 0.0
    fz_n: float = 0.0
    mx_nmm: float = 0.0
    my_nmm: float = 0.0
    mz_nmm: float = 0.0
    label: str = ""
    source: str = ""
    load_cases: tuple = ()
    product_revision: str = ""
    input_fingerprint: str = ""

    def as_vector(self) -> tuple:
        return (self.fx_n, self.fy_n, self.fz_n, self.mx_nmm, self.my_nmm, self.mz_nmm)

    @staticmethod
    def from_load_vector(
        node_id: str, vector: "LoadVector", *, label: Optional[str] = None,
        expected_point: Optional["Point3D"] = None,
    ) -> "NodalLoad":
        """
        Перенос ОДНОЙ уже перенесённой в нужную точку LoadVector в узловую
        нагрузку решателя рамы. `expected_point` (независимая проверка
        c24d42b, раздел 2: "при преобразовании LoadVector в NodalLoad
        проверяй совпадение точки приложения с координатой узла либо явно
        выполняй перенос") — если передан координатой узла `node_id` в
        `FrameModel`, а `vector.point` ей НЕ соответствует, это значит,
        что нагрузку забыли перенести (`LoadVector.transferred_to(...)`)
        перед тем, как положить её в узел с ДРУГИМИ координатами — момент
        в этом случае относился бы не к той точке. Без `expected_point`
        (не передан) проверка не выполняется — вызывающий код не обязан
        знать координату узла в месте построения (напр. в тестах решателя
        на закрытых формулах).
        """
        if expected_point is not None and not _points_match(vector.point, expected_point):
            raise FrameModelError(
                f"LoadVector.point={vector.point!r} не совпадает с координатой узла "
                f"{node_id!r} ({expected_point!r}) — перенесите нагрузку в точку узла "
                "через LoadVector.transferred_to(...) ПЕРЕД построением NodalLoad, "
                "иначе момент будет отнесён не к той точке."
            )
        return NodalLoad(
            node_id=node_id, fx_n=vector.fx_n, fy_n=vector.fy_n, fz_n=vector.fz_n,
            mx_nmm=vector.mx_nmm, my_nmm=vector.my_nmm, mz_nmm=vector.mz_nmm,
            label=label if label is not None else vector.label,
            source=vector.source, load_cases=(vector.load_case,),
            product_revision=vector.product_revision, input_fingerprint=vector.input_fingerprint,
        )

    @staticmethod
    def from_resultant(
        node_id: str, resultant: "ResultantLoad", *, label: Optional[str] = None,
        expected_point: Optional["Point3D"] = None,
    ) -> "NodalLoad":
        """Перенос РЕЗУЛЬТИРУЮЩЕЙ (суммы нескольких режимов) нагрузки из LoadCaseSet.resultant_at().
        `expected_point` — та же проверка совпадения точки, что и в `from_load_vector()`."""
        if expected_point is not None and not _points_match(resultant.point, expected_point):
            raise FrameModelError(
                f"ResultantLoad.point={resultant.point!r} не совпадает с координатой узла "
                f"{node_id!r} ({expected_point!r}) — resultant_at(point=...) должен был "
                "получить координату этого узла."
            )
        return NodalLoad(
            node_id=node_id, fx_n=resultant.fx_n, fy_n=resultant.fy_n, fz_n=resultant.fz_n,
            mx_nmm=resultant.mx_nmm, my_nmm=resultant.my_nmm, mz_nmm=resultant.mz_nmm,
            label=label if label is not None else resultant.note,
            source="load_transfer.LoadCaseSet.resultant_at", load_cases=resultant.load_cases,
            product_revision=resultant.product_revision, input_fingerprint=resultant.input_fingerprint,
        )


@dataclass
class FrameModel:
    nodes: list
    members: list
    supports: list
    loads: list = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.nodes) < 2:
            raise FrameModelError("Модели нужно минимум 2 узла.")
        ids = [n.node_id for n in self.nodes]
        if len(set(ids)) != len(ids):
            raise FrameModelError("Идентификаторы узлов должны быть уникальны.")
        self._node_index = {n.node_id: i for i, n in enumerate(self.nodes)}
        for m in self.members:
            for ref in (m.node_i, m.node_j):
                if ref not in self._node_index:
                    raise FrameModelError(f"Элемент {m.member_id!r} ссылается на несуществующий узел {ref!r}.")
            if m.node_i == m.node_j:
                raise FrameModelError(f"Элемент {m.member_id!r}: node_i и node_j совпадают.")
        member_ids = [m.member_id for m in self.members]
        if len(set(member_ids)) != len(member_ids):
            raise FrameModelError("Идентификаторы элементов должны быть уникальны.")
        for s in self.supports:
            if s.node_id not in self._node_index:
                raise FrameModelError(f"Опора ссылается на несуществующий узел {s.node_id!r}.")
        support_nodes = [s.node_id for s in self.supports]
        if len(set(support_nodes)) != len(support_nodes):
            raise FrameModelError("На одном узле не может быть двух отдельных записей Support — объедините в одну.")
        for load in self.loads:
            if load.node_id not in self._node_index:
                raise FrameModelError(f"Нагрузка ссылается на несуществующий узел {load.node_id!r}.")

        # Неизменяемый расчётный снимок (независимая проверка c24d42b,
        # раздел 2) — `self.loads` заменяется на `tuple` НЕИЗМЕНЯЕМЫХ
        # `NodalLoad` (см. их frozen=True): список нагрузок, с которым
        # реально решает `solve()`, нельзя дополнить/заменить в обход
        # конструктора уже ПОСЛЕ создания модели.
        self.loads = tuple(self.loads)

        # Проверка согласованности ревизии/снимка входных данных НА ГРАНИЦЕ
        # решателя (независимая проверка c24d42b, раздел 2: "FrameModel.
        # solve() принимает одновременно NodalLoad с ревизиями old/new и
        # fingerprint old/new и выдаёт обычный результат — метки
        # сохраняются, но не проверяются"). Та же дисциплина, что и в
        # load_transfer.LoadCaseSet.resultant_at(): сравниваются только
        # ЯВНО заданные (непустые) значения, чтобы не ломать существующие
        # тесты/исследовательские расчёты, не отслеживающие ревизию.
        revisions = {ld.product_revision for ld in self.loads if ld.product_revision}
        if len(revisions) > 1:
            raise FrameModelError(
                f"Нельзя решать модель с узловыми нагрузками разных product_revision: "
                f"{sorted(revisions)} — это разные состояния изделия/анкеты; пересчитайте "
                "нагрузки под единую ревизию перед сборкой FrameModel (независимая проверка "
                "c24d42b, раздел 2)."
            )
        fingerprints = {ld.input_fingerprint for ld in self.loads if ld.input_fingerprint}
        if len(fingerprints) > 1:
            raise FrameModelError(
                f"Нельзя решать модель с узловыми нагрузками разных input_fingerprint: "
                f"{sorted(fingerprints)} — нагрузки посчитаны для разных снимков входных "
                "данных (независимая проверка c24d42b, раздел 2)."
            )

    def known_limitations(self) -> list:
        return [
            "Нагрузки принимаются только в узлах — распределённая нагрузка вдоль элемента "
            "(напр. собственный вес) должна быть заранее приведена к узловым нагрузкам "
            "вызывающим кодом (дискретизация на промежуточные узлы).",
            "Балочный элемент без сдвиговой поправки (Эйлер–Бернулли) — то же допущение, "
            "что и в core/shaft_beam_model.py (см. euler_bernoulli_applicable — ПРЕДВАРИТЕЛЬНЫЙ "
            "фильтр по L/D, не доказательство).",
            "Внутренние силовые факторы вдоль элемента интерполируются как для элемента БЕЗ "
            "внутренней распределённой нагрузки (N/V/T постоянны, M линеен) — корректно только "
            "если вся нагрузка приведена к узлам, как указано выше.",
        ]

    def node(self, node_id: str) -> FrameNode:
        return self.nodes[self._node_index[node_id]]

    def dof_index(self, node_id: str, dof_name: str) -> int:
        return self._node_index[node_id] * DOF_PER_NODE + DOF_NAMES.index(dof_name)

    def n_dof(self) -> int:
        return len(self.nodes) * DOF_PER_NODE

    def solve(self) -> "FrameSolution":
        n = self.n_dof()
        k_global = zeros(n, n)
        member_axes = {}
        member_transforms = {}
        member_lengths = {}

        for m in self.members:
            ni, nj = self.node(m.node_i), self.node(m.node_j)
            length = _norm(_sub(nj.point.as_tuple(), ni.point.as_tuple()))
            if length < 1e-6:
                raise FrameModelError(f"Элемент {m.member_id!r} имеет нулевую длину.")
            axes = _local_axes(ni.point, nj.point, m.reference_up)
            t = _transformation_matrix(*axes)
            k_local = _local_stiffness_matrix(length, m.section)
            k_global_elem = _matT_mat_mat(t, k_local)
            member_axes[m.member_id] = axes
            member_transforms[m.member_id] = t
            member_lengths[m.member_id] = length

            gi = self._node_index[m.node_i] * DOF_PER_NODE
            gj = self._node_index[m.node_j] * DOF_PER_NODE
            global_map = list(range(gi, gi + 6)) + list(range(gj, gj + 6))
            for a in range(12):
                for b in range(12):
                    k_global[global_map[a]][global_map[b]] += k_global_elem[a][b]

        f_global = zeros_vector(n)
        for load in self.loads:
            base = self._node_index[load.node_id] * DOF_PER_NODE
            vec = load.as_vector()
            for i in range(6):
                f_global[base + i] += vec[i]

        restrained_mask = [False] * n
        support_by_node = {s.node_id: s for s in self.supports}
        for node_id, s in support_by_node.items():
            base = self._node_index[node_id] * DOF_PER_NODE
            for i, is_restrained in enumerate(s.restrained):
                if is_restrained:
                    restrained_mask[base + i] = True

        free = [i for i in range(n) if not restrained_mask[i]]
        fixed = [i for i in range(n) if restrained_mask[i]]
        if not free:
            raise FrameModelError("Все степени свободы закреплены — решать нечего.")

        k_ff = [[k_global[i][j] for j in free] for i in free]
        f_f = [f_global[i] for i in free]
        try:
            u_f = solve_linear_system(k_ff, f_f)
        except LinAlgError as exc:
            raise FrameModelError(
                f"Система неустойчива (вероятно, механизм — недостаточно опор): {exc}"
            ) from exc

        u = zeros_vector(n)
        for idx, val in zip(free, u_f):
            u[idx] = val

        # Реакции: R_c = (K·u)_c - F_c на закреплённых DOF.
        reactions_full = zeros_vector(n)
        for i in fixed:
            ku_i = sum(k_global[i][j] * u[j] for j in range(n))
            reactions_full[i] = ku_i - f_global[i]

        return FrameSolution(
            model=self, displacements=u, reactions=reactions_full,
            restrained_mask=restrained_mask, member_axes=member_axes,
            member_transforms=member_transforms, member_lengths=member_lengths,
            k_global=k_global, f_global=f_global,
        )


@dataclass
class MemberEndForces:
    member_id: str
    # Локальные силы/моменты на конце i и конце j (знак — растяжение N>0,
    # остальное — по локальным осям элемента).
    n_i: float
    vy_i: float
    vz_i: float
    t_i: float
    my_i: float
    mz_i: float
    n_j: float
    vy_j: float
    vz_j: float
    t_j: float
    my_j: float
    mz_j: float


@dataclass
class FrameSolution:
    model: FrameModel
    displacements: list
    reactions: list
    restrained_mask: list
    member_axes: dict
    member_transforms: dict
    member_lengths: dict
    k_global: list
    f_global: list

    def displacement_at(self, node_id: str, dof_name: str) -> float:
        return self.displacements[self.model.dof_index(node_id, dof_name)]

    def reaction_at(self, node_id: str, dof_name: str) -> float:
        return self.reactions[self.model.dof_index(node_id, dof_name)]

    def member_end_forces(self, member_id: str) -> MemberEndForces:
        m = next((mm for mm in self.model.members if mm.member_id == member_id), None)
        if m is None:
            raise FrameModelError(f"Неизвестный элемент {member_id!r}.")
        gi = self.model._node_index[m.node_i] * DOF_PER_NODE
        gj = self.model._node_index[m.node_j] * DOF_PER_NODE
        u_elem = self.displacements[gi:gi + 6] + self.displacements[gj:gj + 6]
        t = self.member_transforms[member_id]
        u_local = [sum(t[row][col] * u_elem[col] for col in range(12)) for row in range(12)]
        k_local = _local_stiffness_matrix(self.member_lengths[member_id], m.section)
        f_local = [sum(k_local[row][col] * u_local[col] for col in range(12)) for row in range(12)]
        return MemberEndForces(
            member_id=member_id,
            n_i=f_local[0], vy_i=f_local[1], vz_i=f_local[2],
            t_i=f_local[3], my_i=f_local[4], mz_i=f_local[5],
            n_j=f_local[6], vy_j=f_local[7], vz_j=f_local[8],
            t_j=f_local[9], my_j=f_local[10], mz_j=f_local[11],
        )

    def transverse_displacement_along_member(self, member_id: str, s_mm: float) -> tuple:
        """
        ГЛОБАЛЬНЫЙ 3D-вектор ЧИСТО ПОПЕРЕЧНОГО (перпендикулярного оси
        элемента) изгибного перемещения точки оси элемента на локальной
        координате `s_mm` (0 ≤ s_mm ≤ длина элемента) — независимая
        проверка коммита c24d42b, раздел 5 ("реализуй перемещения внутри
        элементов с согласованной интерполяцией... для наклонной оси
        сравнивай перемещения в общей системе и проецируй разность на
        поперечную плоскость").

        МЕТОД. Кубическая интерполяция Эрмита по узловым перемещениям и
        поворотам концов ЭТОГО ЖЕ элемента — ТОЧНОЕ решение уравнения
        изгиба для элемента БЕЗ внутренней распределённой нагрузки (см.
        `known_limitations` — вся нагрузка в этой модели узловая, поэтому
        внутри элемента M(x) линеен, V(x) постоянен, а форма — кубика;
        это СОГЛАСОВАННАЯ постобработка того же самого элемента, который
        решил МКЭ, а не отдельная независимая аппроксимация формы). В
        КАЖДОЙ из двух плоскостей изгиба (местные xy и xz) отдельная
        кубика Эрмита:
            v(s) = N1·v_i + N2·θ'_i + N3·v_j + N4·θ'_j,  ξ=s/L,
            N1=1−3ξ²+2ξ³, N2=L(ξ−2ξ²+ξ³), N3=3ξ²−2ξ³, N4=L(−ξ²+ξ³).
        θ' — производная прогиба (dv/dx), НЕ напрямую местный поворот:
        по знаковому соглашению локальной матрицы жёсткости этого модуля
        (см. `_local_stiffness_matrix`, docstring про "знаки инвертированы
        относительно xy-плоскости") в плоскости xy местный rz = +dv/dx
        (стандартное соглашение), а в плоскости xz местный ry = −dw/dx
        (см. проверку числом против замкнутого решения консоли в
        tests/test_frame_model.py — оба соглашения сверены с закрытой
        формулой balки на изгиб).

        Проекция на поперечную плоскость (для наклонной оси) получается
        АВТОМАТИЧЕСКИ: local_y/local_z ортонормированы к local_x самим
        построением базиса (`_local_axes`), поэтому v(s)·local_y +
        w(s)·local_z — уже ЧИСТО перпендикулярная оси элемента
        составляющая в ГЛОБАЛЬНЫХ координатах, без отдельного шага
        проецирования.
        """
        m = next((mm for mm in self.model.members if mm.member_id == member_id), None)
        if m is None:
            raise FrameModelError(f"Неизвестный элемент {member_id!r}.")
        length = self.member_lengths[member_id]
        s_mm = _finite("s_mm", s_mm)
        if not (-1e-6 <= s_mm <= length + 1e-6):
            raise FrameModelError(
                f"s_mm={s_mm} вне длины элемента {member_id!r} [0, {length}] — "
                "интерполяция определена только ВНУТРИ элемента."
            )
        s_mm = min(max(s_mm, 0.0), length)

        gi = self.model._node_index[m.node_i] * DOF_PER_NODE
        gj = self.model._node_index[m.node_j] * DOF_PER_NODE
        u_elem = self.displacements[gi:gi + 6] + self.displacements[gj:gj + 6]
        t = self.member_transforms[member_id]
        u_local = [sum(t[row][col] * u_elem[col] for col in range(12)) for row in range(12)]
        # u_local индексы: [ux_i,uy_i,uz_i,rx_i,ry_i,rz_i, ux_j,uy_j,uz_j,rx_j,ry_j,rz_j]
        v_i, v_j = u_local[1], u_local[7]
        w_i, w_j = u_local[2], u_local[8]
        rz_i, rz_j = u_local[5], u_local[11]          # местный rz = +dv/dx (плоскость xy)
        ry_i, ry_j = u_local[4], u_local[10]           # местный ry = −dw/dx (плоскость xz)

        xi = s_mm / length if length > 0 else 0.0
        n1 = 1.0 - 3.0 * xi ** 2 + 2.0 * xi ** 3
        n2 = length * (xi - 2.0 * xi ** 2 + xi ** 3)
        n3 = 3.0 * xi ** 2 - 2.0 * xi ** 3
        n4 = length * (-xi ** 2 + xi ** 3)

        v_s = n1 * v_i + n2 * rz_i + n3 * v_j + n4 * rz_j              # dv/dx = +rz
        w_s = n1 * w_i + n2 * (-ry_i) + n3 * w_j + n4 * (-ry_j)        # dw/dx = −ry

        local_x, local_y, local_z = self.member_axes[member_id]
        return (
            v_s * local_y[0] + w_s * local_z[0],
            v_s * local_y[1] + w_s * local_z[1],
            v_s * local_y[2] + w_s * local_z[2],
        )

    def equilibrium_residual(self) -> dict:
        """
        Сумма всех приложенных нагрузок + реакций опор должна быть ~0 по
        силам и по моментам относительно глобального начала координат
        (см. докстринг модуля — обязательная проверка равновесия, не
        предположение). Возвращает остаток — по конструкции решателя он
        численно близок к нулю (машинная точность), большое отклонение
        означает ошибку в матрице/сборке, а не физику модели.
        """
        fx = fy = fz = mx = my = mz = 0.0
        for node in self.model.nodes:
            base = self.model._node_index[node.node_id] * DOF_PER_NODE
            total = [self.f_global[base + i] + self.reactions[base + i] for i in range(6)]
            fx += total[0]; fy += total[1]; fz += total[2]
            # Момент внешних сил относительно начала координат = приложенный момент
            # в узле + момент силы узла относительно начала координат (r×F).
            r = node.point.as_tuple()
            add = _cross(r, (total[0], total[1], total[2]))
            mx += total[3] + add[0]
            my += total[4] + add[1]
            mz += total[5] + add[2]
        return {"fx": fx, "fy": fy, "fz": fz, "mx": mx, "my": my, "mz": mz}

    def independent_free_body_check(self, reference_point: Point3D) -> dict:
        """
        Независимая проверка равновесия ВСЕЙ модели (продолжение,
        18.09.2026, п. «P0»: "добавь независимый тест всего свободного
        тела: сумма внешних нагрузок и реакций основания равна нулю по 3
        силам и 3 моментам относительно одного центра").

        Отличие от `equilibrium_residual()`: та функция суммирует сырые
        компоненты `f_global`/`reactions` этого же решателя ВНУТРИ этого
        же модуля — совпадающая внутренняя ошибка переноса момента (r×F)
        осталась бы незамеченной, потому что обе стороны проверки считали
        бы её одинаково. Здесь перенос каждой нагрузки/реакции в общую
        `reference_point` выполняется через `core.load_transfer.LoadVector.
        transferred_to()` — ОТДЕЛЬНО написанную и отдельно протестированную
        (см. tests/test_load_transfer.py) реализацию r×F в другом модуле.
        Расхождение между этой проверкой и `equilibrium_residual()` указывало
        бы на ошибку ровно в одной из двух независимых реализаций переноса.

        В сумму входят ТОЛЬКО внешние узловые нагрузки (`self.model.loads`)
        и реакции НА ОПОРАХ (`self.model.supports`) — внутренние усилия
        между узлами одной и той же модели (напр. `member_end_forces`)
        сюда намеренно не включаются (раздел задания: "внутренние реакции
        между подсистемами в эту сумму не включаются").
        """
        vectors = []
        for load in self.model.loads:
            node = self.model.node(load.node_id)
            vectors.append(LoadVector(
                node_ref=load.node_id, point=node.point,
                fx_n=load.fx_n, fy_n=load.fy_n, fz_n=load.fz_n,
                mx_nmm=load.mx_nmm, my_nmm=load.my_nmm, mz_nmm=load.mz_nmm,
                load_case=LoadCase.OPERATING,
                source="frame_model.independent_free_body_check#внешняя_нагрузка",
                label=f"внешняя_нагрузка_{load.node_id}",
            ))
        for support in self.model.supports:
            node = self.model.node(support.node_id)
            base = self.model._node_index[support.node_id] * DOF_PER_NODE
            r = self.reactions[base:base + 6]
            vectors.append(LoadVector(
                node_ref=support.node_id, point=node.point,
                fx_n=r[0], fy_n=r[1], fz_n=r[2], mx_nmm=r[3], my_nmm=r[4], mz_nmm=r[5],
                load_case=LoadCase.OPERATING,
                source="frame_model.independent_free_body_check#реакция_опоры",
                label=f"реакция_опоры_{support.node_id}",
            ))

        fx = fy = fz = mx = my = mz = 0.0
        for v in vectors:
            t = v.transferred_to(reference_point)
            fx += t.fx_n; fy += t.fy_n; fz += t.fz_n
            mx += t.mx_nmm; my += t.my_nmm; mz += t.mz_nmm
        return {"fx": fx, "fy": fy, "fz": fz, "mx": mx, "my": my, "mz": mz}
