from pathlib import Path

path = Path(r"C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\Песколовка\GRIT_CHAMBER_CODEX_TASK.md")
text = path.read_text(encoding="utf-8")

text = text.replace(
    "`STATUS = NOT_STARTED`\n\n`SOLIDWORKS_CONNECTED = UNKNOWN`\n\n`ACTIVE_DOCUMENT = UNKNOWN`\n\n`WRITE_TOOLS = UNKNOWN`\n\n`FLOW_SIMULATION_AVAILABLE = UNKNOWN`\n\n`PARTICLE_STUDY_AVAILABLE = UNKNOWN`",
    "`STATUS = BLOCKED`\n\n`SOLIDWORKS_CONNECTED = false`\n\n`ACTIVE_DOCUMENT = NONE_OBSERVED`\n\n`WRITE_TOOLS = NONE_EXPOSED`\n\n`FLOW_SIMULATION_AVAILABLE = UNKNOWN`\n\n`PARTICLE_STUDY_AVAILABLE = UNKNOWN`\n\nПроверка 2026-10-03: среди доступных инструментов текущей сессии нет SolidWorks-коннектора. Локально установлен `C:\\Program Files\\SOLIDWORKS Corp\\SOLIDWORKS\\sldworks.exe` и зарегистрирован COM ProgID `SldWorks.Application` (SOLIDWORKS 2026). Создание COM-объекта запускает процесс, однако вызовы `RevisionNumber()` и `Visible` завершаются `TYPE_E_ELEMENTNOTFOUND (0x8002802B)` и в PowerShell 7, и в Windows PowerShell 5.1. Поэтому управляемое CAD-построение, rebuild и запуск Flow Simulation не подтверждены. Установленный каталог Flow Simulation сам по себе не подтверждает доступность модуля в API или лицензию. Пользовательский документ не открывался и не изменялся."
)

anchor = "# 26. ПРЕДВАРИТЕЛЬНОЕ ОСАЖДЕНИЕ"
hydro = """## ANALYTICAL HYDRAULICS — фактически рассчитано 2026-10-03

Принято: `Q = 0.006 m³/s`, прямоугольная зона шириной `B` и глубиной `H_WATER = 0.55 m`; указанные значения относятся только к идеализированной основной зоне. Для полной ванны с днищем, экранами и шнеком рабочий объём пока неизвестен.

| Конфигурация | A_SETTLE, m² | V_WORK, m³ | T_THEORETICAL, s | Q/A, m/s | Q/(B·H), m/s |
|---|---:|---:|---:|---:|---:|
| BASE_700x900 | 0.630 | 0.3465 | 57.75 | 0.009524 | 0.01558 |
| NARROW_600x1050 | 0.630 | 0.3465 | 57.75 | 0.009524 | 0.01818 |
| SHORT_WIDE_800x800 | 0.640 | 0.3520 | 58.67 | 0.009375 | 0.01364 |

При условном внутреннем диаметре входа ровно 100 мм: `V_INLET = 4Q/(πD²) = 0.764 m/s`. Обозначение DN100 не задаёт фактический внутренний диаметр, поэтому это только ориентир. Удельный расход через перелив шириной 0.6 м: `Q/W = 0.0100 m²/s`; скорость воды на переливе без глубины потока вычислить нельзя. Скорости через распределительный экран и под выходной перегородкой `UNKNOWN`, поскольку их фактические площади и нижний просвет не заданы и CAD не построен.

Контроль исходных значений раздела 6 пройден **только арифметически**: `A = 0.630 m²`, `V = 0.3465 m³`, `T = 57.75 s ≈ 57.8 s`.

---

"""
text = text.replace(anchor, hydro + anchor)

settle = """## SETTLING CALCULATION — фактически рассчитано 2026-10-03

Исходные свойства **чистой воды 20 °C**: `ρ = 998.2 kg/m³`, `μ = 0.001002 Pa·s`; частица принята сферической, `ρp = 2650 kg/m³`, `g = 9.81 m/s²`. Скорость найдена итерационно из баланса веса с учётом плавучести и сопротивления, `Re = ρvd/μ`, `Cd = 24/Re · (1 + 0.15 Re^0.687)` при `Re < 1000`. Формула Стокса без поправки не применялась. Источники модели и свойств: [NIST — свойства жидкостей](https://webbook.nist.gov/chemistry/fluid/), [IAPWS — вязкость воды](https://www.iapws.org/relguide/viscosity.html), [публикация с корреляцией Schiller–Naumann](https://www.cambridge.org/core/journals/journal-of-fluid-mechanics/article/new-paradigm-for-computing-hydrodynamic-forces-on-particles-in-eulerlagrange-pointparticle-simulations/C653BA1C01108A86F99CF0F921931B44).

`Analytical eta = min(100%, v_settle/(Q/A)·100%)` — предельная оценка идеального отстойника по площади, **не прогноз реальной эффективности песколовки**. Турбулентность, короткий путь, форма зерна, промывка и вторичный вынос не учтены.

| d, mm | Re particle | Settling velocity, m/s | Ideal eta BASE/NARROW | Ideal eta SHORT_WIDE |
|---:|---:|---:|---:|---:|
| 0.10 | 0.793 | 0.00797 | 83.6% | 85.0% |
| 0.15 | 2.375 | 0.01590 | 100% | 100% |
| 0.20 | 4.940 | 0.02479 | 100% | 100% |
| 0.30 | 12.922 | 0.04324 | 100% | 100% |
| 0.50 | 39.096 | 0.07849 | 100% | 100% |

`ETA_0_20 >= 70%` фактически **не подтверждена**: Particle Study и CFD не запускались.

---

"""
text = text.replace("# 27. PHASE C — SOLIDWORKS FLOW SIMULATION", settle + "# 27. PHASE C — SOLIDWORKS FLOW SIMULATION")

