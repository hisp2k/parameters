# GRIT_CHAMBER_CODEX_TASK.md

## Параметрическое проектирование песколовки через Codex + SolidWorks + Flow Simulation

---

# 0. НАЗНАЧЕНИЕ ЭТОГО ФАЙЛА

Этот Markdown-файл является одновременно:

1. техническим заданием для Codex;
2. исполняемым чек-листом;
3. журналом фактически выполненных операций;
4. журналом перестроений SolidWorks;
5. журналом Flow Simulation;
6. журналом Particle Study;
7. итоговым расчётным отчётом;
8. реестром созданных файлов;
9. реестром ошибок и ограничений;
10. точкой продолжения работы в следующих сессиях Codex.

**Codex обязан обновлять именно этот файл по мере выполнения работы.**

Не создавать отдельный текстовый отчёт вместо заполнения этого файла.

После каждого законченного этапа:

- обновлять статус этапа;
- записывать фактический результат;
- сохранять пути созданных файлов;
- фиксировать ошибки;
- фиксировать UNKNOWN;
- фиксировать CAPABILITY_GAP;
- фиксировать фактические результаты расчётов.

Сам файл должен оставаться пригодным для повторного запуска Codex.

---

# 1. ГЛАВНАЯ КОМАНДА CODEX

Используя подключённый SolidWorks-коннектор:

**фактически построить новую параметрическую модель компактной песколовки, выполнить доступные инженерные проверки и SOLIDWORKS Flow Simulation, сохранить созданные модели и результаты симуляции, а затем записать фактические результаты выполнения в этот же Markdown-файл.**

Не ограничиваться:

- рекомендациями;
- описанием действий;
- созданием нового промпта;
- созданием ещё одного TASK.md;
- псевдокодом;
- расчётом без построения модели.

Если операция поддерживается коннектором — выполнить её.

---

# 2. РАБОЧИЙ РЕЖИМ

Использовать:

`Codex -> SolidWorks Connector -> New Workspace Files`

Существующие пользовательские файлы не изменять.

Не изменять:

- существующие SLDPRT;
- существующие SLDASM;
- существующие SLDDRW;
- PDM;
- производственные проекты;
- активный пользовательский документ.

Создавать только новые файлы в отдельной рабочей папке проекта песколовки.

---

# 3. СТАТУС ПРОЕКТА

Текущий статус:

`DESIGN / PILOT`

Производственный статус:

`manufacturing_approved = false`

Не менять на `true` без отдельной команды пользователя.

---

# 4. ИСХОДНЫЕ ДАННЫЕ

## 4.1 Расход

Пиковый расход:

`Q_PEAK = 0.006 m3/s`

или:

`Q_PEAK = 6 l/s`

Исходное условие:

`60 литров за 10 секунд`

Суточное поступление:

`до 10 m3/day`

---

## 4.2 Среда

Базовая среда:

`сточная вода`

Для первого расчёта свойств жидкости принять:

`вода 20 °C`

Если фактические свойства сточной воды неизвестны:

`WASTEWATER_PROPERTIES = UNKNOWN`

---

## 4.3 Песок

Расчётная плотность минеральной частицы:

`RHO_PARTICLE = 2650 kg/m3`

Целевая фракция:

`D_TARGET = 0.20 mm`

Дополнительно проверить:

- 0.10 мм;
- 0.15 мм;
- 0.20 мм;
- 0.30 мм;
- 0.50 мм.

Целевая расчётная эффективность:

`ETA_0_20 >= 70 %`

---

# 5. БАЗОВАЯ ГЕОМЕТРИЯ

Базовая конфигурация:

`BASE_700x900`

Параметры:

`B_BATH = 700 mm`

`L_SETTLE = 900 mm`

`L_INLET = 250 mm`

`L_OUTLET = 200 mm`

`L_BATH = 1350 mm`

`H_WATER = 550 mm`

`H_FREEBOARD = 200 mm`

`H_BATH = 750 mm`

`W_WEIR = 600 mm`

Вход:

`DN100`

---

# 6. КОНТРОЛЬНЫЕ ЗНАЧЕНИЯ

Площадь осаждения:

`A_SETTLE = 0.700 x 0.900 = 0.630 m2`

Рабочий объём:

`V_SETTLE = 0.630 x 0.550 = 0.3465 m3`

Расчётное время пребывания при пиковом расходе:

`T_PEAK ~= 57.8 s`

После построения модели сравнить фактические расчётные параметры с этими значениями.

---

# 7. ТРИ ОБЯЗАТЕЛЬНЫЕ КОНФИГУРАЦИИ

## CONFIG_01

`BASE_700x900`

- B = 700 мм
- L_SETTLE = 900 мм
- A ~= 0.630 м²

## CONFIG_02

`NARROW_600x1050`

- B = 600 мм
- L_SETTLE = 1050 мм
- A ~= 0.630 м²

## CONFIG_03

`SHORT_WIDE_800x800`

