"""
ЧЕРНОВИК инженерного ядра для шнекового транспортера (25.SHT, Тех-Аэро).

СТАТУС: не проверено инженером Тех-Аэро. Составлено по открытым инженерным
источникам (классические формулы расчёта винтовых/шнековых конвейеров,
приводимые в отраслевых методичках и калькуляторах) — см. список источников
в конце файла. НЕ использовать для реального проектирования или коммерческого
расчёта без проверки и подтверждения главным инженером/технологом.

Назначение: показать, как поля опросного листа "Опросный_Шнековый"
(BOM_модели_и_опросные_листы_транспортеров.xlsx, Stage 11) могли бы
математически превращаться в параметры CAD-модели (диаметр шнека, шаг витка,
частота вращения, мощность мотор-редуктора) — то есть заполнить роль
"инженерного ядра", которое в карте связи (лист "Связь_с_себестоимостью")
указано как готовое, но нигде не найдено в виде кода/формул (Stage 11).

Не покрыто (нет проверенной публичной формулы, найденной на момент черновика):
- толщина витка (обычно определяется прочностным расчётом по крутящему моменту,
  не по расходной формуле);
- толщина корпуса/облицовки (футеровка) — конструктивный, не расчётный выбор
  по абразивности;
- расчёт для двухвального исполнения;
- расчёт для вертикальных/крутонаклонных шнеков (>20°) — отдельная методика.
"""

from __future__ import annotations
from dataclasses import dataclass
import math

# ---------------------------------------------------------------------------
# Справочные ряды и коэффициенты (см. источники в конце файла)
# ---------------------------------------------------------------------------

# Стандартный ряд диаметров шнека, мм
STANDARD_DIAMETERS_MM = [100, 125, 160, 200, 250, 320, 400, 500, 650, 800]

# Стандартный ряд мощностей мотор-редукторов, кВт (обычная линейка,
# уточнить по фактическому каталогу поставщика приводов Тех-Аэро)
STANDARD_MOTOR_KW = [0.37, 0.55, 0.75, 1.1, 1.5, 2.2, 3.0, 4.0, 5.5, 7.5, 11.0, 15.0, 18.5, 22.0]


class Abrasiveness:
    LOW = "низкая"
    MEDIUM = "средняя"
    HIGH = "высокая"


# Коэффициент заполнения желоба ψ — зависит от груза (комментарий в опросном
# листе поля "Абразивность", "Липкость / налипание")
FILL_FACTOR_PSI = {
    Abrasiveness.LOW: 0.40,      # лёгкие сыпучие непылящие
    Abrasiveness.MEDIUM: 0.30,   # средние
    Abrasiveness.HIGH: 0.25,     # абразивные/тяжёлые
}

# Отношение шага витка к диаметру E = S/D
STEP_TO_DIAMETER_RATIO = {
    Abrasiveness.LOW: 1.0,       # неабразивные — шаг = диаметру
    Abrasiveness.MEDIUM: 0.9,
    Abrasiveness.HIGH: 0.8,      # абразивные — уменьшенный шаг
}

# Коэффициент сопротивления движению груза ω (для расчёта мощности)
RESISTANCE_OMEGA = {
    Abrasiveness.LOW: 1.2,
    Abrasiveness.MEDIUM: 2.5,
    Abrasiveness.HIGH: 4.0,
}

# Коэффициент A в формуле максимальной частоты вращения n_max = A / sqrt(D[м])
MAX_SPEED_A = {
    Abrasiveness.LOW: 65.0,
    Abrasiveness.MEDIUM: 45.0,
    Abrasiveness.HIGH: 30.0,
}

# Минимальный коэффициент запаса диаметра по размеру куска: D >= K * a_max
# K=4 для рядового (несортированного) груза, K=12 для сортированного/калиброванного
LUMP_FACTOR_ORDINARY = 4.0
LUMP_FACTOR_SORTED = 12.0

DRIVE_EFFICIENCY = 0.88          # КПД привода η (типовое значение 0.85-0.9)
POWER_SAFETY_MARGIN = 1.25       # запас мощности двигателя (20-25%)


def incline_correction_c(angle_deg: float) -> float:
    """Поправочный коэффициент на угол наклона трассы (0° = горизонталь)."""
    if angle_deg <= 0:
        return 1.0
    if angle_deg <= 10:
        return 0.9
    if angle_deg <= 20:
        return 0.75
    raise ValueError(
        "Угол наклона > 20° требует отдельной методики расчёта "
        "(круто наклонные/вертикальные шнеки) — не покрыто этим черновиком."
    )


