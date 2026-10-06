# -*- coding: utf-8 -*-
"""
Обобщённый объект передачи нагрузки узел→корпус→рама→основание (раздел 2
доп. задания «Продолжи цепочку вал→подшипники→корпус→рама→основание»).

НАЗНАЧЕНИЕ. Реакции опор вала (см. core/shaft_beam_model.py) и другие
сосредоточенные воздействия (масса привода, реакция муфты, вес самого
корпуса) должны попадать в модель корпуса и рамы БЕЗ ПОТЕРИ точки
приложения и БЕЗ ДВОЙНОГО СЧЁТА одной и той же нагрузки в двух режимах
одновременно. Раньше в репозитории такого объекта не было — реакции вала
существовали только как числа Reactions.support_a_n/support_b_n без
привязки к 3D-координатам, режиму нагружения и источнику.

СИСТЕМА КООРДИНАТ. Правая (X,Y,Z), миллиметры; силы — Н, моменты — Н·мм.
Ось Z принята "вертикальной вверх" по умолчанию инженерной практики этого
репозитория, но сам класс не навязывает физический смысл осей — это
исключительно соглашение вызывающего кода (см. FrameNode в frame_model.py).

ПЕРЕДАЧА МОМЕНТА ПРИ ПЕРЕНОСЕ ТОЧКИ ПРИЛОЖЕНИЯ. Жёсткое (недеформируемое)
перемещение силы F с моментом M, приложенных в точке A, в эквивалентную
систему в точке B:
    F_B = F_A                              (сила не меняется)
    M_B = M_A + r_A/B × F_A,   r_A/B = A − B  (вектор ОТ B К A)
Это стандартная статика приведения системы сил к другому центру
(см. любой курс теоретической механики, "Приведение системы сил к
центру"). Знак перепутать легко — модуль проверяет это в тестах на
известном примере (чистая сила без момента, перенесённая на плечо r,
должна дать M_B = r × F, а не −r × F).

РЕЖИМЫ НАГРУЖЕНИЯ (LoadCase) — раздел задания: "раздели случаи нагрузки:
свой вес, рабочий режим, пуск, расчётное заполнение, подтверждённая
перегрузка/заклинивание, транспортировка". Случаи ПРИНЦИПИАЛЬНО не
складываются друг с другом автоматически — LoadCaseSet.resultant_at()
требует явно назвать, какие случаи суммируются в конкретном расчёте,
именно чтобы не допустить незаметного двойного счёта (напр. случайного
сложения "рабочий режим" и "пуск", которые физически не действуют
одновременно на одном и том же объекте).

НЕЗАВИСИМАЯ ПРОВЕРКА (продолжение, 18.09.2026, п. «P1»). Три отдельных
дефекта, найденных независимой проверкой коммита 377e33c, исправлены здесь:

1. ОТСУТСТВИЕ ДАННЫХ ≠ ПОДТВЕРЖДЁННЫЙ НОЛЬ. Раньше `resultant_at(cases=
   [STARTUP])` при отсутствии в наборе НИ ОДНОЙ нагрузки с `load_case=
   STARTUP` молча возвращал `ResultantLoad(fx_n=0, ...)` — числовой ноль,
   неотличимый от "режим пуска физически даёт нулевую нагрузку в этой
   точке, это проверено и подтверждено". Теперь запрошенный, но
   ОТСУТСТВУЮЩИЙ в наборе режим — это `LoadTransferError` (контролируемая
   ошибка "нет данных"), а не тихий физический ноль. Явно подтверждённый
   ноль по-прежнему представим — добавьте `LoadVector` с нулевыми
   компонентами и понятным `source`/`label` ("подтверждено: пуск не
   нагружает эту опору") — тогда `contributing_count>=1` и результат 0.0
   означает ПОДТВЕРЖДЕНИЕ, а не молчание.
2. РАЗНЫЕ ревизии/снимки входных данных. Суммирование нагрузок с РАЗНЫМИ
   заявленными `product_revision`/`input_fingerprint` физически означает
   смешивание чисел, посчитанных для разных состояний изделия/анкеты —
   `resultant_at()` теперь это обнаруживает и отклоняет (сравниваются
   только явно заданные, непустые значения — нагрузки без этой метаданной
   не блокируют друг друга, иначе большинство существующих синтетических
   тестов, не проставляющих ревизию, ложно ломались бы).
3. ЗАЩИТА ОТ ДУБЛЕЙ работает НЕЗАВИСИМО от того, как создан набор:
   `LoadCaseSet(loads=[...])` теперь тоже идёт через `add()` (раньше
   обходил дедупликацию, `_seen_keys` оставался пустым), `loads` — только
   для чтения (нельзя дописать в обход `add()` через `s.loads.append(...)`),
   и смена `label` при ЧИСЛЕННО идентичном ненулевом векторе силы/момента
   в той же (node_ref, load_case, source) тоже отклоняется — иначе защита
   по ключу тривиально обходится косметическим изменением одной строки.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional


class LoadTransferError(ValueError):
    pass


def _finite(name: str, value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LoadTransferError(f"{name}: ожидалось число, получено {type(value).__name__} ({value!r}).")
    if not math.isfinite(value):
        raise LoadTransferError(f"{name}: значение должно быть конечным числом, получено {value!r}.")
    return float(value)


class LoadCase(str, Enum):
    """Раздел задания, п.2 — случаи нагрузки, которые нельзя молча смешивать."""

    SELF_WEIGHT = "собственный_вес"
    OPERATING = "рабочий_режим"
    STARTUP = "пуск"
    DESIGN_FILL = "расчётное_заполнение"
    CONFIRMED_OVERLOAD_JAM = "подтверждённая_перегрузка_заклинивание"
    TRANSPORT = "транспортировка"


@dataclass(frozen=True)
class Point3D:
    x_mm: float
    y_mm: float
    z_mm: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x_mm", _finite("x_mm", self.x_mm))
        object.__setattr__(self, "y_mm", _finite("y_mm", self.y_mm))
        object.__setattr__(self, "z_mm", _finite("z_mm", self.z_mm))

    def __sub__(self, other: "Point3D") -> tuple[float, float, float]:
        return (self.x_mm - other.x_mm, self.y_mm - other.y_mm, self.z_mm - other.z_mm)

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x_mm, self.y_mm, self.z_mm)


def _cross(r: tuple[float, float, float], f: tuple[float, float, float]) -> tuple[float, float, float]:
    rx, ry, rz = r
    fx, fy, fz = f
    return (ry * fz - rz * fy, rz * fx - rx * fz, rx * fy - ry * fx)


@dataclass(frozen=True)
class LoadVector:
    """
    Одна нагрузка в одной точке для ОДНОГО режима нагружения. `node_ref` —
    идентификатор узла/позиции BOM, к которой относится нагрузка (не
    произвольная строка "куда-то" — должен быть трассируемым, напр. имя
    опоры вала или обозначение позиции BOM корпуса). `fingerprint`/
    `product_revision` — та же дисциплина, что и в VerificationRecord
    (core/verification.py): нагрузка, посчитанная для устаревших входных
    данных, не должна выглядеть действительной молча.

    НЕИЗМЕНЯЕМ (`frozen=True`, независимая проверка коммита c24d42b,
    раздел 2) — раньше `LoadCaseSet.loads` отдавал `tuple` из ОБЫЧНЫХ
    (изменяемых) `LoadVector`: `s.loads[0].fz_n = -999` мутировал уже
    принятую в набор нагрузку НА МЕСТЕ, без пересчёта её fingerprint_key,
    без повторной проверки дублей/ревизии и без какого-либо следа в
    расчёте — набор продолжал считать себя тем же, что был принят. Теперь
    `LoadVector` — неизменяемый расчётный снимок: изменить нагрузку задним
    числом физически нельзя, можно только построить НОВЫЙ `LoadVector`
    (что естественно меняет её fingerprint/происхождение).
    """

    node_ref: str
    point: Point3D
    fx_n: float
    fy_n: float
    fz_n: float
    mx_nmm: float
    my_nmm: float
    mz_nmm: float
    load_case: LoadCase
    source: str                       # откуда взята нагрузка (напр. "shaft_beam_model.solve_reactions#support_a")
    label: str = ""
    product_revision: str = ""
    input_fingerprint: str = ""

    def __post_init__(self) -> None:
        for name in ("fx_n", "fy_n", "fz_n", "mx_nmm", "my_nmm", "mz_nmm"):
            object.__setattr__(self, name, _finite(name, getattr(self, name)))
        if not isinstance(self.load_case, LoadCase):
            raise LoadTransferError(f"load_case должен быть значением LoadCase, получено {self.load_case!r}.")
        if not self.source:
            raise LoadTransferError("source обязателен — нагрузка без источника не трассируема.")
        if not self.node_ref:
            raise LoadTransferError("node_ref обязателен — нагрузка должна быть привязана к узлу/позиции BOM.")

    @property
    def force(self) -> tuple[float, float, float]:
        return (self.fx_n, self.fy_n, self.fz_n)

    @property
    def moment(self) -> tuple[float, float, float]:
        return (self.mx_nmm, self.my_nmm, self.mz_nmm)

    def fingerprint_key(self) -> str:
        """
        Ключ для обнаружения дублей/двойного счёта — та же (node_ref,
        load_case, source, label) нагрузка, добавленная в набор дважды,
        почти всегда ошибка вызывающего кода, а не два разных воздействия.
        """
        raw = "|".join([self.node_ref, self.load_case.value, self.source, self.label])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def transferred_to(self, new_point: Point3D, *, new_node_ref: Optional[str] = None) -> "LoadVector":
        """
        Жёсткий перенос точки приложения (см. докстринг модуля):
        F не меняется, M_new = M_old + r×F, r = точка_старая − точка_новая.
        """
        r = self.point - new_point
        add_mx, add_my, add_mz = _cross(r, self.force)
        return LoadVector(
            node_ref=new_node_ref if new_node_ref is not None else self.node_ref,
            point=new_point,
            fx_n=self.fx_n, fy_n=self.fy_n, fz_n=self.fz_n,
            mx_nmm=self.mx_nmm + add_mx, my_nmm=self.my_nmm + add_my, mz_nmm=self.mz_nmm + add_mz,
            load_case=self.load_case, source=self.source, label=self.label,
            product_revision=self.product_revision, input_fingerprint=self.input_fingerprint,
        )

    def to_dict(self) -> dict:
        return {
            "node_ref": self.node_ref,
            "point_mm": list(self.point.as_tuple()),
            "fx_n": self.fx_n, "fy_n": self.fy_n, "fz_n": self.fz_n,
            "mx_nmm": self.mx_nmm, "my_nmm": self.my_nmm, "mz_nmm": self.mz_nmm,
            "load_case": self.load_case.value,
            "source": self.source, "label": self.label,
            "product_revision": self.product_revision, "input_fingerprint": self.input_fingerprint,
        }


@dataclass(frozen=True)
class ResultantLoad:
    """
    Итог суммирования НЕСКОЛЬКИХ LoadVector, перенесённых в одну точку.
    Отдельный тип от LoadVector специально: LoadVector.load_case — ровно
    ОДИН режим (иначе бессмысленно применять criterion к смешанному
    случаю); результат суммирования нескольких случаев — это уже не
    "один режим", поэтому здесь `load_cases` — список, и результат нельзя
    случайно передать туда, где ожидается нагрузка одного режима.

    `product_revision`/`input_fingerprint` (продолжение, 18.09.2026, п.
    «P1»): раньше терялись при суммировании — результат было невозможно
    трассировать назад к ревизии/снимку входных данных, из которых он
    получен. Теперь `resultant_at()` заполняет их ЕДИНЫМ значением (после
    проверки на согласованность вкладов, см. её докстринг) — пусто, если
    ни один из суммированных LoadVector его не указал.
    """

    point: Point3D
    fx_n: float
    fy_n: float
    fz_n: float
    mx_nmm: float
    my_nmm: float
    mz_nmm: float
    load_cases: tuple  # tuple[LoadCase, ...] — какие режимы просуммированы
    contributing_count: int
    note: str = ""
    product_revision: str = ""
    input_fingerprint: str = ""

    @property
    def force(self) -> tuple[float, float, float]:
        return (self.fx_n, self.fy_n, self.fz_n)

    @property
    def moment(self) -> tuple[float, float, float]:
        return (self.mx_nmm, self.my_nmm, self.mz_nmm)


class LoadCaseSet:
    """
    Набор нагрузок, СГРУППИРОВАННЫХ по режиму — сложение между режимами
    только по явному запросу вызывающего кода (`resultant_at(cases=[...])`),
    никогда неявно по умолчанию (раздел задания: "не допускай двойного
    счёта веса"). Дубли (одинаковый fingerprint_key) отклоняются при
    добавлении — иначе одна и та же нагрузка, добавленная дважды по
    ошибке, тихо удвоила бы результат.

    НЕ dataclass — намеренно (продолжение, 18.09.2026, п. «P1»): раньше
    `loads` был обычным публичным полем dataclass, и конструктор
    `LoadCaseSet(loads=[load, load])` записывал список НАПРЯМУЮ, минуя
    `add()` — дедупликация (`_seen_keys`) оставалась пустой, дубль тихо
    проходил. Теперь `loads` — то, что попадает в набор ТОЛЬКО через
    `add()` (включая начальный список конструктора), а свойство `loads`
    отдаёт неизменяемый `tuple` — `s.loads.append(...)` (прямое
    редактирование списка в обход `add()`) больше не работает физически:
    `tuple` не имеет `.append`.
    """

    def __init__(self, loads: Optional[Iterable[LoadVector]] = None) -> None:
        self._loads: list[LoadVector] = []
        self._seen_keys: set = set()
        for load in (loads or []):
            self.add(load)

    def __repr__(self) -> str:
        return f"LoadCaseSet(loads={self._loads!r})"

    @property
    def loads(self) -> tuple:
        return tuple(self._loads)

    def add(self, load: LoadVector) -> None:
        key = load.fingerprint_key()
        if key in self._seen_keys:
            raise LoadTransferError(
                f"Нагрузка с ключом (node_ref={load.node_ref!r}, load_case={load.load_case.value!r}, "
                f"source={load.source!r}, label={load.label!r}) уже добавлена в набор — "
                "повторное добавление похоже на двойной счёт, а не на новую нагрузку "
                "(если это ДЕЙСТВИТЕЛЬНО другая нагрузка, дайте ей другой label)."
            )
        # Доп. защита (продолжение, 18.09.2026, п. «P1»): смена ТОЛЬКО label
        # при том же (node_ref, load_case, source) и ЧИСЛЕННО идентичном
        # НЕНУЛЕВОМ векторе силы/момента — это ровно тот случай, когда
        # ключ дедупликации выше (он включает label) тривиально обходится
        # косметическим переименованием одной и той же физической нагрузки.
        # Нулевой вектор ИСКЛЮЧЁН из этой проверки: несколько явных
        # "подтверждённых нулей" под разными метками (напр. для разных
        # режимов проверки) — законный, а не подозрительный случай.
        if any(load.force) or any(load.moment):
            for existing in self._loads:
                if (existing.node_ref == load.node_ref and existing.load_case == load.load_case
                        and existing.source == load.source and existing.label != load.label
                        and existing.point == load.point
                        and existing.force == load.force and existing.moment == load.moment):
                    raise LoadTransferError(
                        f"Нагрузка (node_ref={load.node_ref!r}, load_case={load.load_case.value!r}, "
                        f"source={load.source!r}) с ЧИСЛЕННО идентичным вектором силы/момента уже "
                        f"добавлена под другой меткой ({existing.label!r} vs {load.label!r}) — смена "
                        "label не делает это новой физической нагрузкой; если это ДЕЙСТВИТЕЛЬНО "
                        "отдельное совпадающее по числам воздействие, используйте другой source."
                    )
        self._seen_keys.add(key)
        self._loads.append(load)

    def by_case(self, load_case: LoadCase) -> list[LoadVector]:
        return [ld for ld in self._loads if ld.load_case == load_case]

    def cases_present(self) -> set:
        return {ld.load_case for ld in self._loads}

    def resultant_at(
        self, point: Point3D, cases: Iterable[LoadCase], *, allow_missing_cases: Iterable[LoadCase] = (),
    ) -> ResultantLoad:
        """
        Суммарная нагрузка (сила+момент) от ВЫБРАННЫХ явно случаев,
        перенесённая в одну общую точку `point`. `cases` обязателен и
        не имеет значения по умолчанию "все" — вызывающий код обязан
        сознательно перечислить, какие режимы физически действуют
        одновременно в этом расчёте.

        `allow_missing_cases` (продолжение, 18.09.2026, п. «P1»): по
        умолчанию ПУСТ — запрошенный режим, для которого в наборе нет НИ
        ОДНОЙ нагрузки, — это отсутствие данных, и метод бросает
        `LoadTransferError`, а не тихо возвращает численный ноль (см.
        докстринг модуля, пункт 1). Если для конкретного расчёта
        отсутствие режима физически ожидаемо и ОСОЗНАННО (не забывчивость),
        перечислите такие режимы явно в `allow_missing_cases` — тогда их
        отсутствие не считается ошибкой и вклад остаётся нулевым.
        """
        cases = list(cases)
        if not cases:
            raise LoadTransferError(
                "cases не может быть пустым — явно укажите, какие режимы нагружения суммируются "
                "(раздел задания: не смешивать случаи нагрузки неявно)."
            )
        for c in cases:
            if not isinstance(c, LoadCase):
                raise LoadTransferError(f"Неизвестный режим нагружения: {c!r}.")
        allow_missing = set(allow_missing_cases)
        present = self.cases_present()
        missing = [c for c in cases if c not in present and c not in allow_missing]
        if missing:
            missing_labels = ", ".join(sorted(c.value for c in missing))
            raise LoadTransferError(
                f"Запрошены режимы нагружения без единой нагрузки в наборе: {missing_labels}. "
                "Это ОТСУТСТВИЕ ДАННЫХ, а не подтверждённый физический ноль — молчаливо "
                "считать такой режим нулевым запрещено (независимая проверка, продолжение "
                "18.09.2026, п. «P1»). Если ноль для этого режима ДЕЙСТВИТЕЛЬНО подтверждён, "
                "добавьте LoadVector с нулевыми компонентами и source, объясняющим происхождение "
                "нуля; если отсутствие режима здесь ожидаемо и осознанно, передайте его в "
                "allow_missing_cases."
            )
        selected = [ld for ld in self._loads if ld.load_case in cases]

        # Согласованность ревизии/снимка входных данных (продолжение,
        # 18.09.2026, п. «P1», пункт 2): сравниваются только ЯВНО заданные
        # (непустые) значения — нагрузка, не проставившая ревизию/
        # fingerprint, не блокирует суммирование (иначе большинство
        # синтетических/исследовательских расчётов, не отслеживающих
        # ревизию, ложно ломались бы), но ДВЕ РАЗНЫЕ явно заданные ревизии/
        # снимка среди суммируемых нагрузок — почти всегда смешивание
        # чисел, посчитанных для разных состояний изделия/анкеты.
        revisions = {ld.product_revision for ld in selected if ld.product_revision}
        if len(revisions) > 1:
            raise LoadTransferError(
                f"Нельзя суммировать нагрузки с разными product_revision: {sorted(revisions)} — "
                "это разные состояния изделия; пересчитайте нагрузки под единую ревизию перед "
                "суммированием (независимая проверка, продолжение 18.09.2026, п. «P1»)."
            )
        fingerprints = {ld.input_fingerprint for ld in selected if ld.input_fingerprint}
        if len(fingerprints) > 1:
            raise LoadTransferError(
                f"Нельзя суммировать нагрузки с разными input_fingerprint: {sorted(fingerprints)} — "
                "нагрузки посчитаны для разных снимков входных данных анкеты/проекта "
                "(независимая проверка, продолжение 18.09.2026, п. «P1»)."
            )

        fx = fy = fz = mx = my = mz = 0.0
        for ld in selected:
            transferred = ld.transferred_to(point)
            fx += transferred.fx_n
            fy += transferred.fy_n
            fz += transferred.fz_n
            mx += transferred.mx_nmm
            my += transferred.my_nmm
            mz += transferred.mz_nmm
        case_labels = "+".join(sorted(c.value for c in set(cases)))
        return ResultantLoad(
            point=point, fx_n=fx, fy_n=fy, fz_n=fz, mx_nmm=mx, my_nmm=my, mz_nmm=mz,
            load_cases=tuple(sorted(set(cases), key=lambda c: c.value)),
            contributing_count=len(selected),
            note=f"сумма {len(selected)} нагрузок из набора, режимы: {case_labels}",
            product_revision=next(iter(revisions), ""),
            input_fingerprint=next(iter(fingerprints), ""),
        )


# ---------------------------------------------------------------------------
# Источники: любой курс теоретической механики, раздел "Приведение системы
# сил к заданному центру" (сила + пара сил, теорема о переносе силы).
# ---------------------------------------------------------------------------