- B = 800 мм
- L_SETTLE = 800 мм
- A ~= 0.640 м²

Все три конфигурации должны использовать один MASTER/Skeleton.

---

# 8. АРХИТЕКТУРА ПАРАМЕТРИЧЕСКОЙ МОДЕЛИ

Использовать:

`INPUTS`

→ `CALC`

→ `MASTER/SKELETON`

→ `BATH`

→ `INLET`

→ `HYDRAULIC BAFFLES`

→ `SEDIMENT ZONE`

→ `SCREW TROUGH`

→ `SCREW`

→ `DISCHARGE`

→ `FRAME`

→ `CONFIGURATIONS`

→ `VALIDATION`

→ `FLOW SIMULATION`

Не допускать циклических зависимостей.

Локальная геометрия не должна управлять MASTER.

---

# 9. ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ

Создать минимум:

`AI_Q_Peak`

`AI_B_Bath`

`AI_L_Settle`

`AI_L_Inlet`

`AI_L_Outlet`

`AI_L_Bath`

`AI_H_Water`

`AI_H_Freeboard`

`AI_H_Bath`

`AI_Shell_Thickness`

`AI_Inlet_DN`

`AI_Weir_Width`

`AI_Inlet_Baffle_Offset`

`AI_Distributor_Open_Area`

`AI_Distributor_Hole_Dia`

`AI_Distributor_Blind_Zone`

`AI_Outlet_Baffle_Depth`

`AI_Screw_Diameter`

`AI_Screw_Pitch`

`AI_Screw_Angle`

`AI_Screw_Rpm`

`AI_Screw_Clearance`

`AI_Liner_Thickness`

`AI_Discharge_Height`

`AI_Frame_Height`

При необходимости добавлять другие параметры с понятными именами.

---

# 10. МАТЕРИАЛ

Базовый корпус:

`AISI 304`

Толщина корпуса:

`2.0 mm`

Крышки:

`1.5-2.0 mm`

Толщина должна оставаться параметром.

---

# 11. ВХОД

Вход:

`DN100`

Струя не должна быть направлена:

- непосредственно в пескосборную зону;
- непосредственно на шнек;
- вдоль дна;
- прямо на перелив.

---

# 12. ВХОДНОЙ ГАСИТЕЛЬ

Создать экран/гаситель после входного патрубка.

Исходный диапазон:

`100-150 mm`

от входа.

Положение параметризовать.

---

# 13. РАСПРЕДЕЛИТЕЛЬНЫЙ ЭКРАН

Исходное положение:

приблизительно после входной зоны.

Начальный ориентир:

`X ~= 250 mm`

Экран на всю рабочую ширину.

Диаметр отверстий:

`20-25 mm`

Свободное сечение:

`25-30 %`

Нижняя неперфорированная зона:

`100-120 mm`

Рассчитывать автоматически:

- количество отверстий;
- шаг;
- свободное сечение;
- число рядов;
- число колонок.

---

# 14. ВЫХОДНАЯ ПЕРЕГОРОДКА

Перед переливом создать погружную перегородку.

Цель:

- уменьшить короткое замыкание потока;
- уменьшить вынос песка;
- сформировать равномерный выходной поток.

Глубина:

`AI_Outlet_Baffle_Depth`

---

# 15. ПЕСКОСБОРНАЯ ЗОНА

Днище должно направлять осадок к шнеку.

Не создавать:

- обратных уклонов;
- закрытых карманов;
- горизонтальных зон накопления;
- зон, недоступных для очистки.

---

# 16. ШНЕК

Использовать:

`D_SCREW = 100 mm`

`P_SCREW = 100 mm`

`ALPHA_SCREW = 30 deg`

Допустимый диапазон:

`28-32 deg`

Номинальная скорость:

`N_SCREW = 15 rpm`

Рабочий диапазон:

`10-20 rpm`

Базовый привод:

`0.75 kW`

с частотным регулированием.

Основная версия:

`shaftless screw`

Привод:

`верхний`

---

# 17. БЕЗВАЛЬНЫЙ ШНЕК

Не устанавливать нижний погружной подшипник.

Создать:

- желоб;
- сменный износостойкий вкладыш;
- рабочий зазор;
- зону демонтажа;
- переход к сухой части;
- выгрузочную горловину.

---

# 18. ГЕОМЕТРИЯ ШНЕКА

Если коннектор поддерживает:

- Helix/Spiral;
- Sweep;
- управляемую винтовую геометрию;

создать реальный шнек.

Если нет:

зафиксировать:

`CAPABILITY_GAP_SCREW_GEOMETRY`

и создать минимум:

- ось;
- наружную огибающую;
- желоб;
- технологический зазор;
- интерфейс привода;
- выгрузку.

---

# 19. ВЫГРУЗКА

Создать:

`AI_Discharge_Height`

Выгрузка должна находиться выше уровня воды.

Предусмотреть:

