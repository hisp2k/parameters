# -*- coding: utf-8 -*-
"""
Расчёт подшипников (Issue #3, продолжение — прочность TUBE-SAND-001,
раздел "Подшипники: радиальная/осевая нагрузка, статическая грузоподъёмность,
ресурс L10h, частота вращения и применимость к среде").

Реальные, проверяемые формулы каталожного расчёта подшипников качения —
СТАНДАРТНЫЕ (ISO 281 / общий курс "Детали машин"), НЕ подтверждённая
методика Тех-Аэро и не типоразмер конкретного подшипника: динамическая
грузоподъёмность C, статическая C0 и коэффициенты X/Y — ВСЕГДА входные
параметры из каталога конкретного поставщика/типоразмера, эта функция их
не выдумывает и не подставляет "типичное" значение.

Реакции опор (радиальная составляющая по двум плоскостям) — вход извне
(см. core/shaft_beam_model.py::solve_reactions, по одной плоскости на
вызов — результирующая нагрузка на опору есть векторная сумма реакций в
обеих плоскостях, см. `resultant_radial_load_n()`).

Ресурс L10h — единственный load case в этом репозитории, где критерий
"не менее" (см. core/verification.py::CRITERION_AT_LEAST) — деталь
разблокирована исправлением "устранить ограничение result<=limit".
"""

from __future__ import annotations

import math
from dataclasses import dataclass


class BearingCalculationError(ValueError):
    pass


def _require_positive(name: str, value) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise BearingCalculationError(f"{name}: ожидалось конечное число, получено {value!r}.")
    if value <= 0:
        raise BearingCalculationError(f"{name}: должно быть больше нуля, получено {value}.")


def _require_nonnegative(name: str, value) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise BearingCalculationError(f"{name}: ожидалось конечное число, получено {value!r}.")
    if value < 0:
        raise BearingCalculationError(f"{name}: не может быть отрицательным, получено {value}.")