@dataclass
class QuestionnaireInput:
    """Поля, взятые из листа 'Опросный_Шнековый' (см. Stage 11)."""

    productivity_value: float          # "Производительность"
    productivity_unit: str             # "Единица производительности": "т/ч" | "кг/ч" | "м3/ч"
    bulk_density_kg_m3: float          # "Насыпная плотность"
    max_lump_size_mm: float            # "Максимальный размер куска"
    is_sorted_material: bool           # эвристика по "Состояние продукта" (гранулы/паллет = sorted)
    abrasiveness: str                  # "Абразивность": Abrasiveness.LOW/MEDIUM/HIGH
    working_length_mm: float           # "Рабочая длина по оси"
    incline_deg: float                 # "Угол наклона"
    forced_diameter_mm: float | None = None   # "Диаметр шнека", если заказчик задал явно
    forced_step_mm: float | None = None       # "Шаг витка", если задан явно


@dataclass
class EngineeringCoreResult:
    diameter_mm: float
    step_mm: float
    rotation_speed_rpm: float
    shaft_power_kw: float
    motor_power_kw: float
    fill_factor_psi: float
    incline_factor_c: float
    productivity_t_per_h: float
    warnings: list[str]


def _productivity_to_t_per_h(value: float, unit: str, density_kg_m3: float) -> float:
    unit = unit.strip().lower()
    if unit in ("т/ч", "t/h"):
        return value
    if unit in ("кг/ч", "kg/h"):
        return value / 1000.0
    if unit in ("м3/ч", "м³/ч", "m3/h"):
        return value * density_kg_m3 / 1000.0
    raise ValueError(f"Неизвестная единица производительности: {unit!r}")