- дренирование;
- переход мокрой части в сухую;
- выгрузочную горловину;
- сервисный доступ.

---

# 20. РАМА

Создать параметрическую опорную раму.

Нагрузка не должна передаваться только через тонкий лист корпуса.

Предусмотреть:

- основные опоры;
- усиления;
- опору привода;
- точки крепления к основанию.

---

# 21. PHASE A — ПРОВЕРКА SOLIDWORKS

Codex обязан сначала записать ниже фактический результат.

## RESULT — SOLIDWORKS CONNECTION

`STATUS = CONNECTED`

`SOLIDWORKS_CONNECTED = true`

`ACTIVE_DOCUMENT = NONE_OBSERVED`

`WRITE_TOOLS = VERIFIED_TYPED_COM_API`

`FLOW_SIMULATION_AVAILABLE = ADDIN_LOADED_CFD_NOT_TESTED`

`PARTICLE_STUDY_AVAILABLE = UNKNOWN`

Проверка 2026-10-03: среди доступных инструментов текущей сессии нет SolidWorks-коннектора. Локально установлен `C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\sldworks.exe` и зарегистрирован COM ProgID `SldWorks.Application` (SOLIDWORKS 2026). Первоначальный динамический вызов COM в PowerShell завершался `TYPE_E_ELEMENTNOTFOUND (0x8002802B)`. Повторное подключение 2026-10-03 выполнено через типизированный интерфейс `SolidWorks.Interop.sldworks.ISldWorks`: фактически получены `RevisionNumber() = 34.3.2`, `ActiveDoc = NONE`, путь шаблона детали `~BLANK_PART_TEMPLATE.prtdot`. Окно SOLIDWORKS Design Premium 2026 SP3.2 запущено. Методы создания, сохранения, построения элементов и полного перестроения проверены на новых файлах проекта. Надстройка Flow Simulation загружена (`LoadAddIn = 2`, уже загружена), но создание CFD-проекта и Particle Study не проверены. Пользовательский документ не открывался и не изменялся.

После проверки заменить UNKNOWN фактическими значениями.

---

# 22. PHASE B — СОЗДАНИЕ CAD

Выполнить:

- [x] создать новый проект;
- [x] создать MASTER/Skeleton (первый этап: 25 переменных, параметрический контур и корпус);
- [x] построить ванну (прямоугольный открытый корпус с толщиной 2 мм; днище пескосборной зоны ещё не создано);
- [ ] построить днище;
- [ ] создать вход;
- [ ] создать гаситель;
- [ ] создать распределительный экран;
- [ ] создать выходную перегородку;
- [ ] создать перелив;
- [ ] создать желоб шнека;
- [ ] создать шнек либо огибающую;
- [ ] создать выгрузку;
- [ ] создать раму;
- [x] создать три конфигурации (размеры основания перестраиваются).

После каждого крупного этапа выполнить rebuild.

---

# 23. REBUILD

По каждой конфигурации выполнить полный rebuild.

Заполнить:

| Configuration | Rebuild | Errors | Warnings |
|---|---|---|---|
| BASE_700x900 | PASS для текущей геометрии | 0 | 0 |
| NARROW_600x1050 | PASS для текущей геометрии | 0 | 0 |
| SHORT_WIDE_800x800 | PASS для текущей геометрии | 0 | 0 |

Допустимые статусы:

`PASS`

`FAIL`

Нельзя записывать PASS без фактического rebuild.

---

# 24. ГЕОМЕТРИЧЕСКИЕ ПРОВЕРКИ

Проверить:

- самопересечения;
- пересечения деталей;
- положение экранов;
- пространство под перегородкой;
- зазор шнека;
- пересечение шнека с корпусом;
- положение выгрузки;
- уровень воды;
- свободный борт;
- доступность сервисных зон.

Результаты записать сюда.

## GEOMETRY VALIDATION RESULTS

`STATUS = PARTIAL_PASS_BUILT_GEOMETRY_ONLY`

Проверена только построенная часть: у каждой конфигурации одно твёрдое тело; `MASTER_FOOTPRINT`, `BATH_BASE_PLATE` и `BATH_SHELL_2MM` имеют код ошибки 0 и не имеют предупреждений. Оболочка имеет толщину 0.002 м и одну удалённую верхнюю грань. Пересечения с ещё не построенными узлами, зазор шнека, положение экранов, уровень воды и сервисные зоны `NOT_RUN`.

---

# 25. АНАЛИТИЧЕСКАЯ ГИДРАВЛИКА

Для каждой конфигурации рассчитать:

`A_SETTLE`

`V_WORK`

`T_THEORETICAL`

`Q/A`

Среднюю скорость в основной зоне.

Скорость:

- на входе;
- через распределительный экран;
- под выходной перегородкой;
- на переливе.

---

## ANALYTICAL HYDRAULICS — фактически рассчитано 2026-10-03