text = text.replace("## GEOMETRY VALIDATION RESULTS\n\n`STATUS = NOT_RUN`", "## GEOMETRY VALIDATION RESULTS\n\n`STATUS = NOT_RUN`\n\nПричина: геометрия CAD не создана из-за недоступного интерфейса управления SOLIDWORKS. Визуальная или аналитическая проверка геометрии не подменяет проверку твёрдых тел.")
text = text.replace("`NONE_CONFIRMED`\n\nЕсли функция недоступна", "- `CAPABILITY_GAP_SOLIDWORKS_CONNECTOR`: инструмент SolidWorks отсутствует в текущем перечне доступных инструментов.\n- `CAPABILITY_GAP_SOLIDWORKS_COM`: вызов API установленного SOLIDWORKS 2026 завершается `0x8002802B`.\n- `CAPABILITY_GAP_FLOW_SIMULATION_ACCESS`: фактический запуск невозможен через текущий интерфейс; наличие каталога установки не подтверждает доступ к модулю.\n- `CAPABILITY_GAP_PARTICLE_STUDY_ACCESS`: тот же блокирующий доступ к Flow Simulation.\n\nЕсли функция недоступна")
text = text.replace("`CAD_STATUS = NOT_STARTED`", "`CAD_STATUS = BLOCKED_NO_SOLIDWORKS_API`")
text = text.replace("`CONFIGURATION_STATUS = NOT_STARTED`", "`CONFIGURATION_STATUS = NOT_STARTED`")
text = text.replace("`REBUILD_STATUS = NOT_STARTED`", "`REBUILD_STATUS = NOT_RUN`")
text = text.replace("`ANALYTICAL_CALC_STATUS = NOT_STARTED`", "`ANALYTICAL_CALC_STATUS = COMPLETED_PRELIMINARY`")
text = text.replace("`FLOW_SIMULATION_STATUS = NOT_STARTED`", "`FLOW_SIMULATION_STATUS = NOT_RUN_CAPABILITY_GAP`")
text = text.replace("`PARTICLE_STUDY_STATUS = NOT_STARTED`", "`PARTICLE_STUDY_STATUS = NOT_RUN_CAPABILITY_GAP`")
text = text.replace("`OPTIMIZATION_STATUS = NOT_STARTED`", "`OPTIMIZATION_STATUS = NOT_RUN_NO_CFD_RESULT`")
text = text.replace("| MASTER | | | |", "| MASTER | NOT_CREATED | — | BLOCKED |")
text = text.replace("| Assembly | | | |", "| Assembly | NOT_CREATED | — | BLOCKED |")
for name in ["BASE CFD", "NARROW CFD", "SHORT_WIDE CFD", "Images", "Animations"]:
    text = text.replace(f"| {name} | | | |", f"| {name} | NOT_CREATED | — | NOT_RUN |")
text = text.replace("| Reports | | | |", f"| Reports | GRIT_CHAMBER_CODEX_TASK.md | {path} | UPDATED |")
text = text.replace("| BASE_700x900 | NOT_RUN | | |", "| BASE_700x900 | NOT_RUN | CAD не создана | — |")
text = text.replace("| NARROW_600x1050 | NOT_RUN | | |", "| NARROW_600x1050 | NOT_RUN | CAD не создана | — |")
text = text.replace("| SHORT_WIDE_800x800 | NOT_RUN | | |", "| SHORT_WIDE_800x800 | NOT_RUN | CAD не создана | — |")
text = text.replace("- `PARTICLE_WALL_INTERACTION`", "- `PARTICLE_WALL_INTERACTION`\n- `ACTUAL_DN100_INTERNAL_DIAMETER`\n- `SCREEN_HOLE_COUNT_AND_OPEN_AREA`\n- `OUTLET_BAFFLE_CLEARANCE`\n- `SOLIDWORKS_LICENSE_AND_API_HEALTH`\n- `FLOW_SIMULATION_LICENSE_AND_API_ACCESS`")

# The task's final line is kept as required.
path.write_text(text, encoding="utf-8")
