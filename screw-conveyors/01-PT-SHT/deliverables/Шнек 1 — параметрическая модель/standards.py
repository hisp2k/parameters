"""Small, cited selection catalog for the existing screw model."""
from __future__ import annotations

TUBES = {
    "133x4.5": (133, 4.5), "133x5": (133, 5),
    "140x4.5": (140, 4.5), "140x5": (140, 5), "140x5.5": (140, 5.5),
    "159x5": (159, 5),
}
SCREWS = {
    "100x80": (100, 80), "100x100": (100, 100),
    "125x100": (125, 100), "125x125": (125, 125),
    "160x125": (160, 125), "160x160": (160, 160),
    "200x160": (200, 160), "200x200": (200, 200),
}
MATERIALS = ("08Х18Н10", "12Х18Н10Т", "10Х17Н13М2Т")

CATALOG = {
    "tube": {"standard": "ГОСТ 10704-91", "url": "https://protect.gost.ru/gost/details/9d92e82e-d057-436a-abd4-5a56a7e07e96",
             "items": [{"id": key, "diameter": d, "wall": t} for key, (d, t) in TUBES.items()]},
    "screw": {"standard": "ГОСТ 2037-82, таблица 1", "url": "https://files.stroyinf.ru/Data2/1/4294751/4294751811.pdf",
              "items": [{"id": key, "diameter": d, "pitch": p} for key, (d, p) in SCREWS.items()]},
    "material": {"standard": "ГОСТ 5632-2014", "url": "https://protect.gost.ru/gost/details/d6ac3954-d07e-4a10-a038-f3ab9b1d5b7b",
                 "items": list(MATERIALS)},
}

def validate_selection(values: dict, selection: dict) -> list[str]:
    errors = []
    if not isinstance(selection, dict):
        return ["Выбор по ГОСТ должен быть объектом."]
    if set(selection) != {"tube", "screw", "material"}:
        return ["Набор выбранных позиций ГОСТ не соответствует каталогу."]
    tube = selection["tube"]
    if tube != "custom":
        if tube not in TUBES:
            errors.append("Неизвестный типоразмер трубы.")
        elif (values.get("tube_diameter"), values.get("tube_wall")) != TUBES[tube]:
            errors.append("Размер трубы не совпадает с выбранной позицией ГОСТ 10704-91.")
    screw = selection["screw"]
    if screw != "custom":
        if screw not in SCREWS:
            errors.append("Неизвестная пара диаметр–шаг винта.")
        elif (values.get("screw_diameter"), values.get("pitch")) != SCREWS[screw]:
            errors.append("Диаметр и шаг не совпадают с выбранной позицией ГОСТ 2037-82.")
    if selection["material"] != "unspecified" and selection["material"] not in MATERIALS:
        errors.append("Неизвестная марка стали ГОСТ 5632-2014.")
    return errors