Принято: `Q = 0.006 m³/s`, прямоугольная зона шириной `B` и глубиной `H_WATER = 0.55 m`; указанные значения относятся только к идеализированной основной зоне. Для полной ванны с днищем, экранами и шнеком рабочий объём пока неизвестен.

| Конфигурация | A_SETTLE, m² | V_WORK, m³ | T_THEORETICAL, s | Q/A, m/s | Q/(B·H), m/s |
|---|---:|---:|---:|---:|---:|
| BASE_700x900 | 0.630 | 0.3465 | 57.75 | 0.009524 | 0.01558 |
| NARROW_600x1050 | 0.630 | 0.3465 | 57.75 | 0.009524 | 0.01818 |
| SHORT_WIDE_800x800 | 0.640 | 0.3520 | 58.67 | 0.009375 | 0.01364 |

При условном внутреннем диаметре входа ровно 100 мм: `V_INLET = 4Q/(πD²) = 0.764 m/s`. Обозначение DN100 не задаёт фактический внутренний диаметр, поэтому это только ориентир. Удельный расход через перелив шириной 0.6 м: `Q/W = 0.0100 m²/s`; скорость воды на переливе без глубины потока вычислить нельзя. Скорости через распределительный экран и под выходной перегородкой `UNKNOWN`, поскольку их фактические площади и нижний просвет не заданы и CAD не построен.

Контроль исходных значений раздела 6 пройден **только арифметически**: `A = 0.630 m²`, `V = 0.3465 m³`, `T = 57.75 s ≈ 57.8 s`.

---

# 26. ПРЕДВАРИТЕЛЬНОЕ ОСАЖДЕНИЕ

Рассчитать скорость осаждения для:

- 0.10 мм;
- 0.15 мм;
- 0.20 мм;
- 0.30 мм;
- 0.50 мм.

Не применять закон Стокса за пределами его области применимости без проверки Reynolds.

Записать:

| d, mm | Re particle | Settling velocity | Analytical eta |
|---:|---:|---:|---:|
| 0.10 | | | |
| 0.15 | | | |
| 0.20 | | | |
| 0.30 | | | |
| 0.50 | | | |

---

## SETTLING CALCULATION — фактически рассчитано 2026-10-03

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

# 27. PHASE C — SOLIDWORKS FLOW SIMULATION

После успешного CAD выполнить реальную Flow Simulation, если модуль доступен через коннектор.

Если недоступен:

`CAPABILITY_GAP_FLOW_SIMULATION`

и не выдавать аналитический расчёт за CFD.

---

# 28. CFD ТИП РАСЧЁТА

Использовать, если технически поддерживается:

- internal flow;
- water;
- air;
- gravity;
- free surface;
- transient calculation.

Расчёт должен учитывать заполнение ванны водой с газовой зоной над поверхностью.

---

# 29. ГРАВИТАЦИЯ

Использовать:

`g = 9.81 m/s2`

Направление проверить относительно системы координат модели.

---

# 30. НАЧАЛЬНЫЙ УРОВЕНЬ

Исходно:

`H_WATER = 550 mm`

Над водой:

`air`

Начальная свободная поверхность:

горизонтальная.

---

# 31. CFD CASE 01

Постоянный расчётный расход:

`Q_IN = 6 l/s`

Выполнить нестационарный расчёт до устойчивого или квазистационарного режима.

---

# 32. CFD CASE 02

Отдельный импульсный сценарий:

`6 l/s`

продолжительностью:

`10 s`

Общий объём:

`60 l`

Если фоновый поток неизвестен:

`Q_BACKGROUND = UNKNOWN`

Не выдумывать его.

---

# 33. ВЫХОД

Использовать физически корректную открытую/атмосферную выходную границу через перелив.

Если требуется downstream level и он неизвестен:

`REQUIRED_DOWNSTREAM_LEVEL`

---

# 34. CFD MESH

Создать минимум:

`MESH_COARSE`

`MESH_MEDIUM`

`MESH_FINE`

Сгущение сетки выполнить около:

- входа;
- гасителя;
- отверстий распределительного экрана;
- днища;
- желоба;
- выходной перегородки;
- перелива.

---

# 35. СЕТОЧНАЯ НЕЗАВИСИМОСТЬ

Сравнить MEDIUM и FINE.

По возможности контролировать:

- уровень воды;
- Q_out;
- среднюю скорость;
- Vmax около днища;
- потерю напора.

Ориентировочный критерий:

`delta <= 5 %`

Если нет:

`MESH_NOT_CONVERGED`

---

# 36. МАССОВЫЙ БАЛАНС

Сравнить:

`Q_IN`

и:

`Q_OUT`

Ориентировочный критерий:

`difference <= 2 %`

Если выше:

`MASS_BALANCE_WARNING`

---

# 37. КОНТРОЛЬНЫЕ СЕЧЕНИЯ

Создать:

`S1_INLET`

`S2_AFTER_INLET_BAFFLE`

`S3_AFTER_DISTRIBUTOR`

`S4_SETTLING_ZONE`