def _require_finite_real(name: str, value) -> None:
    """
    Проверка сигнальной (знаковой) компоненты нагрузки — реакции опоры в
    отдельной плоскости МОГУТ быть отрицательными (знак = направление,
    см. core/shaft_beam_model.py), поэтому здесь нет требования
    неотрицательности, только "конечное вещественное число".

    Codex-замечание (продолжение, 18.09.2026, п.1): раньше эта проверка
    оборачивалась в `abs(value)` до вызова `_require_nonnegative`, что
    ломало саму проверку типа — `abs(True) == 1`, обычный `int`, поэтому
    булево значение тихо проходило как валидная нагрузка 1 Н, а строка
    падала с сырым `TypeError` из `abs()` вместо понятной ошибки. Здесь
    тип и конечность проверяются НА СЫРОМ значении, до любой арифметики.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise BearingCalculationError(f"{name}: ожидалось конечное число, получено {value!r}.")


def resultant_radial_load_n(load_vertical_n: float, load_horizontal_n: float) -> float:
    """Результирующая радиальная нагрузка — векторная сумма реакций в двух ортогональных плоскостях."""
    _require_finite_real("load_vertical_n", load_vertical_n)
    _require_finite_real("load_horizontal_n", load_horizontal_n)
    return math.hypot(load_vertical_n, load_horizontal_n)


@dataclass
class DynamicEquivalentLoad:
    equivalent_load_n: float
    x_factor: float
    y_factor: float
    inputs_used: dict


def dynamic_equivalent_load(
    radial_load_n: float, axial_load_n: float, x_factor: float, y_factor: float,
) -> DynamicEquivalentLoad:
    """
    P = X·Fr + Y·Fa — стандартная формула эквивалентной динамической
    нагрузки (ISO 281 / "Детали машин"). X, Y — коэффициенты КОНКРЕТНОГО
    типоразмера подшипника из каталога поставщика (зависят от отношения
    Fa/(C0) и угла контакта) — обязательный вход, не подставляется.
    """
    _require_nonnegative("radial_load_n", radial_load_n)
    _require_nonnegative("axial_load_n", axial_load_n)
    _require_nonnegative("x_factor", x_factor)
    _require_nonnegative("y_factor", y_factor)
    p = x_factor * radial_load_n + y_factor * axial_load_n
    return DynamicEquivalentLoad(
        equivalent_load_n=p, x_factor=x_factor, y_factor=y_factor,
        inputs_used={"radial_load_n": radial_load_n, "axial_load_n": axial_load_n,
                     "x_factor": x_factor, "y_factor": y_factor},
    )


#: Показатели степени ISO 281, п. "Rating life" — ЕДИНСТВЕННЫЕ поддерживаемые
#: этой методикой значения (шариковые/роликовые подшипники качения). Любое
#: другое положительное число НЕ является ошибкой арифметики — это признак
#: несоответствия каталогу/методике (независимая проверка, продолжение
#: 18.09.2026, п. «P1»: "тип подшипника/показатель привяжи к поддерживаемой
#: методике и каталогу, а не любому положительному p").
LIFE_EXPONENT_BALL = 3.0
LIFE_EXPONENT_ROLLER = 10.0 / 3.0
SUPPORTED_LIFE_EXPONENTS = (LIFE_EXPONENT_BALL, LIFE_EXPONENT_ROLLER)

#: Верхняя граница |log10(L10h)|, при превышении которой результат либо не
#: представим как конечное float-число (переполнение), либо физически
#: бессмысленно велик/мал для инженерной интерпретации (напр. 10^250 часов).
#: float имеет диапазон ~1e-308..1e308 (log10 ~ ±308) — берём с запасом.
_MAX_ABS_LOG10_L10H = 300.0


class BearingLifeOverflowError(BearingCalculationError):
    """
    Входные данные конечны и положительны, но результат L10h выходит за
    пределы представимого/осмысленного диапазона (переполнение степени
    (C/P)^p). Это КОНТРОЛИРУЕМАЯ ошибка расчёта — раньше в этом случае
    функция либо тихо возвращала `inf` (C=1e200, P=1e-200 → (C/P)^3 = inf),
    либо падала с сырым `OverflowError` из Python (C=1e120, P=1 →
    (C/P)^3 переполняет float **prior to** деления на срок в часах) —
    оба исхода скрывали факт, что сами входные C/P физически неправдоподобны
    (каталожная динамическая грузоподъёмность порядка 10^120 Н не существует),
    вместо явного сообщения об этом вызывающему коду.
    """


@dataclass
class L10LifeResult:
    l10_life_hours: float
    dynamic_capacity_n: float
    equivalent_load_n: float
    rotation_speed_rpm: float
    exponent: float


def l10_life_hours(
    dynamic_capacity_c_n: float, equivalent_load_p_n: float, rotation_speed_rpm: float,
    *, exponent: float,
) -> L10LifeResult:
    """
    L10h = (10⁶ / (60·n)) · (C/P)^p — стандартная формула номинального
    ресурса подшипника качения (ISO 281). p=3 для шариковых, p=10/3 для
    роликовых — ОБЯЗАТЕЛЬНЫЙ именованный аргумент без значения по
    умолчанию (Codex-замечание, продолжение 18.09.2026, п.1): раньше
    `exponent=3.0` был подставлен по умолчанию, то есть забытый явный
    выбор типа подшипника молча выдавал ЛЮБОЙ типоразмер за шариковый —
    именно то "не подставляется" не работало на практике, только в
    комментарии. Теперь тип (через показатель степени) обязан быть
    указан вызывающим кодом на каждом вызове, иначе — TypeError на этапе
    вызова, а не тихая подмена типа подшипника.

    Независимая проверка (продолжение, 18.09.2026, п. «P1»): два отдельных
    исправления —
    1. `exponent` теперь обязан совпадать с одним из `SUPPORTED_LIFE_
       EXPONENTS` (ISO 281: 3.0 — шариковые, 10/3 — роликовые). Любое
       другое положительное число раньше проходило без вопросов — это
       позволяло случайно посчитать ресурс по показателю степени, не
       соответствующему НИКАКОМУ реальному типу подшипника из каталога.
    2. Степень (C/P)^p считается В ЛОГАРИФМИЧЕСКОМ пространстве
       (log10), поэтому переполнение float ловится ДО того, как Python
       либо тихо вернёт `inf`, либо бросит сырой `OverflowError` из
       оператора `**` — вызывающий код получает понятную
       `BearingLifeOverflowError` с указанием, какие именно входы дают
       нефизичный результат.

    Независимая проверка коммита c24d42b (продолжение, 18.09.2026, раздел
    3): п.2 выше был реализован НЕПОЛНОСТЬЮ — предфактор считался как
    `math.log10(1.0e6 / (60.0 * rotation_speed_rpm))`, то есть
    произведение `60·n` СНАЧАЛА вычислялось как обычное float-умножение
    и МОГЛО САМО переполниться (repro: `rotation_speed_rpm=1e308` конечно
    и положительно, но `60*1e308` уже `inf` → `1e6/inf=0.0` →
    `math.log10(0.0)` бросает сырой `ValueError: math domain error`,
    А НЕ `BearingLifeOverflowError`, хотя вход прошёл все проверки
    `_require_positive`). Логарифмирование самого предфактора обязано
    происходить БЕЗ промежуточного произведения — `log10(1e6/(60n)) =
    6 − log10(60) − log10(n)` — тогда переполниться нечему: `n>0` конечно
    ⇒ `log10(n)` всегда конечно, само взятие логарифма никогда не требует
    вычислять `60·n` как единое число.
    """
    _require_positive("dynamic_capacity_c_n", dynamic_capacity_c_n)
    _require_positive("equivalent_load_p_n", equivalent_load_p_n)
    _require_positive("rotation_speed_rpm", rotation_speed_rpm)
    _require_positive("exponent", exponent)
    if not any(math.isclose(exponent, allowed, rel_tol=1e-9) for allowed in SUPPORTED_LIFE_EXPONENTS):
        raise BearingCalculationError(
            f"exponent={exponent!r} не входит в поддерживаемую методику ISO 281 "
            f"(p={LIFE_EXPONENT_BALL} — шариковые подшипники, "
            f"p={LIFE_EXPONENT_ROLLER:.6f} — роликовые подшипники). Другой "
            "показатель степени — признак несоответствия типу подшипника/"
            "каталогу, а не допустимая численная настройка."
        )

    # Считаем log10(L10h) = log10(1e6/(60n)) + p·(log10(C) − log10(P)),
    # чтобы обнаружить переполнение ДО возведения в степень (см. докстринг).
    # log10(1e6/(60n)) = 6 − log10(60) − log10(n) — БЕЗ промежуточного
    # произведения `60*n` (независимая проверка c24d42b, раздел 3: именно
    # это произведение переполнялось раньше для очень больших n).
    log_prefactor = 6.0 - math.log10(60.0) - math.log10(rotation_speed_rpm)
    log_ratio = math.log10(dynamic_capacity_c_n) - math.log10(equivalent_load_p_n)
    log_l10h = log_prefactor + exponent * log_ratio
    if not math.isfinite(log_l10h) or abs(log_l10h) > _MAX_ABS_LOG10_L10H:
        raise BearingLifeOverflowError(
            f"Ресурс L10h при dynamic_capacity_c_n={dynamic_capacity_c_n!r}, "
            f"equivalent_load_p_n={equivalent_load_p_n!r}, exponent={exponent!r} "
            f"выходит за пределы представимого диапазона (log10(L10h)≈{log_l10h!r}). "
            "Проверьте порядок величины входных данных C/P — вероятна ошибка единиц "
            "измерения или подстановка нефизичного каталожного значения."
        )
    l10h = 10.0 ** log_l10h
    return L10LifeResult(
        l10_life_hours=l10h, dynamic_capacity_n=dynamic_capacity_c_n,
        equivalent_load_n=equivalent_load_p_n, rotation_speed_rpm=rotation_speed_rpm, exponent=exponent,
    )


@dataclass
class StaticCapacityCheck:
    static_safety_factor: float
    static_capacity_n: float
    static_equivalent_load_n: float


def static_capacity_safety_factor(
    static_capacity_c0_n: float, static_equivalent_load_p0_n: float,
) -> StaticCapacityCheck:
    """
    s0 = C0/P0 — коэффициент запаса по статической грузоподъёмности.
    Минимально требуемое s0 (типично 1.0-2.0 в зависимости от режима/
    требований к плавности хода) — КАТАЛОЖНОЕ/нормативное значение,
    передаётся вызывающим кодом как отдельный criterion_limit при сборке
    VerificationRecord, здесь не подставляется никакое "типичное" число.
    """
    _require_positive("static_capacity_c0_n", static_capacity_c0_n)
    _require_positive("static_equivalent_load_p0_n", static_equivalent_load_p0_n)
    return StaticCapacityCheck(
        static_safety_factor=static_capacity_c0_n / static_equivalent_load_p0_n,
        static_capacity_n=static_capacity_c0_n, static_equivalent_load_n=static_equivalent_load_p0_n,
    )


# ---------------------------------------------------------------------------
# Источники: ISO 281 (Rolling bearings — Dynamic load ratings and rating
# life); общий курс "Детали машин" (расчёт подшипников качения на
# статическую/динамическую грузоподъёмность). X/Y/C/C0 — каталожные
# величины конкретного изготовителя/типоразмера, НЕ нормативный акт.
# ---------------------------------------------------------------------------
