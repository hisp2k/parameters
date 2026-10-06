from pathlib import Path
import re
import shutil

source = Path(r"C:\Users\adm\.codex\attachments\b8cd7552-32be-41e2-9e27-1bca6330df68\Вставленный текст.txt")
output = Path(r"C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\Песколовка\GRIT_CHAMBER_CODEX_TASK.md")
backup = Path(r"C:\Users\adm\Documents\Codex\2026-10-03\new-chat\work\GRIT_CHAMBER_CODEX_TASK_before_current_run.md")
shutil.copy2(output, backup)
text = output.read_text(encoding="utf-8")

text = text.replace("`FLOW_SIMULATION_AVAILABLE = ADDIN_LOADED_CFD_NOT_TESTED`", "`FLOW_SIMULATION_AVAILABLE = ADDIN_AND_COM_API_VERIFIED_PROJECT_NOT_CREATED`")
text = text.replace("`PARTICLE_STUDY_AVAILABLE = UNKNOWN`", "`PARTICLE_STUDY_AVAILABLE = API_INTERFACE_FOUND_STUDY_NOT_RUN`")

phase_b = """# 22. PHASE B — СОЗДАНИЕ CAD

Выполнено в новых файлах пилотной модели:

- [x] создать новый проект;
- [x] создать MASTER/Skeleton: 25 глобальных переменных и три конфигурации;
- [x] построить ванну 2 мм;
- [x] построить два поперечных уклона пескосборной зоны;
- [x] создать входное отверстие Ø100 мм;
- [x] создать входной гаситель;
- [x] создать распределительный экран Ø22 мм с проверенным числом отверстий;
- [x] создать выходную погружную перегородку;
- [x] создать переливную стенку и выходной проём шириной 600 мм;
- [ ] создать полноценный сменный желоб шнека;
- [x] создать ось 30°, наружную огибающую шнека Ø100 мм и трубчатый кожух ID110/OD120 мм;
- [ ] создать реальную винтовую лопасть безвального шнека;
- [ ] создать разгрузочную горловину, уплотнения, привод и сервисный доступ;
- [x] создать пилотную раму: 4 стойки, продольные и поперечные балки, 4 опорные площадки;
- [x] создать три конфигурации MASTER; детальная геометрия сохранена в отдельных производных файлах для каждого выбранного размера.

Внутренние элементы производных файлов построены по размерам соответствующей конфигурации, но не связаны уравнениями с переменными MASTER. Переключение конфигурации внутри одного производного файла не является проверенным способом получить другой детальный вариант. Полноценная параметрическая сборка остаётся `NOT_CREATED`.
"""
text = re.sub(r"# 22\. PHASE B — СОЗДАНИЕ CAD\n.*?(?=\n---\n\n# 23\.)", phase_b.rstrip(), text, flags=re.S)

text = text.replace("PASS для текущей геометрии", "PASS для выбранной конфигурации пилотного CAD")

geom = """# 24. ГЕОМЕТРИЧЕСКИЕ ПРОВЕРКИ

## GEOMETRY VALIDATION RESULTS — 2026-10-03

`STATUS = PARTIAL_PASS_PILOT_GEOMETRY`

Каждый из трёх итоговых производных файлов открыт повторно, перестроен и сохранён с `Save3`: коды ошибок и предупреждений элементов равны 0. Экран имеет соответственно 255, 210 и 285 отверстий Ø22 мм; подтверждено количеством сегментов эскиза 259/214/289 и количеством граней экранного тела 261/216/291. Поперечные экраны находятся при X=0.125 и 0.250 м, выходная перегородка при X=L_BATH−0.22 м. Два уклона направлены к центральной зоне шириной 140 мм.

Объёмные пересечения наружной огибающей шнека с остальными телами проверены операцией `IBody2.Operations2(SWBODYINTERSECT)` в каждой выбранной конфигурации: 0 пересечений, суммарный объём 0 м³. Проход Ø120 мм вырезан через выходную перегородку и переливную стенку; установлен отдельный трубчатый кожух ID110/OD120 мм. Это не подтверждает герметичность стыков, зазоры при вращении, прочность, доступность демонтажа и работу реального винтового пера.

Незакрытые проверки: фактический свободный борт при течении, геометрия и доступность желоба, уплотнения и привод, анкеровка рамы, нагрузка на листовой корпус, внешние присоединения, коллизии реальной винтовой лопасти, герметичность для CFD. Производственные чертежи и сборка не создавались.
"""
text = re.sub(r"# 24\. ГЕОМЕТРИЧЕСКИЕ ПРОВЕРКИ\n.*?(?=\n---\n\n# 25\.)", geom.rstrip(), text, flags=re.S)