`S5_BEFORE_OUTLET_BAFFLE`

`S6_UNDER_OUTLET_BAFFLE`

`S7_WEIR`

Для каждого записать:

- Area;
- Q;
- Vavg;
- Vmax;
- Pressure.

---

# 38. РЕЗУЛЬТАТЫ CFD

Получить:

- поле скоростей;
- векторное поле;
- давление;
- свободную поверхность;
- зоны рециркуляции;
- области высокой скорости возле днища;
- зоны малого времени пребывания;
- Flow Trajectories.

---

# 39. ПРОВЕРКА КОРОТКОГО ПУТИ

Проверить прямой путь:

`INLET -> OUTLET`

Если выражен:

`HYDRAULIC_SHORT_CIRCUIT_WARNING`

Записать описание и конфигурацию.

---

# 40. PARTICLE STUDY

Если доступно через текущий SolidWorks-коннектор — выполнить.

Плотность:

`2650 kg/m3`

Размеры:

- 0.10 мм
- 0.15 мм
- 0.20 мм
- 0.30 мм
- 0.50 мм

Частицы вводить через входное сечение распределённо.

Не выпускать все частицы из одной точки.

---

# 41. КОЛИЧЕСТВО ЧАСТИЦ

Исходно стремиться использовать:

`N >= 1000`

частиц на фракцию, если вычислительные возможности позволяют.

Для 0.20 мм проверить чувствительность результата к числу частиц.

---

# 42. КЛАССИФИКАЦИЯ PARTICLE RESULTS

Использовать:

`CAPTURED`

`ESCAPED`

`REMAINING`

Не считать любое столкновение со стенкой автоматически успешным улавливанием.

---

# 43. РАСЧЁТ CFD ЭФФЕКТИВНОСТИ

Для каждой фракции:

`ETA = N_CAPTURED / N_INJECTED * 100 %`

Целевой критерий:

`ETA_0_20 >= 70 %`

Результат обозначать:

`CFD_PARTICLE_ESTIMATE`

а не:

`PHYSICAL_TEST_CONFIRMED`

---

# 44. ОБЯЗАТЕЛЬНАЯ СИМУЛЯЦИЯ ВСЕХ КОНФИГУРАЦИЙ

Выполнить одинаковую методологию для:

- BASE_700x900
- NARROW_600x1050
- SHORT_WIDE_800x800

---

# 45. СРАВНИТЕЛЬНАЯ ТАБЛИЦА

Заполнить после расчёта:

| Parameter | BASE | NARROW | SHORT_WIDE |
|---|---:|---:|---:|
| A_settle, m2 | 0.630 analytical | 0.630 analytical | 0.640 analytical |
| V, m3 | 0.3465 analytical | 0.3465 analytical | 0.3520 analytical |
| T theoretical, s | 57.75 | 57.75 | 58.67 |
| Q/A, m/s | 0.009524 | 0.009524 | 0.009375 |
| Vavg settling zone, m/s | 0.01558 analytical | 0.01818 analytical | 0.01364 analytical |
| Vmax bottom | NOT_RUN | NOT_RUN | NOT_RUN |
| Max water level | NOT_RUN | NOT_RUN | NOT_RUN |
| Min freeboard | NOT_RUN | NOT_RUN | NOT_RUN |
| Pressure loss | NOT_RUN | NOT_RUN | NOT_RUN |
| eta 0.10 | NOT_RUN | NOT_RUN | NOT_RUN |
| eta 0.15 | NOT_RUN | NOT_RUN | NOT_RUN |
| eta 0.20 | NOT_RUN | NOT_RUN | NOT_RUN |
| eta 0.30 | NOT_RUN | NOT_RUN | NOT_RUN |
| eta 0.50 | NOT_RUN | NOT_RUN | NOT_RUN |
| Short circuit | NOT_RUN | NOT_RUN | NOT_RUN |
| Mesh convergence | NOT_RUN | NOT_RUN | NOT_RUN |
| Mass balance | NOT_RUN | NOT_RUN | NOT_RUN |

---

# 46. ОПТИМИЗАЦИЯ

Если:

`ETA_0_20 < 70 %`

или:

`HYDRAULIC_SHORT_CIRCUIT_WARNING`

проводить итерации в порядке:

1. L_SETTLE;
2. B_BATH;
3. положение входного гасителя;
4. положение распределительного экрана;
5. свободное сечение экрана;
6. диаметр отверстий;
7. глубина выходной перегородки;
8. ширина перелива;
9. форма пескосборной зоны;
10. общий объём.

После каждой итерации:

`REBUILD -> CFD -> PARTICLE STUDY -> COMPARE`

---

# 47. СОХРАНЕНИЕ СИМУЛЯЦИИ

Сохранить физические файлы проекта Flow Simulation в папке проекта.

Создать структуру, например:

`/Песколовка/01_CAD/`

`/Песколовка/02_FlowSimulation/BASE_700x900/`