def compute_engineering_core(inp: QuestionnaireInput) -> EngineeringCoreResult:
    warnings: list[str] = []

    q_t_h = _productivity_to_t_per_h(
        inp.productivity_value, inp.productivity_unit, inp.bulk_density_kg_m3
    )
    density_t_m3 = inp.bulk_density_kg_m3 / 1000.0
    psi = FILL_FACTOR_PSI[inp.abrasiveness]
    e_ratio = STEP_TO_DIAMETER_RATIO[inp.abrasiveness]
    c = incline_correction_c(inp.incline_deg)
    a_max = MAX_SPEED_A[inp.abrasiveness]

    lump_factor = LUMP_FACTOR_SORTED if inp.is_sorted_material else LUMP_FACTOR_ORDINARY
    min_diameter_mm = inp.max_lump_size_mm * lump_factor

    q_m3_h = q_t_h / density_t_m3 if density_t_m3 > 0 else 0.0

    def n_required_and_max(diameter_mm: float, step_mm: float) -> tuple[float, float]:
        d_m = diameter_mm / 1000.0
        s_m = step_mm / 1000.0
        cross_section_flow = 60.0 * (math.pi * d_m ** 2 / 4.0) * s_m * psi * c
        if cross_section_flow <= 0:
            raise ValueError("Некорректные входные данные: нулевое сечение потока.")
        n_req = q_m3_h / cross_section_flow
        n_max_ = a_max / math.sqrt(d_m)
        return n_req, n_max_

    if inp.forced_diameter_mm is not None:
        # Заказчик/инженер задал диаметр явно — считаем по нему без подбора,
        # но проверяем и предупреждаем, если он не проходит по ограничениям.
        diameter_mm = inp.forced_diameter_mm
        step_mm = inp.forced_step_mm if inp.forced_step_mm is not None else diameter_mm * e_ratio
        if diameter_mm < min_diameter_mm:
            warnings.append(
                f"Заданный диаметр {diameter_mm} мм меньше минимально допустимого "
                f"по крупности куска ({min_diameter_mm:.0f} мм) — требуется проверка "
                "инженером, увеличение диаметра или дробление продукта."
            )
        n_required, n_max = n_required_and_max(diameter_mm, step_mm)
        if n_required > n_max:
            warnings.append(
                f"При заданном диаметре {diameter_mm} мм требуемая частота вращения "
                f"({n_required:.1f} об/мин) превышает максимально допустимую "
                f"({n_max:.1f} об/мин) — заданный диаметр не проходит по производительности, "
                "нужна проверка инженером."
            )
        n_rpm = min(n_required, n_max)
    else:
        # Подбираем наименьший стандартный диаметр, который одновременно
        # проходит по крупности куска И позволяет обеспечить Q при n <= n_max.
        diameter_mm = None
        step_mm = None
        n_rpm = None
        for candidate_d in STANDARD_DIAMETERS_MM:
            if candidate_d < min_diameter_mm:
                continue
            candidate_step = candidate_d * e_ratio
            n_required, n_max = n_required_and_max(candidate_d, candidate_step)
            if n_required <= n_max:
                diameter_mm = candidate_d
                step_mm = candidate_step
                n_rpm = n_required
                break
        if diameter_mm is None:
            # Ни один стандартный диаметр не проходит — берём максимальный
            # из ряда и явно предупреждаем, что производительность не будет
            # достигнута при безопасной частоте вращения.
            diameter_mm = STANDARD_DIAMETERS_MM[-1]
            step_mm = diameter_mm * e_ratio
            n_required, n_max = n_required_and_max(diameter_mm, step_mm)
            n_rpm = min(n_required, n_max)
            reason = (
                f"превышает максимум стандартного ряда ({diameter_mm} мм)"
                if min_diameter_mm > diameter_mm
                else "не позволяет обеспечить заданную производительность "
                     "при безопасной частоте вращения ни на одном стандартном диаметре"
            )
            warnings.append(
                f"Требуемый диаметр по крупности куска ({min_diameter_mm:.0f} мм) {reason} — "
                "нужен нестандартный шнек или пересмотр требований, решение за инженером."
            )

    working_length_m = inp.working_length_mm / 1000.0
    height_gain_m = working_length_m * math.sin(math.radians(inp.incline_deg))
    omega = RESISTANCE_OMEGA[inp.abrasiveness]

    shaft_power_kw = (q_t_h * working_length_m * omega + q_t_h * height_gain_m) / 367.0
    motor_power_kw_raw = shaft_power_kw / DRIVE_EFFICIENCY * POWER_SAFETY_MARGIN
    motor_power_kw = next(
        (p for p in STANDARD_MOTOR_KW if p >= motor_power_kw_raw), STANDARD_MOTOR_KW[-1]
    )
    if motor_power_kw_raw > STANDARD_MOTOR_KW[-1]:
        warnings.append(
            f"Расчётная мощность ({motor_power_kw_raw:.2f} кВт) превышает "
            f"верхнюю границу стандартного ряда в этом черновике "
            f"({STANDARD_MOTOR_KW[-1]} кВт) — нужен каталог приводов поставщика."
        )

    return EngineeringCoreResult(
        diameter_mm=diameter_mm,
        step_mm=step_mm,
        rotation_speed_rpm=round(n_rpm, 1),
        shaft_power_kw=round(shaft_power_kw, 3),
        motor_power_kw=motor_power_kw,
        fill_factor_psi=psi,
        incline_factor_c=c,
        productivity_t_per_h=round(q_t_h, 3),
        warnings=warnings,
    )


if __name__ == "__main__":
    # Пример: приблизительно воспроизводим заказ №2377 (Stage 10) — но с
    # ПРИДУМАННЫМИ (а не реальными) значениями производительности и плотности,
    # так как в опросном листе заказа 2377 они не сохранились. Это только
    # иллюстрация работы формул, не реальная перепроверка заказа.
    example = QuestionnaireInput(
        productivity_value=5.0,
        productivity_unit="т/ч",
        bulk_density_kg_m3=700.0,
        max_lump_size_mm=15.0,
        is_sorted_material=False,
        abrasiveness=Abrasiveness.MEDIUM,
        working_length_mm=3000.0,
        incline_deg=0.0,
    )
    result = compute_engineering_core(example)
    print(result)


# ---------------------------------------------------------------------------
# Источники (формулы — общеинженерные, публикуются во множестве методичек;
# конкретные страницы, использованные при составлении черновика):
# - https://bigspiral.ru/raschet-shnekovogo-transportera-proizvoditelnost-diametr-moshhnost/
# - https://studfile.net/preview/17025552/page:3/ (стандартный ряд диаметров,
#   отношение шага к диаметру, коэффициент крупности куска)
# ---------------------------------------------------------------------------
