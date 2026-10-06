"""Canonical questionnaire schema for transporter calculator v3.

The AI/heuristic parser converts arbitrary customer questionnaires into these
canonical field IDs. Engineering calculations never read free-form document
text directly: they only receive validated canonical values.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class FieldMeta:
    field_id: str
    title: str
    unit: str
    dtype: str
    section: str
    required_for: str = ""
    default: Any = None
    allowed: Optional[List[str]] = None
    aliases: tuple[str, ...] = ()
    note: str = ""


FIELDS: List[FieldMeta] = [
    # Common / identification
    FieldMeta("project_name", "Наименование проекта", "", "str", "Общие", aliases=("проект", "наименование проекта", "объект", "название проекта")),
    FieldMeta("customer", "Заказчик", "", "str", "Общие", aliases=("заказчик", "клиент", "покупатель")),
    FieldMeta(
        "product_type", "Тип транспортера", "", "enum", "Общие", required_for="all",
        allowed=["Ленточный конвейер", "Рольганг"],
        aliases=("тип транспортера", "тип конвейера", "вид конвейера", "оборудование"),
    ),
    FieldMeta("cargo_name", "Наименование груза", "", "str", "Груз", aliases=("груз", "материал", "наименование груза", "перемещаемый продукт")),

    # Belt - critical input
    FieldMeta("capacity_tph", "Производительность", "т/ч", "float", "Ленточный", required_for="belt", aliases=("производительность", "расход", "подача", "производительность т/ч")),
    FieldMeta("length_m", "Длина по осям барабанов", "м", "float", "Ленточный", required_for="belt", aliases=("длина конвейера", "длина транспортера", "длина по осям барабанов", "межосевое расстояние")),
    FieldMeta("incline_deg", "Угол наклона трассы", "°", "float", "Ленточный", required_for="belt", aliases=("угол наклона", "наклон трассы", "угол подъема", "угол конвейера")),
    FieldMeta("bulk_density_t_m3", "Насыпная плотность", "т/м³", "float", "Ленточный", required_for="belt", aliases=("насыпная плотность", "объемная масса", "объёмная масса", "плотность груза")),
    FieldMeta("repose_angle_deg", "Угол естественного откоса", "°", "float", "Ленточный", required_for="belt", aliases=("угол естественного откоса", "угол откоса", "естественный откос")),

    # Belt - classification/defaults
    FieldMeta("service_category", "Категория условий эксплуатации", "", "enum", "Ленточный", default="Средние", allowed=["Легкие", "Средние", "Тяжелые", "Очень тяжелые"], aliases=("условия эксплуатации", "категория эксплуатации", "тяжесть условий")),
    FieldMeta("abrasiveness", "Абразивность", "", "enum", "Ленточный", default="Средняя", allowed=["Низкая", "Средняя", "Высокая"], aliases=("абразивность", "абразивный")),
    FieldMeta("dustiness", "Пылеобразование", "", "enum", "Ленточный", default="Низкая", allowed=["Низкая", "Средняя", "Высокая"], aliases=("пылеобразование", "пыление", "пыльность")),
    FieldMeta("max_lump_mm", "Максимальный кусок", "мм", "float", "Ленточный", default=0.0, aliases=("максимальный кусок", "крупность", "размер куска", "макс. кусок", "фракция")),
    FieldMeta("fragile_cargo", "Хрупкий груз", "да/нет", "bool", "Ленточный", default=False, aliases=("хрупкий груз", "хрупкость", "повреждаемый груз")),
    FieldMeta("trough_angle_deg", "Угол желобчатости роликоопоры", "°", "int", "Ленточный", default=30, aliases=("угол желобчатости", "угол роликоопоры", "желобчатость")),
    FieldMeta("special_execution", "Исполнение ленты", "", "enum", "Ленточный", default="Общего назначения", allowed=["Общего назначения", "Морозостойкая", "Теплостойкая", "Трудновоспламеняющаяся", "Пищевая"], aliases=("исполнение ленты", "тип исполнения ленты", "морозостойкость", "теплостойкость")),
    FieldMeta("carry_spacing_m", "Шаг грузовых роликоопор", "м", "float", "Ленточный", default=1.2, aliases=("шаг грузовых роликоопор", "шаг роликоопор", "шаг верхних роликоопор")),
    FieldMeta("return_spacing_m", "Шаг роликов холостой ветви", "м", "float", "Ленточный", default=2.5, aliases=("шаг холостых роликов", "шаг нижних роликов", "шаг обратной ветви")),
    FieldMeta("frame_support_span_m", "Шаг опор рамы", "м", "float", "Конструкция", default=2.0, aliases=("шаг опор рамы", "расстояние между опорами", "пролет рамы", "пролёт рамы")),
    FieldMeta("frame_steel_grade", "Материал рамы", "", "enum", "Конструкция", default="09Г2С (предварительно)", allowed=["Ст3 / S235 (предварительно)", "09Г2С (предварительно)"], aliases=("материал рамы", "сталь рамы", "марка стали")),

    # Roller conveyor - critical input
    FieldMeta("conveyor_length_m", "Длина рольганга", "м", "float", "Рольганг", required_for="roller", aliases=("длина рольганга", "длина роликового конвейера", "длина конвейера", "длина транспортера")),
    FieldMeta("cargo_shape", "Форма груза", "", "enum", "Рольганг", required_for="roller", allowed=["Прямоугольный груз", "Цилиндрический груз"], aliases=("форма груза", "тип груза", "форма изделия")),
    FieldMeta("cargo_length_mm", "Длина груза", "мм", "float", "Рольганг", aliases=("длина груза", "длина изделия", "длина упаковки")),
    FieldMeta("cargo_width_mm", "Ширина груза", "мм", "float", "Рольганг", aliases=("ширина груза", "ширина изделия", "ширина упаковки")),
    FieldMeta("cargo_height_mm", "Высота груза", "мм", "float", "Рольганг", aliases=("высота груза", "высота изделия", "высота упаковки")),
    FieldMeta("cylinder_diameter_mm", "Диаметр цилиндрического груза", "мм", "float", "Рольганг", aliases=("диаметр груза", "диаметр цилиндра", "диаметр рулона", "диаметр бочки")),
    FieldMeta("cylinder_axial_length_mm", "Осевая длина цилиндрического груза", "мм", "float", "Рольганг", aliases=("осевая длина", "длина цилиндра", "ширина рулона", "длина бочки")),
    FieldMeta("cargo_mass_kg", "Масса единицы груза", "кг", "float", "Рольганг", required_for="roller", aliases=("масса груза", "масса изделия", "вес груза", "масса единицы")),
    FieldMeta("speed_mps", "Скорость перемещения", "м/с", "float", "Рольганг", required_for="roller", aliases=("скорость перемещения", "скорость рольганга", "скорость конвейера")),
    FieldMeta("conveyor_type", "Тип рольганга", "", "enum", "Рольганг", required_for="roller", allowed=["Гравитационный/неприводной", "Приводной"], aliases=("тип рольганга", "привод", "приводной неприводной", "тип роликового конвейера")),
    FieldMeta("side_clearance_each_mm", "Боковой зазор с каждой стороны", "мм", "float", "Рольганг", default=50.0, aliases=("боковой зазор", "запас по ширине", "зазор по ширине")),
    FieldMeta("dynamic_load_factor", "Динамический коэффициент нагрузки", "", "float", "Рольганг", default=1.25, aliases=("динамический коэффициент", "коэффициент динамики", "ударная нагрузка")),
    FieldMeta("load_gap_mm", "Зазор между грузами", "мм", "float", "Рольганг", default=100.0, aliases=("зазор между грузами", "интервал между грузами", "шаг груза")),

    # Economics / installation
    FieldMeta("hourly_rate_rub", "Базовая ставка нормо-часа", "руб/ч", "float", "Экономика", aliases=("нормо-час", "ставка нормо-часа", "стоимость часа", "часовая ставка")),
    FieldMeta("complexity", "Сложность монтажа", "", "enum", "Экономика", default="Стандартный цех", allowed=["Стандартный цех", "Стесненные условия", "Высотные работы"], aliases=("сложность монтажа", "условия монтажа", "коэффициент сложности")),
    FieldMeta("price_frame_m", "Цена 1 м рамы", "руб/м", "float", "Экономика", default=0.0, aliases=("цена рамы", "стоимость рамы за метр", "рама руб м")),
    FieldMeta("price_belt_m", "Цена 1 м ленты", "руб/м", "float", "Экономика", default=0.0, aliases=("цена ленты", "стоимость ленты за метр", "лента руб м")),
    FieldMeta("price_roller_pc", "Цена 1 ролика", "руб/шт", "float", "Экономика", default=0.0, aliases=("цена ролика", "стоимость ролика", "ролик руб шт")),
    FieldMeta("price_motor", "Цена мотор-редуктора", "руб", "float", "Экономика", default=0.0, aliases=("цена мотор-редуктора", "стоимость мотор-редуктора", "цена привода")),
    FieldMeta("extra_components", "Прочие комплектующие", "руб", "float", "Экономика", default=0.0, aliases=("прочие комплектующие", "прочие материалы", "дополнительные комплектующие")),

    # Optional corporate labor norms; defaults are v2 preliminary norms
    FieldMeta("belt_frame_h_m", "Норма сборки рамы ленточного", "нормо-ч/м", "float", "Экономика", default=0.80),
    FieldMeta("belt_drive_h", "Монтаж приводной станции", "нормо-ч", "float", "Экономика", default=6.0),
    FieldMeta("belt_tension_h", "Монтаж натяжной станции", "нормо-ч", "float", "Экономика", default=4.0),
    FieldMeta("belt_roller_h_pc", "Установка ролика ленточного", "нормо-ч/шт", "float", "Экономика", default=0.10),
    FieldMeta("belt_install_h_m", "Монтаж/центровка ленты", "нормо-ч/м", "float", "Экономика", default=0.12),
    FieldMeta("roller_frame_h_m", "Норма сборки рамы рольганга", "нормо-ч/м", "float", "Экономика", default=0.60),
    FieldMeta("roller_roller_h_pc", "Установка ролика рольганга", "нормо-ч/шт", "float", "Экономика", default=0.12),
    FieldMeta("roller_drive_h", "Монтаж привода рольганга", "нормо-ч", "float", "Экономика", default=4.0),
    FieldMeta("roller_adjustment_h_m", "Регулировка рольганга", "нормо-ч/м", "float", "Экономика", default=0.15),
]

FIELD_MAP: Dict[str, FieldMeta] = {f.field_id: f for f in FIELDS}

BELT_REQUIRED = [f.field_id for f in FIELDS if f.required_for in ("belt", "all")]
ROLLER_REQUIRED_BASE = [f.field_id for f in FIELDS if f.required_for in ("roller", "all")]


def questionnaire_rows(product_type: str) -> List[FieldMeta]:
    """Fields shown in the standard template for a selected product."""
    if product_type == "belt":
        sections = {"Общие", "Груз", "Ленточный", "Конструкция", "Экономика"}
        return [f for f in FIELDS if f.section in sections and f.field_id not in {
            "conveyor_length_m", "cargo_shape", "cargo_length_mm", "cargo_width_mm", "cargo_height_mm",
            "cylinder_diameter_mm", "cylinder_axial_length_mm", "cargo_mass_kg", "speed_mps", "conveyor_type",
            "side_clearance_each_mm", "dynamic_load_factor", "load_gap_mm", "roller_frame_h_m",
            "roller_roller_h_pc", "roller_drive_h", "roller_adjustment_h_m",
        }]
    sections = {"Общие", "Груз", "Рольганг", "Конструкция", "Экономика"}
    return [f for f in FIELDS if f.section in sections and f.field_id not in {
        "capacity_tph", "length_m", "incline_deg", "bulk_density_t_m3", "repose_angle_deg", "service_category",
        "abrasiveness", "dustiness", "max_lump_mm", "fragile_cargo", "trough_angle_deg", "special_execution",
        "carry_spacing_m", "return_spacing_m", "belt_frame_h_m", "belt_drive_h", "belt_tension_h",
        "belt_roller_h_pc", "belt_install_h_m", "price_belt_m",
    }]