`/Песколовка/02_FlowSimulation/NARROW_600x1050/`

`/Песколовка/02_FlowSimulation/SHORT_WIDE_800x800/`

`/Песколовка/03_Результаты/`

`/Песколовка/04_Анимации/`

`/Песколовка/05_Отчеты/`

---

# 48. СОХРАНЕНИЕ СИМУЛЯЦИИ В ЭТОМ MD

Бинарные файлы SOLIDWORKS/Flow Simulation физически не встраивать в Markdown.

Но **в этот файл обязательно записать полное состояние симуляции, достаточное для аудита и повторного запуска**.

Для каждой конфигурации записать:

- имя проекта;
- путь к CAD;
- путь к CFD-проекту;
- дату/версию расчёта;
- тип анализа;
- выбранные жидкости;
- гравитацию;
- начальный уровень воды;
- граничные условия;
- параметры входа;
- параметры выхода;
- mesh settings;
- local mesh settings;
- solver settings;
- физические модели;
- расчётное время;
- convergence status;
- Q_in;
- Q_out;
- mass balance;
- основные результаты;
- particle settings;
- particle count;
- particle efficiency;
- предупреждения;
- пути к изображениям;
- пути к анимациям;
- пути к экспортированным данным.

Таким образом этот `.md` является текстовым слепком симуляции.

---

# 49. CFD RECORD — BASE_700x900

Codex должен заполнить:

`STATUS = NOT_RUN_GEOMETRY_INCOMPLETE`

`CAD_FILE = NOT_AVAILABLE_NO_CFD_RUN`

`CFD_PROJECT = NOT_AVAILABLE_NO_CFD_RUN`

`FLOW_TYPE = NOT_AVAILABLE_NO_CFD_RUN`

`FLUIDS = NOT_AVAILABLE_NO_CFD_RUN`

`GRAVITY = NOT_AVAILABLE_NO_CFD_RUN`

`FREE_SURFACE = NOT_AVAILABLE_NO_CFD_RUN`

`TRANSIENT = NOT_AVAILABLE_NO_CFD_RUN`

`Q_IN = NOT_AVAILABLE_NO_CFD_RUN`

`OUTLET_BC = NOT_AVAILABLE_NO_CFD_RUN`

`INITIAL_WATER_LEVEL = NOT_AVAILABLE_NO_CFD_RUN`

`MESH = NOT_AVAILABLE_NO_CFD_RUN`

`LOCAL_MESH = NOT_AVAILABLE_NO_CFD_RUN`

`SOLVER_STATUS = NOT_AVAILABLE_NO_CFD_RUN`

`Q_OUT = NOT_AVAILABLE_NO_CFD_RUN`

`MASS_BALANCE = NOT_AVAILABLE_NO_CFD_RUN`

`VAVG_SETTLING = NOT_AVAILABLE_NO_CFD_RUN`

`VMAX_BOTTOM = NOT_AVAILABLE_NO_CFD_RUN`

`MAX_WATER_LEVEL = NOT_AVAILABLE_NO_CFD_RUN`

`MIN_FREEBOARD = NOT_AVAILABLE_NO_CFD_RUN`

`PRESSURE_LOSS = NOT_AVAILABLE_NO_CFD_RUN`

`SHORT_CIRCUIT = NOT_AVAILABLE_NO_CFD_RUN`

`ETA_0_20 = NOT_AVAILABLE_NO_CFD_RUN`

`IMAGE_PATHS = NOT_AVAILABLE_NO_CFD_RUN`

`ANIMATION_PATHS = NOT_AVAILABLE_NO_CFD_RUN`

---

# 50. CFD RECORD — NARROW_600x1050

`STATUS = NOT_RUN_GEOMETRY_INCOMPLETE`

`CAD_FILE = NOT_AVAILABLE_NO_CFD_RUN`

`CFD_PROJECT = NOT_AVAILABLE_NO_CFD_RUN`

`FLOW_TYPE = NOT_AVAILABLE_NO_CFD_RUN`

`FLUIDS = NOT_AVAILABLE_NO_CFD_RUN`

`GRAVITY = NOT_AVAILABLE_NO_CFD_RUN`

`FREE_SURFACE = NOT_AVAILABLE_NO_CFD_RUN`

`TRANSIENT = NOT_AVAILABLE_NO_CFD_RUN`

`Q_IN = NOT_AVAILABLE_NO_CFD_RUN`

`OUTLET_BC = NOT_AVAILABLE_NO_CFD_RUN`

`INITIAL_WATER_LEVEL = NOT_AVAILABLE_NO_CFD_RUN`

`MESH = NOT_AVAILABLE_NO_CFD_RUN`

`LOCAL_MESH = NOT_AVAILABLE_NO_CFD_RUN`

`SOLVER_STATUS = NOT_AVAILABLE_NO_CFD_RUN`

`Q_OUT = NOT_AVAILABLE_NO_CFD_RUN`