hyd_extra = """
### Геометрия распределительного экрана пилотного CAD

Отверстия имеют диаметр 22 мм, 15 рядов. Доля свободного сечения рассчитана относительно погруженной части экрана шириной `B−0.06` и высотой `0.55−0.002` м; это **геометрическая**, а не гидродинамическая величина.

| Конфигурация | Отверстий | Открытая площадь, м² | Доля, % | Q/открытая площадь, м/с |
|---|---:|---:|---:|---:|
| BASE_700x900 | 255 | 0.096934 | 27.64 | 0.06190 |
| NARROW_600x1050 | 210 | 0.079828 | 26.98 | 0.07516 |
| SHORT_WIDE_800x800 | 285 | 0.108338 | 26.72 | 0.05538 |

Переливной проём имеет геометрическую ширину 0.600 м и нижнюю кромку на высоте 0.550 м. Без решения свободной поверхности нельзя определить действительную скорость через него, уровень воды, время пребывания и эффективность улавливания. Пилотные уклоны занимают часть номинального объёма, поэтому значения `V_WORK` и `T_THEORETICAL` выше остаются расчётом **исходной прямоугольной зоны**, а не измерением готовой модели.
"""
needle = "Контроль исходных значений раздела 6 пройден **только арифметически**: `A = 0.630 m²`, `V = 0.3465 m³`, `T = 57.75 s ≈ 57.8 s`."
text = text.replace(needle, needle + "\n" + hyd_extra.rstrip())

text = text.replace("- `SCREEN_HOLE_COUNT_AND_OPEN_AREA`\n", "")
text = text.replace("- `OUTLET_BAFFLE_CLEARANCE`\n", "")
text = text.replace("- `FLOW_SIMULATION_LICENSE_AND_API_ACCESS`", "- `FLOW_SIMULATION_SOLVER_LICENSE`\n- `DOWNSTREAM_BOUNDARY_CONDITION`\n- `SCREW_FLIGHT_THICKNESS_AND_FORM`\n- `SCREW_CASING_END_SEALS`\n- `FRAME_ANCHOR_DETAILS`\n- `REAL_WASTEWATER_PROPERTIES`\n- `FLOW_SIMULATION_LICENSE_AND_API_ACCESS`")
text = text.replace("- `FLOW_SIMULATION_ACCESS = ADDIN_LOADED`: надстройка уже загружена, `LoadAddIn` вернул 2 (`swAddinAlreadyLoaded`); создание CFD-проекта и наличие расчётной лицензии ещё не проверены.", "- `FLOW_SIMULATION_ACCESS = ADDIN_AND_COM_API_VERIFIED`: `FloWorks.App.GetAPI()` вернул `IAppApi`, активный документ доступен как `IDocumentApi`; создание CFD-проекта и расчётная лицензия не проверены.")
text = text.replace("- `PARTICLE_STUDY_ACCESS = UNKNOWN`: запуск и API Particle Study ещё не проверены.", "- `PARTICLE_STUDY_ACCESS = API_INTERFACE_FOUND_NOT_RUN`: установленная типобиблиотека содержит `ITracerStudyAPI`; исследование и Solver не запускались.")

cad_dir = r"C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD"
for number, name, file in [
    (49, "BASE_700x900", "GRIT_PILOT_BASE_CAD_20261003.SLDPRT"),
    (50, "NARROW_600x1050", "GRIT_PILOT_NARROW_CAD_20261003.SLDPRT"),
    (51, "SHORT_WIDE_800x800", "GRIT_PILOT_SHORT_WIDE_CAD_20261003.SLDPRT"),
]:
    heading = f"# {number}. CFD RECORD — {name}"
    start = text.index(heading)
    end = text.index("\n---", start)
    block = text[start:end]
    block = block.replace("`STATUS = NOT_RUN_GEOMETRY_INCOMPLETE`", "`STATUS = NOT_RUN_PILOT_CAD_AND_BC_INCOMPLETE`")
    block = block.replace("`CAD_FILE = NOT_AVAILABLE_NO_CFD_RUN`", f"`CAD_FILE = {cad_dir}\\{file}`")
    text = text[:start] + block + text[end:]

