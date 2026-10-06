"""
Калькулятор ленточных и роликовых транспортеров — промышленная итерация v2
Python 3.10+ / Streamlit

Назначение
----------
Предварительный инженерный и коммерческий расчет:
- ленточного конвейера;
- неприводного/приводного роликового конвейера (рольганга);
- трудоемкости и ориентировочной стоимости сборки/монтажа.

Нормативная/методическая база, заложенная в логику
--------------------------------------------------
1. ГОСТ 22644-77 — стандартные ряды ширины ленты и скорости.
2. ГОСТ 20-2018 — резинотканевые конвейерные ленты; результат Tmax и
   удельного рабочего натяжения предназначен для последующего выбора ленты.
3. ISO 5048:1989 — предварительный расчет сопротивлений движению,
   тягового усилия и мощности ленточного конвейера.
4. СП 37.13330.2012 — угол наклона должен проверяться по конкретному грузу.
5. ГОСТ 12.2.022-80 — общие требования безопасности к конвейерам.
6. Размерные ряды роликового конвейера в данном прототипе основаны на
   исторической отраслевой базе ГОСТ 8324-82. Статус этого документа должен
   быть подтвержден в применяемой на предприятии нормативной базе перед
   выпуском КД/РЭ. Таблица используется как справочный ряд, а не как
   утверждение о текущем статусе стандарта.

ВАЖНО
-----
Это расчет уровня технико-коммерческого предложения / предварительного
проектирования. Для выпуска КД необходимы уточненный расчет трассы,
динамики пуска/торможения, барабанов, валов, подшипников, роликоопор,
ленты, металлоконструкции, ограждений, электропривода и безопасности.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple



# =============================================================================
# 1. НОРМАТИВНЫЕ И СПРАВОЧНЫЕ ДАННЫЕ
# =============================================================================

G = 9.81  # м/с²

# ГОСТ 22644-77. Значения в скобках в стандарте считаются нерекомендуемыми;
# в базовом автоматическом подборе они исключены, но 300 мм сохранено.
BELT_WIDTHS_MM = [300, 400, 500, 650, 800, 1000, 1200, 1400, 1600, 1800, 2000, 2250, 2500, 2750, 3000]
BELT_SPEEDS_MPS = [0.25, 0.315, 0.4, 0.5, 0.63, 0.8, 1.0, 1.25, 1.6, 2.0, 2.5, 3.15, 4.0, 5.0, 6.3, 8.0, 10.0]


# ГОСТ 22644-77: номинальный ряд диаметров приводных и неприводных
# нефутерованных барабанов. Конкретный диаметр из этого ряда определяется
# уже расчетной методикой изгиба выбранной ленты, а не самим ГОСТ 22644-77.
DRUM_DIAMETERS_MM = [160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1400, 1600, 2000, 2500]

# ГОСТ 22644-77, табл. 1: длина обечайки барабана для стационарного конвейера.
DRUM_SHELL_LENGTH_MM = {
    300: 400, 400: 500, 500: 600, 650: 750, 800: 950,
    1000: 1150, 1200: 1400, 1400: 1600, 1600: 1800,
    1800: 2000, 2000: 2200, 2250: 2550, 2500: 2800,
    2750: 3050, 3000: 3300,
}

# ГОСТ 22644-77 / ГОСТ 22646-77: номинальные диаметры роликов ленточных
# конвейеров. В автоматическом подборе ниже используется только часть ряда.
BELT_IDLER_DIAMETERS_MM = [63, 76, 89, 102, 108, 127, 133, 152, 159, 168, 178, 194, 219, 245]

# ГОСТ 20-2018, табл. 4 / приложение Б: номинальная прочность одной
# тяговой прокладки по основе. Значение используется для предварительной
# проверки требуемого каркаса. Оно НЕ заменяет проверку полной конструкции
# ленты, стыка и требований конкретного изготовителя.
BELT_FABRICS_N_MM = {
    "БКНЛ-65-2": 55,
    "ТК-100": 100,
    "ТК-200-2": 200,
    "ТЛК-200": 200,
    "ЕР-200": 200,
    "ТЛК-250": 250,
    "ЕР-250": 250,
    "ТК-300-2": 300,
    "ТЛК-300-2": 300,
    "ЕР-315": 315,
    "ТЛК-315": 315,
    "ТК-400": 400,
    "ТЛК-400-2": 400,
    "ЕР-400": 400,
    "ЕР-450": 450,
    "ТЛК-500": 500,
    "ЕР-500": 500,
    "ЕР-630": 630,
}

BELT_SERVICE_TYPES = {
    "Легкие": "3",
    "Средние": "2.2",
    "Тяжелые": "1.2",
    "Очень тяжелые": "1.1",
}

# Инженерный классификатор для автоматического ограничения скорости.
# Это корпоративная расчетная логика, а не таблица ГОСТ.
ABRASIVENESS_SPEED_CAP = {
    "Низкая": 3.15,
    "Средняя": 2.5,
    "Высокая": 1.6,
}
DUSTINESS_SPEED_CAP = {
    "Низкая": 4.0,
    "Средняя": 2.0,
    "Высокая": 1.25,
}

STANDARD_GEAR_RATIOS = [5, 6.3, 8, 10, 12.5, 16, 20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160]

# Предварительный каталог продольных балок рамы из прямоугольной трубы.
# Это НЕ нормативный ассортимент предприятия и может быть заменен на каталог
# фактически закупаемого металлопроката.
FRAME_RHS_CATALOG = [
    (60, 40, 3), (80, 40, 3), (80, 60, 4), (100, 50, 4),
    (100, 60, 4), (120, 60, 4), (140, 80, 5), (160, 80, 5),
    (180, 100, 6), (200, 100, 6),
]
STEEL_GRADES = {
    "Ст3 / S235 (предварительно)": 235.0,
    "09Г2С (предварительно)": 345.0,
}

# Стандартный ряд мощностей электродвигателей для предварительного выбора.
# Это НЕ таблица конкретного ГОСТ конвейеров; ряд нужен только для округления
# расчетной мощности вверх до типоразмера привода.
MOTOR_POWER_KW = [
    0.12, 0.18, 0.25, 0.37, 0.55, 0.75, 1.1, 1.5, 2.2, 3.0, 4.0, 5.5,
    7.5, 11.0, 15.0, 18.5, 22.0, 30.0, 37.0, 45.0, 55.0, 75.0, 90.0,
    110.0, 132.0, 160.0, 200.0, 250.0, 315.0
]

# Коэффициенты производительности C для желобчатой ленты.
# Используются в зависимости B = 1.1 * (sqrt(Q / (C*v*rho)) + 0.05).
# Таблица применяется как инженерная методика проектирования ленточных
# конвейеров; она НЕ является самостоятельным рядом ГОСТ 22644-77.
# Ключ 1: угол желобчатости боковых роликов, град.
# Ключ 2: угол естественного откоса груза, град.
# Значение: коэффициенты для диапазонов наклона 0–10 / 11–15 / 16–18 / 19–22°.
CAPACITY_COEFFICIENTS: Dict[int, Dict[int, List[float]]] = {
    20: {
        30: [257, 245, 232, 225],
        35: [277, 262, 250, 240],
        40: [294, 279, 264, 250],
        45: [313, 295, 280, 265],
    },
    30: {
        30: [296, 282, 267, 259],
        35: [319, 302, 288, 276],
        40: [338, 320, 304, 288],
        45: [358, 340, 322, 305],
    },
}

# Коэффициент C_secondary (обобщение вторичных сопротивлений) по длине
# для предварительной схемы ISO 5048. Интерполируем линейно.
LENGTH_FACTOR_TABLE = [
    (3, 9.00), (4, 7.60), (6, 5.90), (10, 4.50), (16, 3.60),
    (20, 3.20), (25, 2.90), (32, 2.60), (40, 2.40), (50, 2.20),
    (63, 2.00), (80, 1.92), (90, 1.86), (100, 1.78), (120, 1.70),
    (140, 1.63), (160, 1.56), (180, 1.50), (200, 1.45), (250, 1.38),
    (300, 1.31), (350, 1.27), (400, 1.25), (450, 1.22), (500, 1.20),
    (550, 1.18), (600, 1.17), (700, 1.14), (800, 1.12), (900, 1.10),
    (1000, 1.09), (1500, 1.06), (2000, 1.05), (2500, 1.04), (5000, 1.03),
]

# Справочный размерный ряд роликового конвейера (историческая отрасл. база).
ROLLER_LENGTHS_MM = [160, 200, 250, 320, 400, 500, 650, 800, 1000, 1200]
ROLLER_PITCHES_MM = [50, 60, 80, 100, 125, 200, 250, 315, 400, 500, 630]
ROLLER_DIAMETERS_MM = [42, 60, 76, 108, 159]

# Предварительная допустимая статическая нагрузка на один ролик, Н,
# в зависимости от диаметра и стандартной длины ролика.
# None = комбинация не используется в таблице/требует специальной проверки.
ROLLER_CAPACITY_N: Dict[int, Dict[int, Optional[float]]] = {
    42: {
        160: 980, 200: 930, 250: 980, 320: 980, 400: 980,
        500: 784, 650: 588, 800: None, 1000: None, 1200: None,
    },
    60: {
        160: None, 200: 2940, 250: 2940, 320: 1960, 400: 1960,
        500: 1568, 650: 980, 800: 980, 1000: None, 1200: None,
    },
    76: {
        160: None, 200: 4900, 250: 4900, 320: 4900, 400: 4900,
        500: 4900, 650: 3920, 800: 3920, 1000: 2940, 1200: None,
    },
    108: {
        160: None, 200: None, 250: None, 320: 9800, 400: 9800,
        500: 9800, 650: 9800, 800: 9800, 1000: 7840, 1200: 7840,
    },
    159: {
        160: None, 200: None, 250: None, 320: 19600, 400: 19600,
        500: 19600, 650: 19600, 800: 19600, 1000: 19600, 1200: 15680,
    },
}

# Для оценки массы вращающейся части ролика принимается стальная обечайка.
# Толщина — инженерное допущение прототипа, редактируемое через override массы.
ROLLER_WALL_MM = {42: 2.0, 60: 2.5, 76: 3.0, 108: 3.5, 159: 4.5}
ROLLER_JOURNAL_MM = {42: 12, 60: 15, 76: 20, 108: 25, 159: 30}

COMPLEXITY_FACTORS = {
    "Стандартный цех": 1.0,
    "Стесненные условия": 1.2,
    "Высотные работы": 1.5,
}


# =============================================================================
# 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

def next_standard(values: List[float], x: float) -> Optional[float]:
    """Первое стандартное значение >= x. Если ряда не хватает — None."""
    for value in values:
        if value >= x:
            return value
    return None


def largest_standard_not_above(values: List[float], x: float) -> Optional[float]:
    """Максимальное стандартное значение <= x."""
    allowed = [v for v in values if v <= x]
    return max(allowed) if allowed else None


def linear_interp(table: List[Tuple[float, float]], x: float) -> float:
    """Линейная интерполяция табличной зависимости."""
    if x <= table[0][0]:
        return table[0][1]
    if x >= table[-1][0]:
        return table[-1][1]

    for (x1, y1), (x2, y2) in zip(table[:-1], table[1:]):
        if x1 <= x <= x2:
            if x2 == x1:
                return y1
            return y1 + (y2 - y1) * (x - x1) / (x2 - x1)
    return table[-1][1]


def standard_motor(required_kw: float) -> Optional[float]:
    return next_standard(MOTOR_POWER_KW, required_kw)


def safe_div(a: float, b: float, default: float = 0.0) -> float:
    return a / b if abs(b) > 1e-12 else default


def kg_from_newton(force_n: float) -> float:
    """Эквивалентная статическая масса, кгс-эквивалент."""
    return force_n / G


# =============================================================================
# 3. ЛЕНТОЧНЫЙ КОНВЕЙЕР — ИНЖЕНЕРНАЯ МАТЕМАТИКА
# =============================================================================

@dataclass
class BeltInput:
    capacity_tph: float
    length_m: float
    incline_deg: float
    bulk_density_t_m3: float
    repose_angle_deg: float
    service_category: str = "Средние"
    abrasiveness: str = "Средняя"
    dustiness: str = "Низкая"
    max_lump_mm: float = 0.0
    fragile_cargo: bool = False
    trough_angle_deg: int = 30
    speed_mode: str = "Авто"
    manual_speed_mps: float = 1.6
    main_resistance_f: float = 0.020
    drive_efficiency: float = 0.92
    service_factor: float = 1.15
    startup_tension_factor: float = 1.30
    drive_friction_mu: float = 0.35
    wrap_angle_deg: float = 180.0
    carrying_idler_spacing_m: float = 1.2
    allowable_sag_ratio: float = 0.01
    belt_mass_override_kg_m: float = 0.0
    carry_rotating_mass_override_kg_m: float = 0.0
    return_rotating_mass_override_kg_m: float = 0.0
    special_resistance_n: float = 0.0


@dataclass
class BeltResult:
    speed_mps: float
    theoretical_width_mm: float
    selected_width_mm: Optional[float]
    capacity_coefficient: float
    conveyed_mass_kg_m: float
    belt_mass_kg_m: float
    carry_rotating_mass_kg_m: float
    return_rotating_mass_kg_m: float
    lift_height_m: float
    main_resistance_n: float
    length_factor_c: float
    lift_resistance_n: float
    effective_pull_n: float
    shaft_power_kw: float
    design_motor_power_kw: float
    selected_motor_kw: Optional[float]
    sag_tension_n: float
    slack_tension_n: float
    tight_tension_n: float
    max_design_tension_kn: float
    specific_working_tension_n_mm: Optional[float]
    warnings: List[str]


def incline_band_index(angle_deg: float) -> int:
    if angle_deg <= 10:
        return 0
    if angle_deg <= 15:
        return 1
    if angle_deg <= 18:
        return 2
    return 3


def capacity_coefficient(
    repose_angle_deg: float,
    incline_deg: float,
    trough_angle_deg: int,
) -> Tuple[float, List[str]]:
    """
    Интерполяция коэффициента C по углу естественного откоса.
    Для угла наклона трассы используется соответствующая колонка диапазона.
    Таблица рассчитана до 22°; выше 22° результат только оценочный.
    """
    warnings: List[str] = []
    trough_angle_deg = 20 if trough_angle_deg == 20 else 30
    table = CAPACITY_COEFFICIENTS[trough_angle_deg]

    phi = repose_angle_deg
    if phi < 30:
        warnings.append(
            "Угол естественного откоса ниже 30°. Коэффициент производительности "
            "экстраполирован по граничному значению 30°; требуется проверка по грузу."
        )
        phi = 30
    if phi > 45:
        warnings.append(
            "Угол естественного откоса выше 45°. Коэффициент принят по границе 45°; "
            "требуется уточнение характеристик груза."
        )
        phi = 45

    band = incline_band_index(min(incline_deg, 22.0))
    phis = sorted(table.keys())

    if phi in table:
        c = table[int(phi)][band]
    else:
        lower = max(p for p in phis if p <= phi)
        upper = min(p for p in phis if p >= phi)
        if lower == upper:
            c = table[lower][band]
        else:
            c1 = table[lower][band]
            c2 = table[upper][band]
            c = c1 + (c2 - c1) * (phi - lower) / (upper - lower)

    if incline_deg > 18:
        warnings.append(
            "Наклон свыше 18° требует обязательной проверки допустимого угла по "
            "конкретному транспортируемому материалу и условиям сцепления с лентой."
        )
    if incline_deg > 22:
        warnings.append(
            "Таблица коэффициентов производительности в этой модели ограничена 22°. "
            "Расчет ширины выше 22° является предварительным и выполнен по границе 22°."
        )

    return float(c), warnings


def recommended_belt_speed(
    capacity_tph: float,
    density_t_m3: float,
    abrasiveness: str = "Средняя",
    dustiness: str = "Низкая",
    max_lump_mm: float = 0.0,
    fragile_cargo: bool = False,
) -> float:
    """
    Инженерная рекомендация скорости внутри стандартного ряда ГОСТ 22644-77.

    ГОСТ 22644-77 задает допустимый номинальный ряд скоростей, но не выбирает
    единственное значение по четырем параметрам груза. Поэтому сначала берем
    базовую скорость из объемной производительности, затем ограничиваем ее по
    абразивности, пылеобразованию, крупности куска и хрупкости продукта.
    Ограничения — корпоративная инженерная эвристика для ТКП.
    """
    volumetric_m3_h = capacity_tph / max(density_t_m3, 0.01)
    if volumetric_m3_h <= 40:
        base = 1.0
    elif volumetric_m3_h <= 120:
        base = 1.25
    elif volumetric_m3_h <= 300:
        base = 1.6
    elif volumetric_m3_h <= 700:
        base = 2.0
    elif volumetric_m3_h <= 1400:
        base = 2.5
    else:
        base = 3.15

    cap = min(
        ABRASIVENESS_SPEED_CAP.get(abrasiveness, 2.5),
        DUSTINESS_SPEED_CAP.get(dustiness, 2.0),
    )
    if max_lump_mm >= 300:
        cap = min(cap, 1.0)
    elif max_lump_mm >= 150:
        cap = min(cap, 1.25)
    elif max_lump_mm >= 80:
        cap = min(cap, 1.6)
    if fragile_cargo:
        cap = min(cap, 1.0)

    target = min(base, cap)
    # Берем максимальную стандартную скорость, не превышающую целевую.
    return largest_standard_not_above(BELT_SPEEDS_MPS, target) or BELT_SPEEDS_MPS[0]


def belt_width_formula_mm(
    q_tph: float,
    c_coeff: float,
    speed_mps: float,
    density_t_m3: float,
) -> float:
    """
    Предварительный подбор ширины желобчатой ленты:

        B = 1.1 * ( sqrt(Q / (C * v * rho)) + 0.05 )   [м]

    Q   — т/ч
    C   — коэффициент формы поперечного сечения и наклона
    v   — м/с
    rho — т/м³

    После расчета B округляется ВВЕРХ до ряда ГОСТ 22644-77.
    """
    denom = c_coeff * speed_mps * density_t_m3
    if denom <= 0:
        raise ValueError("C, скорость и насыпная плотность должны быть > 0.")
    b_m = 1.1 * (math.sqrt(q_tph / denom) + 0.05)
    return b_m * 1000.0


def belt_auto_masses(width_mm: float) -> Tuple[float, float, float]:
    """
    Предварительные массы для тягового расчета, кг/м.

    Это НЕ нормативные значения ГОСТ и не заменяют паспортные данные.
    Их цель — дать работоспособный расчет ТКП до выбора конкретной ленты и
    роликоопор. В расширенных настройках каждое значение можно переопределить.
    """
    q_belt = 0.012 * width_mm
    q_ro = 0.010 * width_mm
    q_ru = 0.004 * width_mm
    return q_belt, q_ro, q_ru


def calc_belt(inp: BeltInput) -> BeltResult:
    warnings: List[str] = []

    if inp.capacity_tph <= 0:
        raise ValueError("Производительность должна быть больше нуля.")
    if inp.length_m <= 0:
        raise ValueError("Длина конвейера должна быть больше нуля.")
    if inp.bulk_density_t_m3 <= 0:
        raise ValueError("Насыпная плотность должна быть больше нуля.")
    if not (0 < inp.drive_efficiency <= 1):
        raise ValueError("КПД привода должен находиться в диапазоне (0; 1].")
    if inp.allowable_sag_ratio <= 0:
        raise ValueError("Допустимая относительная стрела провеса должна быть > 0.")

    c_coeff, c_warnings = capacity_coefficient(
        inp.repose_angle_deg, inp.incline_deg, inp.trough_angle_deg
    )
    warnings.extend(c_warnings)

    if inp.speed_mode == "Авто":
        speed = recommended_belt_speed(
            inp.capacity_tph, inp.bulk_density_t_m3, inp.abrasiveness,
            inp.dustiness, inp.max_lump_mm, inp.fragile_cargo
        )
        warnings.append(
            "Скорость выбрана инженерной эвристикой из стандартного ряда ГОСТ 22644-77. "
            "Выбор ограничен введенными параметрами крупности, абразивности и "
            "пылеобразования; для рабочего проекта требуется паспорт груза."
        )
    else:
        speed = inp.manual_speed_mps
        if speed not in BELT_SPEEDS_MPS:
            warnings.append("Заданная скорость не входит в заложенный стандартный ряд.")

    theoretical_width_mm = belt_width_formula_mm(
        inp.capacity_tph, c_coeff, speed, inp.bulk_density_t_m3
    )
    selected_width = next_standard(BELT_WIDTHS_MM, theoretical_width_mm)
    width_for_calc = selected_width if selected_width is not None else theoretical_width_mm
    if selected_width is None:
        warnings.append(
            f"Расчетная ширина {theoretical_width_mm:.0f} мм превышает максимальный "
            "ряд 3000 мм. Нужна другая компоновка/скорость/несколько конвейеров."
        )

    if inp.max_lump_mm > 0 and width_for_calc / inp.max_lump_mm < 3.0:
        warnings.append(
            "Ширина ленты менее трех максимальных размеров куска. Это не запрет ГОСТ, "
            "а сигнал обязательной проверки загрузочного сечения, грансостава и вероятности заклинивания."
        )

    # Масса груза на одном погонном метре ленты:
    # Q [т/ч] -> Q/3.6 [кг/с]; q_G = mass_flow / v.
    q_g = inp.capacity_tph / (3.6 * speed)

    auto_belt, auto_ro, auto_ru = belt_auto_masses(width_for_calc)
    q_b = inp.belt_mass_override_kg_m if inp.belt_mass_override_kg_m > 0 else auto_belt
    q_ro = (
        inp.carry_rotating_mass_override_kg_m
        if inp.carry_rotating_mass_override_kg_m > 0
        else auto_ro
    )
    q_ru = (
        inp.return_rotating_mass_override_kg_m
        if inp.return_rotating_mass_override_kg_m > 0
        else auto_ru
    )

    delta = math.radians(inp.incline_deg)
    h = inp.length_m * math.sin(delta)

    # ISO 5048: главное сопротивление движению:
    # F_H = f * L * g * [q_RO + q_RU + (2*q_B + q_G)*cos(delta)]
    f_h = (
        inp.main_resistance_f
        * inp.length_m
        * G
        * (q_ro + q_ru + (2.0 * q_b + q_g) * math.cos(delta))
    )

    # Для уклона: статическая составляющая подъема груза.
    # F_St = q_G * g * H
    f_st = q_g * G * h

    # Обобщающий коэффициент вторичных сопротивлений по длине.
    c_len = linear_interp(LENGTH_FACTOR_TABLE, inp.length_m)
    if inp.length_m < 80:
        warnings.append(
            "Длина менее 80 м: обобщающий коэффициент вторичных сопротивлений дает "
            "только предварительную оценку; в рабочем проекте вторичные сопротивления "
            "следует разложить по узлам (барабаны, загрузка, очистители и т. п.)."
        )

    # Эффективное тяговое усилие по упрощенной схеме:
    # F_U = C * F_H + F_St + F_special.
    f_u = c_len * f_h + f_st + max(inp.special_resistance_n, 0.0)

    # Мощность на валу двигателя с учетом КПД передачи.
    # P = F_U * v / (1000 * eta)
    shaft_power_kw = max(f_u, 0.0) * speed / (1000.0 * inp.drive_efficiency)
    design_motor_kw = shaft_power_kw * inp.service_factor
    selected_motor = standard_motor(design_motor_kw)
    if selected_motor is None:
        warnings.append(
            "Расчетная мощность выше заложенного ряда двигателей 315 кВт. "
            "Требуется специальный подбор привода."
        )

    # Минимальное натяжение для ограничения провеса между роликоопорами.
    # Для равномерно распределенной нагрузки w и малого провеса:
    # sag_ratio = delta/l; T ~= w*l / (8*sag_ratio)
    # Здесь w = (q_B + q_G)*g [Н/м], l = шаг роликоопор.
    sag_tension = (
        (q_b + q_g)
        * G
        * inp.carrying_idler_spacing_m
        / (8.0 * inp.allowable_sag_ratio)
    )

    # Тяговое условие Эйлера–Эйтельвейна на приводном барабане:
    # T1/T2 <= exp(mu * alpha), alpha — угол обхвата в радианах.
    wrap_rad = math.radians(inp.wrap_angle_deg)
    euler_ratio = math.exp(inp.drive_friction_mu * wrap_rad)
    if euler_ratio <= 1.0:
        raise ValueError("Некорректная комбинация коэффициента трения и угла обхвата.")

    t2_traction = max(f_u, 0.0) / (euler_ratio - 1.0)
    t2 = max(t2_traction, sag_tension)
    t1 = t2 + max(f_u, 0.0)

    # Коэффициент пускового/динамического натяжения — инженерный коэффициент.
    tmax = t1 * inp.startup_tension_factor

    specific = None
    if width_for_calc > 0:
        specific = tmax / width_for_calc  # Н / мм ширины ленты

    if theoretical_width_mm < 300:
        warnings.append(
            "Расчетная ширина меньше 300 мм; принят минимальный заложенный стандартный размер."
        )

    return BeltResult(
        speed_mps=speed,
        theoretical_width_mm=theoretical_width_mm,
        selected_width_mm=selected_width,
        capacity_coefficient=c_coeff,
        conveyed_mass_kg_m=q_g,
        belt_mass_kg_m=q_b,
        carry_rotating_mass_kg_m=q_ro,
        return_rotating_mass_kg_m=q_ru,
        lift_height_m=h,
        main_resistance_n=f_h,
        length_factor_c=c_len,
        lift_resistance_n=f_st,
        effective_pull_n=f_u,
        shaft_power_kw=shaft_power_kw,
        design_motor_power_kw=design_motor_kw,
        selected_motor_kw=selected_motor,
        sag_tension_n=sag_tension,
        slack_tension_n=t2,
        tight_tension_n=t1,
        max_design_tension_kn=tmax / 1000.0,
        specific_working_tension_n_mm=specific,
        warnings=warnings,
    )



# =============================================================================
# 3A. РАСШИРЕННЫЙ ПОДБОР ЛЕНТЫ / РОЛИКООПОР / БАРАБАНА / РЕДУКТОРА
# =============================================================================

@dataclass
class BeltAdvancedResult:
    preliminary_belt_type: str
    required_nominal_strength_n_mm: float
    selected_fabric: Optional[str]
    fabric_strength_n_mm: Optional[float]
    selected_plies: Optional[int]
    selected_nominal_strength_n_mm: Optional[float]
    strength_utilization: Optional[float]
    selected_idler_diameter_mm: Optional[int]
    drive_drum_diameter_mm: Optional[int]
    tail_drum_diameter_mm: Optional[int]
    drum_shell_length_mm: Optional[int]
    drum_rpm: Optional[float]
    gearbox_ratio_required: Optional[float]
    gearbox_ratio_selected: Optional[float]
    output_torque_nm: Optional[float]
    warnings: List[str]


def belt_type_from_service(service_category: str, abrasiveness: str, special_execution: str) -> str:
    if service_category == "Средние":
        # ГОСТ 20-2018: для высокоабразивных/абразивных грузов тип 2.1,
        # для малоабразивных материалов общего назначения — тип 2.2.
        base = "2.1" if abrasiveness == "Высокая" else "2.2"
    else:
        base = BELT_SERVICE_TYPES.get(service_category, "2.2")
    if special_execution == "Общего назначения":
        return base
    return f"{base} / исполнение: {special_execution}"


def allowed_fabrics_for_service(service_category: str, abrasiveness: str) -> List[Tuple[str, float]]:
    items = list(BELT_FABRICS_N_MM.items())
    if service_category == "Очень тяжелые":
        return [(n, s) for n, s in items if 300 <= s <= 630]
    if service_category == "Тяжелые":
        return [(n, s) for n, s in items if 200 <= s <= 630]
    if service_category == "Средние":
        # Встроенный автоподбор сознательно предпочитает синтетические ткани.
        # 2.1: 200–630 Н/мм; 2.2: 200–500 Н/мм (ГОСТ также допускает
        # комбинированную ткань 55 Н/мм, но ее оставляем для ручного выбора).
        upper = 630 if abrasiveness == "Высокая" else 500
        return [(n, s) for n, s in items if 200 <= s <= upper]
    # Для типа 3: синтетическая ткань 100 Н/мм или комбинированная 55 Н/мм.
    return [(n, s) for n, s in items if s in (55, 100)]


def select_belt_carcass(
    required_strength_n_mm: float,
    service_category: str,
    abrasiveness: str,
) -> Tuple[Optional[str], Optional[float], Optional[int], Optional[float]]:
    if service_category == "Очень тяжелые":
        ply_range = range(3, 7)
    elif service_category == "Тяжелые":
        ply_range = range(3, 7)
    else:
        ply_range = range(2, 7)

    candidates = []
    for fabric, strength in allowed_fabrics_for_service(service_category, abrasiveness):
        for plies in ply_range:
            nominal = strength * plies
            if nominal >= required_strength_n_mm:
                candidates.append((nominal, plies, strength, fabric))
    if not candidates:
        return None, None, None, None
    nominal, plies, strength, fabric = min(candidates, key=lambda x: (x[0], x[1], x[2]))
    return fabric, strength, plies, nominal


def recommend_belt_idler_diameter(width_mm: float, speed_mps: float) -> int:
    """Предварительный выбор диаметра из ряда ГОСТ 22646-77."""
    if width_mm <= 500:
        target = 89 if speed_mps <= 4 else 108
    elif width_mm <= 650:
        target = 89 if speed_mps <= 2 else 108
    elif width_mm <= 800:
        target = 89 if speed_mps <= 2 else 108
    elif width_mm <= 1000:
        target = 108 if speed_mps <= 4 else 127
    elif width_mm <= 1200:
        target = 108 if speed_mps <= 2 else 127
    elif width_mm <= 1400:
        target = 127 if speed_mps <= 4 else 159
    elif width_mm <= 1600:
        target = 127 if speed_mps <= 2 else 159
    else:
        target = 159
    return int(next_standard(BELT_IDLER_DIAMETERS_MM, target) or BELT_IDLER_DIAMETERS_MM[-1])


def calc_belt_advanced(
    belt: BeltResult,
    belt_input: BeltInput,
    belt_strength_safety: float = 10.0,
    joint_efficiency: float = 0.90,
    special_execution: str = "Общего назначения",
    drum_factor_mm_per_ply: float = 125.0,
    motor_rpm: float = 1500.0,
) -> BeltAdvancedResult:
    warnings: List[str] = []
    width = belt.selected_width_mm or belt.theoretical_width_mm
    specific = belt.specific_working_tension_n_mm or 0.0
    eta_joint = max(min(joint_efficiency, 1.0), 0.1)

    # ГОСТ 20-2018 задает номинальную прочность прокладок и ленты.
    # Запас прочности и эффективность стыка — проектные параметры калькулятора.
    required_nominal = specific * belt_strength_safety / eta_joint
    fabric, fabric_strength, plies, nominal = select_belt_carcass(required_nominal, belt_input.service_category, belt_input.abrasiveness)
    utilization = required_nominal / nominal if nominal else None

    if fabric is None:
        warnings.append(
            "В ограниченном встроенном ряду ГОСТ 20-2018 не найден каркас требуемой прочности. "
            "Нужен расчет другой конструкции ленты/стыка или согласование с изготовителем."
        )

    idler_d = recommend_belt_idler_diameter(width, belt.speed_mps)

    drive_d = tail_d = shell_l = None
    drum_rpm = ratio_required = ratio_selected = torque = None
    if plies:
        # D ~ (125...150)*n — инженерная методика изгиба многопрокладочной ленты.
        # ГОСТ 22644-77 используется только для округления результата до номинального ряда.
        target_drive = drum_factor_mm_per_ply * plies
        drive_d = next_standard(DRUM_DIAMETERS_MM, target_drive)
        if drive_d is not None:
            tail_d = next_standard(DRUM_DIAMETERS_MM, max(0.8 * drive_d, DRUM_DIAMETERS_MM[0]))
            shell_l = DRUM_SHELL_LENGTH_MM.get(int(width))
            drum_rpm = 60.0 * belt.speed_mps / (math.pi * drive_d / 1000.0)
            if drum_rpm > 0:
                ratio_required = motor_rpm / drum_rpm
                ratio_selected = next_standard(STANDARD_GEAR_RATIOS, ratio_required)
                if ratio_selected is None:
                    warnings.append("Требуемое передаточное число выше встроенного ряда редукторов.")
            torque = belt.effective_pull_n * (drive_d / 1000.0) / 2.0 * belt_input.service_factor
        else:
            warnings.append("Расчетный диаметр приводного барабана превышает ряд ГОСТ 22644-77.")

    warnings.append(
        "Подбор каркаса является предварительной проверкой по прочности. Окончательное обозначение "
        "ленты требует выбора обкладок, резины, бортов, стыка и проверки применяемой на дату проекта редакции ГОСТ 20-2018."
    )

    return BeltAdvancedResult(
        preliminary_belt_type=belt_type_from_service(belt_input.service_category, belt_input.abrasiveness, special_execution),
        required_nominal_strength_n_mm=required_nominal,
        selected_fabric=fabric,
        fabric_strength_n_mm=fabric_strength,
        selected_plies=plies,
        selected_nominal_strength_n_mm=nominal,
        strength_utilization=utilization,
        selected_idler_diameter_mm=idler_d,
        drive_drum_diameter_mm=int(drive_d) if drive_d is not None else None,
        tail_drum_diameter_mm=int(tail_d) if tail_d is not None else None,
        drum_shell_length_mm=shell_l,
        drum_rpm=drum_rpm,
        gearbox_ratio_required=ratio_required,
        gearbox_ratio_selected=ratio_selected,
        output_torque_nm=torque,
        warnings=warnings,
    )


# =============================================================================
# 3B. ПРЕДВАРИТЕЛЬНЫЙ РАСЧЕТ ДВУХБАЛОЧНОЙ РАМЫ
# =============================================================================

@dataclass
class FrameResult:
    section: Optional[str]
    mass_kg_m_one_rail: Optional[float]
    stress_mpa: Optional[float]
    allowable_stress_mpa: float
    deflection_mm: Optional[float]
    allowable_deflection_mm: float
    stress_utilization: Optional[float]
    deflection_utilization: Optional[float]
    total_two_rail_mass_kg: Optional[float]
    warnings: List[str]


def rhs_properties(h_mm: float, b_mm: float, t_mm: float) -> Tuple[float, float, float, float]:
    """A [мм²], Ix [мм4], Wx [мм3], масса [кг/м] прямоугольной трубы."""
    if 2 * t_mm >= min(h_mm, b_mm):
        raise ValueError("Некорректная геометрия трубы")
    hi, bi = h_mm - 2 * t_mm, b_mm - 2 * t_mm
    area = h_mm * b_mm - hi * bi
    ix = (b_mm * h_mm**3 - bi * hi**3) / 12.0
    wx = ix / (h_mm / 2.0)
    mass = area * 1e-6 * 7850.0
    return area, ix, wx, mass


def calc_frame(
    conveyor_length_m: float,
    external_line_mass_kg_m_total: float,
    support_span_m: float,
    steel_yield_mpa: float,
    safety_factor: float = 1.5,
    deflection_ratio: float = 300.0,
    extra_mass_kg_m_each_rail: float = 10.0,
) -> FrameResult:
    warnings: List[str] = []
    allow_stress = steel_yield_mpa / max(safety_factor, 1.0)
    allow_defl = support_span_m * 1000.0 / max(deflection_ratio, 1.0)
    E = 2.0e5  # МПа = Н/мм²
    L_mm = support_span_m * 1000.0

    selected = None
    for h, b, t in FRAME_RHS_CATALOG:
        area, ix, wx, own_mass = rhs_properties(h, b, t)
        # Внешняя нагрузка делится на две продольные балки. Добавляем массу
        # собственно выбранной балки и редактируемый запас на настил/крепеж.
        line_mass_one = external_line_mass_kg_m_total / 2.0 + own_mass + extra_mass_kg_m_each_rail
        w_n_mm = line_mass_one * G / 1000.0
        mmax_n_mm = w_n_mm * L_mm**2 / 8.0
        stress = mmax_n_mm / wx
        deflection = 5.0 * w_n_mm * L_mm**4 / (384.0 * E * ix)
        if stress <= allow_stress and deflection <= allow_defl:
            selected = (h, b, t, own_mass, stress, deflection)
            break

    if selected is None:
        warnings.append(
            "Ни один профиль встроенного предварительного каталога не прошел по прочности/прогибу. "
            "Нужна ферма, уменьшение шага опор или расширенный сортамент."
        )
        return FrameResult(None, None, None, allow_stress, None, allow_defl, None, None, None, warnings)

    h, b, t, own_mass, stress, deflection = selected
    warnings.append(
        "Рама проверена как две шарнирно опертые продольные балки на равномерную нагрузку. "
        "Расчет не заменяет КМ/КМД: не учтены местные нагрузки, связи, стойки, сварные узлы, вибрация и устойчивость."
    )
    return FrameResult(
        section=f"{int(h)}x{int(b)}x{t:g}",
        mass_kg_m_one_rail=own_mass,
        stress_mpa=stress,
        allowable_stress_mpa=allow_stress,
        deflection_mm=deflection,
        allowable_deflection_mm=allow_defl,
        stress_utilization=stress / allow_stress,
        deflection_utilization=deflection / allow_defl,
        total_two_rail_mass_kg=own_mass * 2.0 * conveyor_length_m,
        warnings=warnings,
    )


def calc_roller_drive_selection(roller: "RollerResult", speed_mps: float, motor_rpm: float = 1500.0) -> Dict[str, Optional[float]]:
    if not roller.selected_diameter_mm or speed_mps <= 0:
        return {"roller_rpm": None, "ratio_required": None, "ratio_selected": None, "torque_nm": None}
    d_m = roller.selected_diameter_mm / 1000.0
    rpm = 60.0 * speed_mps / (math.pi * d_m)
    ratio = motor_rpm / rpm if rpm > 0 else None
    ratio_sel = next_standard(STANDARD_GEAR_RATIOS, ratio) if ratio else None
    force = roller.total_drive_resistance_n or 0.0
    torque = force * d_m / 2.0
    return {"roller_rpm": rpm, "ratio_required": ratio, "ratio_selected": ratio_sel, "torque_nm": torque}


# =============================================================================
# 4. РОЛИКОВЫЙ КОНВЕЙЕР — ИНЖЕНЕРНАЯ МАТЕМАТИКА
# =============================================================================

@dataclass
class RollerInput:
    conveyor_length_m: float
    cargo_shape: str
    cargo_length_mm: float
    cargo_width_mm: float
    cargo_height_mm: float
    cylinder_diameter_mm: float
    cylinder_axial_length_mm: float
    cargo_mass_kg: float
    speed_mps: float
    conveyor_type: str
    side_clearance_each_mm: float = 50.0
    dynamic_load_factor: float = 1.25
    load_gap_mm: float = 100.0
    simultaneous_loads_override: int = 0
    drive_efficiency: float = 0.85
    drive_service_factor: float = 1.50
    rolling_resistance_arm_mm: float = 0.50
    bearing_friction_mu: float = 0.03
    roller_rotating_mass_override_kg: float = 0.0


@dataclass
class RollerResult:
    contact_length_mm: float
    cargo_cross_width_mm: float
    minimum_roller_width_mm: float
    selected_roller_length_mm: Optional[int]
    max_pitch_by_three_rollers_mm: float
    selected_pitch_mm: Optional[int]
    roller_count: int
    design_load_per_roller_n: float
    load_per_roller_kg: float
    selected_diameter_mm: Optional[int]
    selected_roller_capacity_n: Optional[float]
    roller_capacity_utilization: Optional[float]
    simultaneous_loads: int
    estimated_rotating_mass_kg: Optional[float]
    motion_resistance_one_load_n: Optional[float]
    total_drive_resistance_n: Optional[float]
    steady_power_kw: float
    design_motor_power_kw: float
    selected_motor_kw: Optional[float]
    theoretical_gravity_slope_deg: Optional[float]
    warnings: List[str]


def estimate_roller_rotating_mass_kg(diameter_mm: int, length_mm: int) -> float:
    """
    Оценка вращающейся массы ролика по массе стальной трубы + торцевых деталей.
    Это не норматив ГОСТ; при наличии паспорта ролика значение нужно заменить.
    """
    wall_mm = ROLLER_WALL_MM[diameter_mm]
    d_o = diameter_mm / 1000.0
    d_i = max((diameter_mm - 2 * wall_mm) / 1000.0, 0.001)
    l = length_mm / 1000.0
    tube_volume = math.pi / 4.0 * (d_o**2 - d_i**2) * l
    tube_mass = tube_volume * 7850.0
    end_parts = 0.45 + 0.006 * diameter_mm
    return tube_mass + end_parts


def choose_roller_diameter(
    roller_length_mm: int,
    design_load_n: float,
) -> Tuple[Optional[int], Optional[float]]:
    """Выбирает минимальный диаметр, выдерживающий расчетную нагрузку."""
    for d in ROLLER_DIAMETERS_MM:
        cap = ROLLER_CAPACITY_N.get(d, {}).get(roller_length_mm)
        if cap is not None and cap >= design_load_n:
            return d, cap
    return None, None


def calc_roller(inp: RollerInput) -> RollerResult:
    warnings: List[str] = []

    if inp.conveyor_length_m <= 0:
        raise ValueError("Длина рольганга должна быть больше нуля.")
    if inp.cargo_mass_kg <= 0:
        raise ValueError("Масса груза должна быть больше нуля.")
    if inp.speed_mps < 0:
        raise ValueError("Скорость не может быть отрицательной.")

    if inp.cargo_shape == "Прямоугольный груз":
        contact_len = inp.cargo_length_mm
        cross_width = inp.cargo_width_mm
        if contact_len <= 0 or cross_width <= 0:
            raise ValueError("Длина и ширина прямоугольного груза должны быть > 0.")
    else:
        contact_len = inp.cylinder_diameter_mm
        cross_width = inp.cylinder_axial_length_mm
        if contact_len <= 0 or cross_width <= 0:
            raise ValueError("Диаметр и осевая длина цилиндра должны быть > 0.")
        warnings.append(
            "Для цилиндра принято, что ось цилиндра ориентирована поперек направления "
            "движения. Если ориентация другая — контактную геометрию нужно изменить."
        )

    # Минимальная рабочая ширина ролика = поперечный габарит груза + два зазора.
    min_width = cross_width + 2.0 * inp.side_clearance_each_mm
    selected_length = next_standard(ROLLER_LENGTHS_MM, min_width)
    if selected_length is None:
        warnings.append(
            f"Требуемая ширина ролика {min_width:.0f} мм превышает заложенный ряд 1200 мм. "
            "Требуется специальный ролик/двухниточная схема."
        )

    # Условие минимум трех роликов под грузом:
    # p <= L_contact / 3.
    max_pitch = contact_len / 3.0
    selected_pitch = largest_standard_not_above(ROLLER_PITCHES_MM, max_pitch)
    if selected_pitch is None:
        warnings.append(
            f"Для контактной длины {contact_len:.0f} мм нужен шаг <= {max_pitch:.1f} мм, "
            "что меньше минимального заложенного стандартного шага 50 мм."
        )
        pitch_for_count = max_pitch
    else:
        pitch_for_count = float(selected_pitch)

    # Число роликов вдоль всей рамы.
    roller_count = max(2, math.ceil(inp.conveyor_length_m * 1000.0 / pitch_for_count) + 1)

    # Для гарантированного условия расчет нагрузки ведем консервативно по 3 роликам,
    # даже если фактически при выбранном шаге под грузом будет 4 и более роликов.
    design_load_per_roller_n = inp.cargo_mass_kg * G * inp.dynamic_load_factor / 3.0
    load_per_roller_kg = kg_from_newton(design_load_per_roller_n)

    selected_d = None
    selected_cap = None
    utilization = None
    rotating_mass = None
    one_load_resistance = None
    total_resistance = None
    steady_power = 0.0
    design_motor = 0.0
    selected_motor = None
    gravity_slope = None
    # Filling affects frame load even if no standard roller can carry the cargo.
    simultaneous = max(inp.simultaneous_loads_override, 1) if inp.simultaneous_loads_override > 0 else max(
        1, math.floor((inp.conveyor_length_m * 1000.0 + max(inp.load_gap_mm, 0.0))
                      / (contact_len + max(inp.load_gap_mm, 0.0))))

    if selected_length is not None:
        selected_d, selected_cap = choose_roller_diameter(int(selected_length), design_load_per_roller_n)
        if selected_d is None:
            warnings.append(
                "Ни один заложенный типоразмер ролика не проходит по сочетанию длины и "
                "расчетной нагрузки. Требуется специальный ролик и расчет подшипников/оси."
            )
        else:
            utilization = design_load_per_roller_n / selected_cap if selected_cap else None

            if inp.roller_rotating_mass_override_kg > 0:
                rotating_mass = inp.roller_rotating_mass_override_kg
            else:
                rotating_mass = estimate_roller_rotating_mass_kg(selected_d, int(selected_length))
                warnings.append(
                    "Масса вращающейся части ролика оценена по геометрической модели трубы. "
                    "Для рабочего проекта замените ее паспортной массой выбранного ролика."
                )

            # Сколько грузов может одновременно находиться на конвейере, если он заполнен.
            if inp.simultaneous_loads_override > 0:
                simultaneous = inp.simultaneous_loads_override
            else:
                packing_pitch = contact_len + max(inp.load_gap_mm, 0.0)
                simultaneous = max(
                    1,
                    math.floor(
                        (inp.conveyor_length_m * 1000.0 + max(inp.load_gap_mm, 0.0))
                        / max(packing_pitch, 1.0)
                    ),
                )
            # Нельзя физически учитывать меньше 1 единицы.
            simultaneous = max(simultaneous, 1)

            # Сопротивление движению одного груза на горизонтальном рольганге.
            # Используется классическая расчетная схема:
            # W1 = G_load * 2k / D                  — качение груза по роликам
            # W2 = (G_load + P*z') * mu*d / D       — трение в опорах роликов
            # W3 = k_rot * P*z*v^2 / (g*L)          — вращательные сопротивления
            # k — приведенное плечо сопротивления качению, м;
            # P — вес одного ролика, Н;
            # z' — число роликов под одним грузом (принято 3 минимум);
            # z — общее число роликов;
            # d — диаметр цапфы/подшипникового узла;
            # D — диаметр ролика.
            d_m = selected_d / 1000.0
            journal_d_m = ROLLER_JOURNAL_MM[selected_d] / 1000.0
            k_roll_m = inp.rolling_resistance_arm_mm / 1000.0
            g_load = inp.cargo_mass_kg * G
            p_roller = rotating_mass * G
            z_support = 3
            k_rot = 0.85

            w1 = g_load * 2.0 * k_roll_m / d_m
            w2 = (g_load + p_roller * z_support) * inp.bearing_friction_mu * journal_d_m / d_m

            # W3 относится к вращающимся массам самого рольганга. Его нельзя
            # повторно умножать на число грузов: иначе сопротивление роликов
            # будет учтено несколько раз. Поэтому грузовые сопротивления W1+W2
            # умножаются на число одновременно находящихся изделий, а W3
            # добавляется один раз для всего конвейера.
            w3_total = (
                k_rot
                * p_roller
                * roller_count
                * inp.speed_mps**2
                / (G * max(inp.conveyor_length_m, 0.001))
            )
            cargo_resistance_one = max(w1 + w2, 0.0)
            one_load_resistance = cargo_resistance_one
            total_resistance = cargo_resistance_one * simultaneous + max(w3_total, 0.0)

            if inp.conveyor_type == "Приводной":
                if not (0 < inp.drive_efficiency <= 1):
                    raise ValueError("КПД привода рольганга должен быть в диапазоне (0; 1].")
                # P = F*v / eta. Перевод Вт -> кВт.
                steady_power = total_resistance * inp.speed_mps / (1000.0 * inp.drive_efficiency)
                design_motor = steady_power * inp.drive_service_factor
                selected_motor = standard_motor(design_motor)
                if selected_motor is None:
                    warnings.append(
                        "Мощность привода превышает заложенный ряд 315 кВт. "
                        "Требуется специальный привод."
                    )
            else:
                # Теоретический минимальный уклон для самодвижения одного груза:
                # G*sin(alpha) >= W. Для малых углов alpha ~= atan(W/G).
                gravity_slope = math.degrees(math.atan2(one_load_resistance, g_load))
                warnings.append(
                    "Для неприводного рольганга вычислен только теоретический минимальный "
                    "уклон. Реальный уклон должен проверяться испытанием с учетом пуска, "
                    "неровностей груза, загрязнения и требований безопасности."
                )
    return RollerResult(
        contact_length_mm=contact_len,
        cargo_cross_width_mm=cross_width,
        minimum_roller_width_mm=min_width,
        selected_roller_length_mm=int(selected_length) if selected_length is not None else None,
        max_pitch_by_three_rollers_mm=max_pitch,
        selected_pitch_mm=int(selected_pitch) if selected_pitch is not None else None,
        roller_count=roller_count,
        design_load_per_roller_n=design_load_per_roller_n,
        load_per_roller_kg=load_per_roller_kg,
        selected_diameter_mm=selected_d,
        selected_roller_capacity_n=selected_cap,
        roller_capacity_utilization=utilization,
        simultaneous_loads=simultaneous,
        estimated_rotating_mass_kg=rotating_mass,
        motion_resistance_one_load_n=one_load_resistance,
        total_drive_resistance_n=total_resistance,
        steady_power_kw=steady_power,
        design_motor_power_kw=design_motor,
        selected_motor_kw=selected_motor,
        theoretical_gravity_slope_deg=gravity_slope,
        warnings=warnings,
    )


# =============================================================================
# 5. ЭКОНОМИКА / ТРУДОЕМКОСТЬ
# =============================================================================

@dataclass
class EconomicResult:
    labor_hours: float
    labor_cost_rub: float
    materials_cost_rub: float
    total_estimate_rub: float
    details: Dict[str, float]
    warnings: List[str]


def calc_belt_economics(
    belt: BeltResult,
    conveyor_length_m: float,
    hourly_rate_rub: float,
    complexity_factor: float,
    price_frame_m: float,
    price_belt_m: float,
    price_roller_pc: float,
    price_motor: float,
    extra_components: float,
    frame_h_m: float,
    drive_station_h: float,
    tension_station_h: float,
    roller_h_pc: float,
    belt_install_h_m: float,
    carry_spacing_m: float,
    return_spacing_m: float,
    belt_length_reserve_pct: float,
) -> EconomicResult:
    warnings: List[str] = []

    carry_sets = math.ceil(conveyor_length_m / max(carry_spacing_m, 0.1)) + 1
    carry_rollers = carry_sets * 3  # трехроликовая желобчатая опора
    return_rollers = math.ceil(conveyor_length_m / max(return_spacing_m, 0.1)) + 1
    physical_rollers = carry_rollers + return_rollers

    # Без диаметров барабанов точную длину замкнутой ленты определить нельзя.
    # Для ТКП принимаем 2L и добавляем редактируемый резерв.
    belt_loop_length = 2.0 * conveyor_length_m * (1.0 + belt_length_reserve_pct / 100.0)

    h_frame = frame_h_m * conveyor_length_m
    h_stations = drive_station_h + tension_station_h
    h_rollers = roller_h_pc * physical_rollers
    h_belt = belt_install_h_m * belt_loop_length
    labor_hours = h_frame + h_stations + h_rollers + h_belt
    labor_cost = labor_hours * hourly_rate_rub * complexity_factor

    frame_cost = price_frame_m * conveyor_length_m
    belt_cost = price_belt_m * belt_loop_length
    rollers_cost = price_roller_pc * physical_rollers
    materials = frame_cost + belt_cost + rollers_cost + price_motor + extra_components
    total = labor_cost + materials

    if hourly_rate_rub <= 0:
        warnings.append("Ставка нормо-часа равна нулю — стоимость работ не начислена.")
    warnings.append(
        "Трудоемкость рассчитана по редактируемым внутренним коэффициентам прототипа, "
        "а не по ГОСТ. После хронометража предприятия коэффициенты следует заменить."
    )

    return EconomicResult(
        labor_hours=labor_hours,
        labor_cost_rub=labor_cost,
        materials_cost_rub=materials,
        total_estimate_rub=total,
        details={
            "Рама, нормо-ч": h_frame,
            "Приводная + натяжная станции, нормо-ч": h_stations,
            "Монтаж роликов/роликоопор, нормо-ч": h_rollers,
            "Протяжка/стыковка/центровка ленты, нормо-ч": h_belt,
            "Физическое количество роликов, шт": float(physical_rollers),
            "Оценочная длина замкнутой ленты, м": belt_loop_length,
            "Рама, руб": frame_cost,
            "Лента, руб": belt_cost,
            "Ролики, руб": rollers_cost,
            "Мотор-редуктор, руб": price_motor,
            "Прочие комплектующие, руб": extra_components,
        },
        warnings=warnings,
    )


def calc_roller_economics(
    roller: RollerResult,
    conveyor_length_m: float,
    conveyor_type: str,
    hourly_rate_rub: float,
    complexity_factor: float,
    price_frame_m: float,
    price_roller_pc: float,
    price_motor: float,
    extra_components: float,
    frame_h_m: float,
    roller_h_pc: float,
    drive_station_h: float,
    adjustment_h_m: float,
) -> EconomicResult:
    warnings: List[str] = []

    h_frame = frame_h_m * conveyor_length_m
    h_rollers = roller_h_pc * roller.roller_count
    h_drive = drive_station_h if conveyor_type == "Приводной" else 0.0
    h_adjustment = adjustment_h_m * conveyor_length_m
    labor_hours = h_frame + h_rollers + h_drive + h_adjustment
    labor_cost = labor_hours * hourly_rate_rub * complexity_factor

    frame_cost = price_frame_m * conveyor_length_m
    rollers_cost = price_roller_pc * roller.roller_count
    motor_cost = price_motor if conveyor_type == "Приводной" else 0.0
    materials = frame_cost + rollers_cost + motor_cost + extra_components
    total = labor_cost + materials

    if hourly_rate_rub <= 0:
        warnings.append("Ставка нормо-часа равна нулю — стоимость работ не начислена.")
    warnings.append(
        "Трудоемкость рассчитана по редактируемым внутренним коэффициентам прототипа, "
        "а не по ГОСТ. После хронометража предприятия коэффициенты следует заменить."
    )

    return EconomicResult(
        labor_hours=labor_hours,
        labor_cost_rub=labor_cost,
        materials_cost_rub=materials,
        total_estimate_rub=total,
        details={
            "Рама, нормо-ч": h_frame,
            "Установка роликов, нормо-ч": h_rollers,
            "Монтаж приводной станции, нормо-ч": h_drive,
            "Регулировка/центровка, нормо-ч": h_adjustment,
            "Количество роликов, шт": float(roller.roller_count),
            "Рама, руб": frame_cost,
            "Ролики, руб": rollers_cost,
            "Мотор-редуктор, руб": motor_cost,
            "Прочие комплектующие, руб": extra_components,
        },
        warnings=warnings,
    )