`MASS_BALANCE = NOT_AVAILABLE_NO_CFD_RUN`

`VAVG_SETTLING = NOT_AVAILABLE_NO_CFD_RUN`

`VMAX_BOTTOM = NOT_AVAILABLE_NO_CFD_RUN`

`MAX_WATER_LEVEL = NOT_AVAILABLE_NO_CFD_RUN`

`MIN_FREEBOARD = NOT_AVAILABLE_NO_CFD_RUN`

`PRESSURE_LOSS = NOT_AVAILABLE_NO_CFD_RUN`

`SHORT_CIRCUIT = NOT_AVAILABLE_NO_CFD_RUN`

`ETA_0_20 = NOT_AVAILABLE_NO_CFD_RUN`

`IMAGE_PATHS = NOT_AVAILABLE_NO_CFD_RUN`

`ANIMATION_PATHS = NOT_AVAILABLE_NO_CFD_RUN`

---

# 51. CFD RECORD — SHORT_WIDE_800x800

`STATUS = NOT_RUN_GEOMETRY_INCOMPLETE`

`CAD_FILE = NOT_AVAILABLE_NO_CFD_RUN`

`CFD_PROJECT = NOT_AVAILABLE_NO_CFD_RUN`

`FLOW_TYPE = NOT_AVAILABLE_NO_CFD_RUN`

`FLUIDS = NOT_AVAILABLE_NO_CFD_RUN`

`GRAVITY = NOT_AVAILABLE_NO_CFD_RUN`

`FREE_SURFACE = NOT_AVAILABLE_NO_CFD_RUN`

`TRANSIENT = NOT_AVAILABLE_NO_CFD_RUN`

`Q_IN = NOT_AVAILABLE_NO_CFD_RUN`

`OUTLET_BC = NOT_AVAILABLE_NO_CFD_RUN`

`INITIAL_WATER_LEVEL = NOT_AVAILABLE_NO_CFD_RUN`

`MESH = NOT_AVAILABLE_NO_CFD_RUN`

`LOCAL_MESH = NOT_AVAILABLE_NO_CFD_RUN`

`SOLVER_STATUS = NOT_AVAILABLE_NO_CFD_RUN`

`Q_OUT = NOT_AVAILABLE_NO_CFD_RUN`

`MASS_BALANCE = NOT_AVAILABLE_NO_CFD_RUN`

`VAVG_SETTLING = NOT_AVAILABLE_NO_CFD_RUN`

`VMAX_BOTTOM = NOT_AVAILABLE_NO_CFD_RUN`

`MAX_WATER_LEVEL = NOT_AVAILABLE_NO_CFD_RUN`

`MIN_FREEBOARD = NOT_AVAILABLE_NO_CFD_RUN`

`PRESSURE_LOSS = NOT_AVAILABLE_NO_CFD_RUN`

`SHORT_CIRCUIT = NOT_AVAILABLE_NO_CFD_RUN`

`ETA_0_20 = NOT_AVAILABLE_NO_CFD_RUN`

`IMAGE_PATHS = NOT_AVAILABLE_NO_CFD_RUN`

`ANIMATION_PATHS = NOT_AVAILABLE_NO_CFD_RUN`

---

# 52. СОХРАНЕНИЕ ИЗОБРАЖЕНИЙ

Если доступно, сохранить:

- продольный Velocity Cut Plot;
- горизонтальный Velocity Cut Plot;
- Bottom Velocity Plot;
- Flow Trajectories;
- Free Surface;
- Pressure Plot;
- Particle Trajectories 0.20 мм.

В этот MD вставить относительные Markdown-ссылки, например:

`![BASE Velocity](./03_Результаты/BASE_velocity.png)`

---

# 53. СОХРАНЕНИЕ АНИМАЦИЙ

Если Flow Simulation позволяет экспортировать анимацию через доступный инструмент:

сохранить минимум:

- free surface;
- velocity;
- flow trajectories;
- particle trajectories 0.20 мм.

В MD сохранить путь:

`ANIMATION_FLOW = ...`

`ANIMATION_PARTICLES_020 = ...`

---

# 54. UNKNOWN

Не угадывать данные.

Записывать сюда всё отсутствующее:

## UNKNOWN LIST

- `Q_BACKGROUND`
- `ACTUAL_WASTEWATER_VISCOSITY`
- `SAND_CONCENTRATION`
- `ACTUAL_GRAIN_DISTRIBUTION`
- `DOWNSTREAM_WATER_LEVEL`
- `WALL_ROUGHNESS`
- `PARTICLE_WALL_INTERACTION`
- `ACTUAL_DN100_INTERNAL_DIAMETER`
- `SCREEN_HOLE_COUNT_AND_OPEN_AREA`
- `OUTLET_BAFFLE_CLEARANCE`
- `SOLIDWORKS_LICENSE_AND_API_HEALTH`
- `FLOW_SIMULATION_LICENSE_AND_API_ACCESS`