registry = f"""# 57. ФИНАЛЬНЫЙ РЕЕСТР ФАЙЛОВ

| Type | File | Full path | Status |
|---|---|---|---|
| MASTER | GRIT_MASTER_V10_20261003.SLDPRT | {cad_dir}\\GRIT_MASTER_V10_20261003.SLDPRT | SAVED; 3 CONFIGURATIONS; PARAMETRIC BATH |
| Pilot BASE | GRIT_PILOT_BASE_CAD_20261003.SLDPRT | {cad_dir}\\GRIT_PILOT_BASE_CAD_20261003.SLDPRT | SAVED; SELECTED CONFIG REBUILD PASS; PARTIAL CAD |
| Pilot NARROW | GRIT_PILOT_NARROW_CAD_20261003.SLDPRT | {cad_dir}\\GRIT_PILOT_NARROW_CAD_20261003.SLDPRT | SAVED; SELECTED CONFIG REBUILD PASS; PARTIAL CAD |
| Pilot SHORT_WIDE | GRIT_PILOT_SHORT_WIDE_CAD_20261003.SLDPRT | {cad_dir}\\GRIT_PILOT_SHORT_WIDE_CAD_20261003.SLDPRT | SAVED; SELECTED CONFIG REBUILD PASS; PARTIAL CAD |
| Assembly | NOT_CREATED | — | NOT_STARTED |
| BASE/NARROW/SHORT_WIDE CFD | NOT_CREATED | — | NOT_RUN |
| Particle Study | NOT_CREATED | — | NOT_RUN |
| Preview | GRIT_PILOT_BASE_preview.png | C:\\Users\\adm\\Documents\\Codex\\2026-10-03\\new-chat\\outputs\\grit_chamber\\03_Результаты\\GRIT_PILOT_BASE_preview.png | SAVED SOLIDWORKS VIEW; NOT CFD RESULT |
| Report | GRIT_CHAMBER_CODEX_TASK.md | C:\\Users\\adm\\Documents\\Codex\\2026-10-03\\new-chat\\outputs\\Песколовка\\GRIT_CHAMBER_CODEX_TASK.md | UPDATED |
"""
text = re.sub(r"# 57\. ФИНАЛЬНЫЙ РЕЕСТР ФАЙЛОВ\n.*?(?=\n---\n\n# 58\.)", lambda _: registry.rstrip(), text, flags=re.S)

final_status = """# 58. ФИНАЛЬНЫЙ СТАТУС

`CAD_STATUS = PILOT_PARTIAL_BATH_INTERNALS_FRAME_CASING_ENVELOPE`

`CONFIGURATION_STATUS = MASTER_3_CONFIGS_DERIVATIVE_CAD_PER_SELECTED_CONFIG`

`REBUILD_STATUS = PASS_SELECTED_CONFIG_OF_3_PILOT_FILES`

`GEOMETRY_INTERFERENCE_STATUS = PASS_SCREW_ENVELOPE_VS_OTHER_BODIES_ONLY`

`ANALYTICAL_CALC_STATUS = COMPLETED_PRELIMINARY`

`FLOW_SIMULATION_STATUS = NOT_RUN_CFD_PROJECT_NOT_CREATED`

`PARTICLE_STUDY_STATUS = NOT_RUN_NO_CFD`

`OPTIMIZATION_STATUS = NOT_RUN_NO_CFD_RESULT`

`manufacturing_approved = false`
"""
text = re.sub(r"# 58\. ФИНАЛЬНЫЙ СТАТУС\n.*?(?=\n---\n\n# 59\.)", final_status.rstrip(), text, flags=re.S)

