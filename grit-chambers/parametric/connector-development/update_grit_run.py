from pathlib import Path

task = Path(r"C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\Песколовка\GRIT_CHAMBER_CODEX_TASK.md")
cad = Path(r"C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD\GRIT_MASTER_V10_20261003.SLDPRT")
text = task.read_text(encoding="utf-8-sig")

text = text.replace("`FLOW_SIMULATION_AVAILABLE = UNKNOWN`", "`FLOW_SIMULATION_AVAILABLE = ADDIN_LOADED_CFD_NOT_TESTED`", 1)
text = text.replace("`WRITE_TOOLS = AVAILABLE_VIA_TYPED_COM_API_NOT_EXECUTED`", "`WRITE_TOOLS = VERIFIED_TYPED_COM_API`", 1)
text = text.replace("Методы создания и сохранения документа доступны в интерфейсе, но операции записи ещё не выполнялись. Flow Simulation и Particle Study остаются непроверенными.", "Методы создания, сохранения, построения элементов и полного перестроения проверены на новых файлах проекта. Надстройка Flow Simulation загружена (`LoadAddIn = 2`, уже загружена), но создание CFD-проекта и Particle Study не проверены.")

for old, new in [
    ("- [ ] создать новый проект;", "- [x] создать новый проект;"),
    ("- [ ] создать MASTER/Skeleton;", "- [x] создать MASTER/Skeleton (первый этап: 25 переменных, параметрический контур и корпус);"),
    ("- [ ] построить ванну;", "- [x] построить ванну (прямоугольный открытый корпус с толщиной 2 мм; днище пескосборной зоны ещё не создано);"),
    ("- [ ] создать три конфигурации.", "- [x] создать три конфигурации (размеры основания перестраиваются)."),
]:
    text = text.replace(old, new, 1)

text = text.replace("| BASE_700x900 | NOT_RUN | CAD не создана | — |", "| BASE_700x900 | PASS для текущей геометрии | 0 | 0 |", 1)
text = text.replace("| NARROW_600x1050 | NOT_RUN | CAD не создана | — |", "| NARROW_600x1050 | PASS для текущей геометрии | 0 | 0 |", 1)
text = text.replace("| SHORT_WIDE_800x800 | NOT_RUN | CAD не создана | — |", "| SHORT_WIDE_800x800 | PASS для текущей геометрии | 0 | 0 |", 1)
text = text.replace("Причина: геометрия CAD ещё не создана; доступ к API восстановлен только на этапе проверки соединения. Визуальная или аналитическая проверка геометрии не подменяет проверку твёрдых тел.", "Проверена только построенная часть: у каждой конфигурации одно твёрдое тело; `MASTER_FOOTPRINT`, `BATH_BASE_PLATE` и `BATH_SHELL_2MM` имеют код ошибки 0 и не имеют предупреждений. Оболочка имеет толщину 0.002 м и одну удалённую верхнюю грань. Пересечения с ещё не построенными узлами, зазор шнека, положение экранов, уровень воды и сервисные зоны `NOT_RUN`.")
text = text.replace("## GEOMETRY VALIDATION RESULTS\n\n`STATUS = NOT_RUN`", "## GEOMETRY VALIDATION RESULTS\n\n`STATUS = PARTIAL_PASS_BUILT_GEOMETRY_ONLY`", 1)

text = text.replace("- `FLOW_SIMULATION_ACCESS = UNKNOWN`: модуль ещё не проверен через восстановленное API.", "- `FLOW_SIMULATION_ACCESS = ADDIN_LOADED`: надстройка уже загружена, `LoadAddIn` вернул 2 (`swAddinAlreadyLoaded`); создание CFD-проекта и наличие расчётной лицензии ещё не проверены.")
text = text.replace("- `PARTICLE_STUDY_ACCESS = UNKNOWN`: ещё не проверен через восстановленное API.", "- `PARTICLE_STUDY_ACCESS = UNKNOWN`: запуск и API Particle Study ещё не проверены.")
text = text.replace("| MASTER | NOT_CREATED | — | NOT_STARTED |", f"| MASTER | {cad.name} | {cad} | SAVED; 3 CONFIGURATIONS; PARTIAL CAD |")
text = text.replace("`CAD_STATUS = NOT_STARTED_API_RECONNECTED`", "`CAD_STATUS = PARTIAL_BATH_ONLY`")
text = text.replace("`CONFIGURATION_STATUS = NOT_STARTED`", "`CONFIGURATION_STATUS = PASS_MASTER_BATH_ONLY`")
text = text.replace("`REBUILD_STATUS = NOT_RUN`", "`REBUILD_STATUS = PASS_CURRENT_GEOMETRY_ALL_3`")
text = text.replace("`FLOW_SIMULATION_STATUS = NOT_RUN_ACCESS_UNKNOWN`", "`FLOW_SIMULATION_STATUS = NOT_RUN_GEOMETRY_INCOMPLETE`")
text = text.replace("`PARTICLE_STUDY_STATUS = NOT_RUN_ACCESS_UNKNOWN`", "`PARTICLE_STUDY_STATUS = NOT_RUN_NO_CFD`")