Дополнять при необходимости.

---

# 55. CAPABILITY GAP

Заполнить фактический список.

## CAPABILITY_GAP LIST

Пока:

- `CAPABILITY_GAP_SOLIDWORKS_CONNECTOR`: инструмент SolidWorks отсутствует в текущем перечне доступных инструментов.
- `WORKAROUND_SOLIDWORKS_COM`: динамический COM-вызов PowerShell даёт `0x8002802B`; типизированный C# interop успешно обращается к API.
- `FLOW_SIMULATION_ACCESS = ADDIN_LOADED`: надстройка уже загружена, `LoadAddIn` вернул 2 (`swAddinAlreadyLoaded`); создание CFD-проекта и наличие расчётной лицензии ещё не проверены.
- `PARTICLE_STUDY_ACCESS = UNKNOWN`: запуск и API Particle Study ещё не проверены.

Если функция недоступна, записывать сюда.

---

# 56. НЕ ВЫПОЛНЯТЬ ПОКА

Без отдельной команды пользователя не создавать:

- производственные чертежи;
- DXF;
- развёртки;
- сварочные чертежи;
- EBOM;
- MBOM;
- CAM;
- программы лазерной резки;
- программы мехобработки;
- полный технологический процесс.

---

# 57. ФИНАЛЬНЫЙ РЕЕСТР ФАЙЛОВ

После выполнения Codex обязан заполнить таблицу:

| Type | File | Full path | Status |
|---|---|---|---|
| MASTER | GRIT_MASTER_V10_20261003.SLDPRT | C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD\GRIT_MASTER_V10_20261003.SLDPRT | SAVED; 3 CONFIGURATIONS; PARTIAL CAD |
| Assembly | NOT_CREATED | — | NOT_STARTED |
| BASE CFD | NOT_CREATED | — | NOT_RUN |
| NARROW CFD | NOT_CREATED | — | NOT_RUN |
| SHORT_WIDE CFD | NOT_CREATED | — | NOT_RUN |
| Images | NOT_CREATED | — | NOT_RUN |
| Animations | NOT_CREATED | — | NOT_RUN |
| Reports | GRIT_CHAMBER_CODEX_TASK.md | C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\Песколовка\GRIT_CHAMBER_CODEX_TASK.md | UPDATED |

---

# 58. ФИНАЛЬНЫЙ СТАТУС

Заполнить после работы:

`CAD_STATUS = PARTIAL_BATH_ONLY`

`CONFIGURATION_STATUS = PASS_MASTER_BATH_ONLY`

`REBUILD_STATUS = PASS_CURRENT_GEOMETRY_ALL_3`

`ANALYTICAL_CALC_STATUS = COMPLETED_PRELIMINARY`

`FLOW_SIMULATION_STATUS = NOT_RUN_GEOMETRY_INCOMPLETE`

`PARTICLE_STUDY_STATUS = NOT_RUN_NO_CFD`

`OPTIMIZATION_STATUS = NOT_RUN_NO_CFD_RESULT`

`manufacturing_approved = false`

---

# 59. ПРАВИЛО ДОСТОВЕРНОСТИ

Не писать:

`PASS`

без фактического выполнения соответствующей операции.

Не писать:

`CFD COMPLETED`

если Solver не запускался.

Не писать:

`PARTICLE STUDY COMPLETED`

если Particle Study не запускался.

Не писать:

`ETA >= 70 %`

если значение не получено расчётом.

Не выдавать:

- аналитический расчёт за CFD;
- Flow Trajectories воды за траектории песка;
- геометрическую модель за проверенную конструкцию;
- CFD за натурное испытание.

---

# 59A. ЖУРНАЛ ПОВТОРНОГО ЗАПУСКА — 2026-10-03

- SOLIDWORKS Design Premium 2026 SP3.2 подключён через типизированный C# COM interop (`RevisionNumber = 34.3.2`).
- Новый рабочий файл: `C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD\GRIT_MASTER_V10_20261003.SLDPRT`. Существующие пользовательские SLDPRT/SLDASM/SLDDRW не изменялись.
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

# 60. ТОЧКА ЗАВЕРШЕНИЯ ТЕКУЩЕЙ РАБОТЫ

Работа считается выполненной на этом этапе, если:

- создана новая CAD-модель;
- существует MASTER/Skeleton;
- созданы три конфигурации;
- выполнен rebuild;
- выполнены геометрические проверки;
- выполнена аналитическая гидравлика;
- Flow Simulation либо фактически выполнена, либо доказан конкретный CAPABILITY_GAP;
- Particle Study либо выполнен, либо доказан конкретный CAPABILITY_GAP;
- файлы симуляции сохранены;
- изображения и анимации сохранены при наличии соответствующей функции;
- этот Markdown обновлён фактическими результатами;
- все UNKNOWN перечислены;
- все ошибки перечислены;
- все пути к результатам записаны.

Финальная обязательная строка:

`manufacturing_approved = false`


