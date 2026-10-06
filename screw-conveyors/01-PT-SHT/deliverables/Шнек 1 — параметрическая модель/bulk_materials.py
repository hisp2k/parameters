"""Curated KWS bulk-material reference, separate from measured design inputs.

V means "may be conveyed in a vertical screw conveyor" in the source. It does
not certify suitability for this particular CAD model.
"""
from __future__ import annotations

SOURCE = "https://www.kwsmfg.com/engineering-guides/screw-conveyor/bulk-material-table/"
GUIDE = "https://www.kwsmfg.com/wp-content/uploads/Screw-Conveyor-Engineering-Guide.pdf"
LB_FT3_TO_KG_M3 = 16.01846337
IN_TO_MM = 25.4

# id: Russian name, source row, group, lb/ft³ range, source size, V marker, example use.
ROWS = {
    "wheat": ("Пшеница, зерно", "Wheat", "Зерно и семена", (45, 48), "-1/2", True, "перегрузка сухого зерна"),
    "wheat_cracked": ("Пшеница дроблёная", "Wheat, cracked", "Зерно и семена", (40, 45), "-1/8", True, "перегрузка дроблёного зерна"),
    "flaxseed": ("Льняное семя", "Flaxseed", "Зерно и семена", (43, 45), "-1/8", True, "хранение и перегрузка семян"),
    "sunflower_seed": ("Подсолнечник, семена", "Sunflower Seed", "Зерно и семена", (19, 38), "-1/2", True, "перегрузка масличных семян"),
    "corn_shelled": ("Кукуруза, зерно", "Corn, shelled", "Зерно и семена", (45, 45), "-1/2", True, "перегрузка кукурузного зерна"),
    "oats": ("Овёс", "Oats", "Зерно и семена", (26, 26), "-1/2", True, "перегрузка овса"),
    "rice_hulled": ("Рис очищенный от шелухи", "Rice, hulled", "Зерно и семена", (45, 49), "-1/2", True, "перегрузка риса"),
    "rice_polished": ("Рис шлифованный", "Rice, polished", "Зерно и семена", (30, 30), "-1/2", True, "перегрузка шлифованного риса"),
    "peas_dried": ("Горох сухой", "Peas, dried", "Зерно и семена", (45, 50), "-1/2", True, "перегрузка сухого гороха"),
    "barley_whole": ("Ячмень цельный", "Barley, whole", "Зерно и семена", (36, 48), "-1/8", False, "перегрузка ячменя"),
    "wheat_flour": ("Пшеничная мука", "Flour, Wheat", "Пищевые порошки и корма", (33, 40), "-1/64", True, "мукомольная линия; нужна проверка пылевой безопасности"),
    "corn_meal": ("Кукурузная мука", "Corn Meal", "Пищевые порошки и корма", (32, 40), "-1/8", True, "перегрузка кукурузной муки"),
    "sugar_dry": ("Сахар сухой гранулированный", "Sugar, refined, granulated, dry", "Пищевые порошки и корма", (50, 55), "-1/8", True, "перегрузка сахара; нужна проверка пылевой безопасности"),
    "starch": ("Крахмал", "Starch", "Пищевые порошки и корма", (25, 50), "-1/64", True, "перегрузка крахмала; нужна проверка пылевой безопасности"),
    "soybean_flour": ("Соевая мука", "Soybean, flour", "Пищевые порошки и корма", (25, 35), "-1/64", True, "перегрузка соевой муки"),
    "fish_meal": ("Рыбная мука", "Fish Meal", "Пищевые порошки и корма", (35, 40), "-1/2", True, "кормопроизводство"),
    "cement_portland": ("Цемент портландский", "Cement, Portland", "Минеральные и строительные", (94, 94), "-100M", False, "подача цемента"),
    "fly_ash": ("Зола уноса", "Flyash", "Минеральные и строительные", (30, 45), "-1/64", False, "подача золы"),
    "sand_dry": ("Песок сухой", "Sand, Dry Bank, dry", "Минеральные и строительные", (90, 110), "-1/8", False, "подача сухого песка; контроль износа"),
    "gypsum_powder": ("Гипс строительный, порошок", "Plaster of Paris (Gypsum)", "Минеральные и строительные", (60, 80), "-200M", False, "подача гипса"),
    "bentonite": ("Бентонит", "Bentonite", "Минеральные и строительные", (50, 60), "-100M", False, "подача бентонита"),
    "talc_powder": ("Тальк порошковый", "Talc, powder", "Минеральные и строительные", (50, 60), "-200M", True, "подача талька при проверке истирания"),
    "wood_flour": ("Древесная мука", "Wood Flour", "Древесные и полимерные", (16, 36), "-1/8", True, "подача древесной муки; нужна проверка пылевой безопасности"),
    "wood_chips": ("Щепа сортированная", "Wood Chips, screened", "Древесные и полимерные", (10, 30), "-3", False, "подача щепы; размер частиц может превышать предел ГОСТ 2037-82"),
    "polyethylene_pellets": ("Полиэтиленовые гранулы", "Polyethylene, pellets", "Древесные и полимерные", (35, 35), "-1/8", False, "подача гранул полимера"),
    "urea_prills": ("Карбамид, покрытые гранулы", "Urea Prills, Coated", "Химические продукты", (43, 46), "-1/8", False, "подача удобрения"),
    "zinc_oxide_light": ("Оксид цинка лёгкий", "Zinc Oxide, light", "Химические продукты", (10, 15), "-100M", True, "подача оксида цинка при проверке пыления"),
}

MATERIALS = {key: {"name": row[0], "source_name": row[1], "category": row[2],
                   "density_lb_ft3": row[3], "particle_spec": row[4],
                   "vertical_candidate": row[5], "application": row[6]}
             for key, row in ROWS.items()}

def _particle_mm(spec: str) -> float | None:
    if not spec.startswith("-") or "M" in spec:
        return None
    number = spec[1:]
    if "/" in number:
        top, bottom = number.split("/", 1)
        inches = float(top) / float(bottom)
    else:
        inches = float(number)
    return round(inches * IN_TO_MM, 3)

def catalog():
    items = []
    for key, value in MATERIALS.items():
        items.append({
            "id": key, "name": value["name"], "source_name": value["source_name"],
            "category": value["category"], "application": value["application"],
            "density_kg_m3": [round(x * LB_FT3_TO_KG_M3, 1) for x in value["density_lb_ft3"]],
            "particle_spec": value["particle_spec"],
            "max_particle_mm": _particle_mm(value["particle_spec"]),
            "vertical_candidate": value["vertical_candidate"],
            "source_url": SOURCE,
        })
    return {"source": SOURCE, "guide": GUIDE, "items": items,
            "categories": list(dict.fromkeys(x["category"] for x in items))}
