from pathlib import Path

out = Path(r"C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\Песколовка\GRIT_CHAMBER_CODEX_TASK.md")
src = Path(r"C:\Users\adm\.codex\attachments\b8cd7552-32be-41e2-9e27-1bca6330df68\Вставленный текст.txt")
text = out.read_text(encoding="utf-8")
text = text.replace(
    "- [x] создать ось 30°, наружную огибающую шнека Ø100 мм и трубчатый кожух ID110/OD120 мм;",
    "- [x] создать ось 30°, винтовой круглый профиль Ø100 мм по наружному размеру с шагом 100 мм и трубчатый кожух ID110/OD120 мм;",
)
text = text.replace(
    "`CAD_STATUS = PILOT_PARTIAL_BATH_INTERNALS_FRAME_CASING_ENVELOPE`",
    "`CAD_STATUS = PILOT_PARTIAL_BATH_INTERNALS_FRAME_CASING_HELICAL_COIL`",
)
text = text.replace(
    "`GEOMETRY_INTERFERENCE_STATUS = PASS_SCREW_ENVELOPE_VS_OTHER_BODIES_ONLY`",
    "`GEOMETRY_INTERFERENCE_STATUS = PASS_HELICAL_COIL_VS_OTHER_BODIES_ONLY`",
)

insert = """# 59C. ВИНТОВАЯ ГЕОМЕТРИЯ — 2026-10-03

После этапа 59B во всех трёх итоговых пилотных файлах построен трёхмерный винтовой путь и круглый безвальный виток: наружный диаметр 100 мм, осевой шаг 100 мм, круглый профиль диаметром 30 мм, наклон оси 30°. Это **геометрическая пилотная аппроксимация**, не плоское винтовое перо и не рассчитанный транспортёр песка. Проверочная сплошная огибающая `SCREW_OUTER_ENVELOPE_D100` подавлена в выбранной конфигурации каждого файла. Активные новые элементы: `SHAFTLESS_HELIX_PATH_P100` и `SHAFTLESS_ROUND_COIL_D100_P100`.

| Конфигурация | Точек винтового пути | Rebuild | Ошибки/предупреждения элементов | Твёрдых тел | Пересечения витка с остальными телами |
|---|---:|---|---|---:|---:|
| BASE_700x900 | 195 | PASS | 0 / 0 | 7 | 0 м³ |
| NARROW_600x1050 | 223 | PASS | 0 / 0 | 7 | 0 м³ |
| SHORT_WIDE_800x800 | 177 | PASS | 0 / 0 | 7 | 0 м³ |

Проверено `IBody2.Operations2(SWBODYINTERSECT)` для витка против корпуса/рамы, экрана, перегородок и кожуха. Остаются `UNKNOWN`: способность такого круглого витка транспортировать расчётную массу песка, момент/мощность привода, износ и конструкция выемного вкладыша. Плоское рабочее перо, привод, разгрузочная горловина и герметизация не созданы.

`manufacturing_approved = false`

---

"""
if "# 59C. ВИНТОВАЯ ГЕОМЕТРИЯ" not in text:
    text = text.replace("# 60. ТОЧКА ЗАВЕРШЕНИЯ ТЕКУЩЕЙ РАБОТЫ", insert + "# 60. ТОЧКА ЗАВЕРШЕНИЯ ТЕКУЩЕЙ РАБОТЫ")
out.write_text(text, encoding="utf-8")
src.write_text(text, encoding="utf-8")
print("updated", text.count("# 59C."))