new_log = f"""# 59B. ЖУРНАЛ ПРОДОЛЖЕНИЯ ПРОЕКТИРОВАНИЯ — 2026-10-03

Источник: исходный `GRIT_MASTER_V10_20261003.SLDPRT`; существующие пользовательские CAD/PDM не изменялись. SOLIDWORKS Design Premium 2026 SP3.2, типизированный C# COM interop.

**Важная исправленная ошибка.** В первых производных пробах оси модели были интерпретированы неправильно, а при добавлении окружностей через `SketchManager.CreateCircleByRadius` без `AddToDB=true` фактически создавалась только часть отверстий. Пробные файлы `GRIT_DETAIL_*`, `GRIT_PILOT_*_V2/V5/V6`, `GRIT_*_TEST` не считать результатом. Оси проверены по `IBody2.GetBodyBox` с инвариантным десятичным форматом: X — длина ванны, Y — высота, Z — ширина от −B до 0. Итоговые файлы построены заново от MASTER, включено `AddToDB=true`, количество отверстий проверено после сохранения.

Итоговые выбранные конфигурации:

| CAD-файл | B×L, м | Отверстий Ø22 | Открытая площадь, м² | Rebuild | Ошибки элементов | Предупреждения | Твёрдых тел | Пересечения огибающей шнека |
|---|---|---:|---:|---|---:|---:|---:|---:|
| `GRIT_PILOT_BASE_CAD_20261003.SLDPRT` | 0.70×1.35 | 255 | 0.096934 | PASS | 0 | 0 | 7 | 0 |
| `GRIT_PILOT_NARROW_CAD_20261003.SLDPRT` | 0.60×1.50 | 210 | 0.079828 | PASS | 0 | 0 | 7 | 0 |
| `GRIT_PILOT_SHORT_WIDE_CAD_20261003.SLDPRT` | 0.80×1.25 | 285 | 0.108338 | PASS | 0 | 0 | 7 | 0 |

В каждом производном файле: корпус 2 мм; входное отверстие Ø100 мм на высоте 0.42 м; входной экран X=0.125 м; распределительный экран X=0.250 м с неперфорированной нижней зоной 114 мм; выходная погружная перегородка; переливная стенка высотой 0.55 м и выходной проём 600 мм; два пескосборных уклона в поперечном сечении; опорная рама высотой 0.50 м со стойками 40×40 мм, продольными и поперечными балками и площадками 100×100 мм; ось под 30°; отверстия прохода Ø120 мм; отдельный трубчатый кожух ID110/OD120 мм; твёрдая огибающая шнека Ø100 мм. Винтовое перо шнека, разгрузочная горловина, привод, уплотнения, сервисный доступ и отдельная сборка **не выполнены**. Твёрдая огибающая является только проверочным объёмом, не работающим шнеком.

Проверка `Operations2(SWBODYINTERSECT)` по всем трём выбранным конфигурациям: пересечение тела огибающей шнека с корпусом, экранами, перегородкой, переливом и кожухом равно 0 м³. Герметичность соединения кожуха с перегородками этим не доказана. Прочность корпуса и рамы не рассчитывалась.

Flow Simulation: надстройка загружена, COM-объект `FloWorks.App.GetAPI()` вернул `IAppApi`, `IActiveDoc` вернул `IDocumentApi`, `IsDemoVersion() = false`; в установленной `floworks.tlb` присутствуют `IProjectApiHandler`, `ITracerStudyAPI`, методы создания проекта и запуска Solver. Это подтверждает доступность API, **не** подтверждает наличие расчётной лицензии или пригодность текущей геометрии/граничных условий. CFD-проект не создан; Solver, сетка и Particle Study не запускались. Эффективность `ETA_0_20` остаётся `UNKNOWN`, целевой критерий 70% не подтверждён.

Оставшиеся инженерные задачи перед CFD: выбрать схему отвода и нижний уровень воды; закрыть/описать границы свободной поверхности; согласовать действительный проход DN100 и сброс; задать уплотнения кожуха, реальную винтовую геометрию и желоб; проверить прочность и технологичность. Затем настроить Flow Simulation, выполнить MEDIUM/FINE, массовый баланс и Particle Study для всех трёх размеров.

`manufacturing_approved = false`

---

"""
text = text.replace("# 60. ТОЧКА ЗАВЕРШЕНИЯ ТЕКУЩЕЙ РАБОТЫ", new_log + "# 60. ТОЧКА ЗАВЕРШЕНИЯ ТЕКУЩЕЙ РАБОТЫ")

output.write_text(text, encoding="utf-8")
source.write_text(text, encoding="utf-8")
print(output)
print(source)