run_record = f"""# 59A. ЖУРНАЛ ПОВТОРНОГО ЗАПУСКА — 2026-10-03

- SOLIDWORKS Design Premium 2026 SP3.2 подключён через типизированный C# COM interop (`RevisionNumber = 34.3.2`).
- Новый рабочий файл: `{cad}`. Существующие пользовательские SLDPRT/SLDASM/SLDDRW не изменялись.
- Созданы 25 глобальных переменных `AI_*` по разделу 9. Числовые значения длин заданы в единицах документа — мм; эскиз и оболочка используют внутренние метры API.
- Созданы конфигурации `BASE_700x900`, `NARROW_600x1050`, `SHORT_WIDE_800x800` в одном мастер-файле.
- `MASTER_FOOTPRINT`: прямоугольник с уравнениями `D1 = AI_L_Bath`, `D2 = AI_B_Bath`. `BATH_BASE_PLATE` вытянут на `AI_H_Bath`; `BATH_SHELL_2MM` удаляет верхнюю грань и создаёт стенки толщиной 2 мм.

| Configuration | AI_B_Bath, mm | AI_L_Settle, mm | AI_L_Bath, mm | Actual footprint B × L, m | Actual H, m | Rebuild | Feature errors | Feature warnings |
|---|---:|---:|---:|---|---:|---|---:|---:|
| BASE_700x900 | 700 | 900 | 1350 | 0.70 × 1.35 | 0.75 | PASS | 0 | 0 |
| NARROW_600x1050 | 600 | 1050 | 1500 | 0.60 × 1.50 | 0.75 | PASS | 0 | 0 |
| SHORT_WIDE_800x800 | 800 | 800 | 1250 | 0.80 × 1.25 | 0.75 | PASS | 0 | 0 |

Текущий файл содержит **только открытый прямоугольный корпус**. Вход, гаситель, распределительный экран, выходная перегородка, перелив, пескосборное днище, шнек, выгрузка, рама и сборка не созданы. `CAD_STATUS = PARTIAL_BATH_ONLY`.

Надстройка Flow Simulation зарегистрирована в SOLIDWORKS и уже загружена (`LoadAddIn = 2`, [коды API](https://help.solidworks.com/2026/english/api/swconst/SolidWorks.Interop.swconst~SolidWorks.Interop.swconst.swLoadAddinError_e.html)). CFD-проект, сетка, Solver и Particle Study **не запускались**.

Ошибки повторного запуска: первый файл в каталоге с кириллическим именем не удалось повторно сохранить (`swGenericSaveError = 1`); он не выбран итоговым. При попытке изменить несколько конфигураций через устаревшую ссылку EquationMgr возник `RPC_E_SERVERFAULT`, после чего SOLIDWORKS был повторно запущен. Значения конфигураций затем изменены последовательно с новым объектом EquationMgr и проверены перестроением. Промежуточные версии `V2`–`V9` не являются итоговыми CAD-моделями.

---

"""
text = text.replace("# 60. ТОЧКА ЗАВЕРШЕНИЯ ТЕКУЩЕЙ РАБОТЫ", run_record + "# 60. ТОЧКА ЗАВЕРШЕНИЯ ТЕКУЩЕЙ РАБОТЫ")

task.write_text(text, encoding="utf-8")
Path(r"C:\Users\adm\.codex\attachments\b8cd7552-32be-41e2-9e27-1bca6330df68\Вставленный текст.txt").write_text(text, encoding="utf-8")
