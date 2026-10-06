from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import csv,json,hashlib

root=Path('work/particle_results');out=Path('outputs')
trap=json.loads((root/'summary_15mm_128seeds.json').read_text(encoding='utf-8'))
hopper=json.loads((root/'summary_12mm_128seeds_hoppertrap_c5000.json').read_text(encoding='utf-8'))
reflect=json.loads((root/'summary_12mm_128seeds_reflect_c2000.json').read_text(encoding='utf-8'))
coarse=json.loads((root/'summary_15mm_128seeds_reflect_c2000.json').read_text(encoding='utf-8'))
assert len(trap)==len(hopper)==len(reflect)==len(coarse)==6
for row in (trap,hopper,reflect,coarse):
 for r in row:assert abs(sum(r['fractions'].values())-1)<1e-10
seed_path=root/'summary_12mm_256seeds_reflect_c5000.json'
seed=json.loads(seed_path.read_text(encoding='utf-8')) if seed_path.exists() else []
step_path=root/'summary_15mm_128seeds_reflect_c2000_h2.json'
step=json.loads(step_path.read_text(encoding='utf-8')) if step_path.exists() else []
collision=json.loads((root/'summary_12mm_128seeds_reflect_c5000.json').read_text(encoding='utf-8'))

records=[]
for a,b,c in zip(trap,hopper,reflect):
 d=a['diameter_mm'];assert d==b['diameter_mm']==c['diameter_mm']
 records.append({'diameter_mm':d,'grid_mm':12,'free_settling_m_s':a['free_settling_m_s'],
 'sticky_all_walls_bottom_percent':100*a['fractions']['bottom_outlet'],
 'sticky_all_walls_hopper_percent':100*a['fractions']['hopper_wall'],
 'upper_reflect_hopper_absorb_hopper_percent':100*b['fractions']['hopper_wall'],
 'upper_reflect_hopper_absorb_direct_bottom_percent':100*b['fractions']['bottom_outlet'],
 'reflect_all_direct_bottom_percent':100*c['fractions']['bottom_outlet'],
 'reflect_all_direct_bottom_15mm_percent':100*coarse[len(records)]['fractions']['bottom_outlet'],
 'reflect_all_main_percent':100*c['fractions']['main_outlet'],
 'reflect_all_unresolved_percent':100*c['fractions']['unresolved'],
 'reflect_all_direct_bottom_count':c['counts']['bottom_outlet'],
 'reflect_all_unresolved_count':c['counts']['unresolved'],
 'particle_study_in_solidworks':False})
with (out/'PT-SHT-10_осаждение_фракции.csv').open('w',encoding='utf-8-sig',newline='') as fp:
 wr=csv.DictWriter(fp,fieldnames=records[0]);wr.writeheader();wr.writerows(records)
(out/'PT-SHT-10_осаждение_расчёт.json').write_text(json.dumps({'title':'Independent demonstration particle tracker on SOLIDWORKS water flow field','primary_grid_mm':12,'wall_scenarios':{'trap_all_15mm':trap,'reflect_upper_trap_hopper_12mm':hopper,'reflect_all_12mm_2000':reflect,'reflect_all_15mm_2000':coarse},'collision_check_12mm_5000':collision,'seed_check':seed,'step_check_15mm':step,'model_is_SOLIDWORKS_Particle_Study':False},ensure_ascii=False,indent=2),encoding='utf-8')
table='\n'.join(f"| {r['diameter_mm']:.2f} | {r['free_settling_m_s']*1000:.1f} | {r['upper_reflect_hopper_absorb_hopper_percent']:.1f} | {r['reflect_all_direct_bottom_percent']:.1f} | {r['reflect_all_main_percent']:.1f} | {r['reflect_all_unresolved_percent']:.1f} |" for r in records)
weights=[.10,.15,.15,.20]
direct=sum(weights[i]*records[i]['reflect_all_direct_bottom_percent'] for i in range(4))/.60
hopper_aggregate=sum(weights[i]*records[i]['upper_reflect_hopper_absorb_hopper_percent'] for i in range(4))/.60
mass_direct=.60*direct/100 # kg/h total sand 1 kg/h
mass_hopper=.60*hopper_aggregate/100
fine_text=f"Для 0,25 мм: при шаге 15 мм {coarse[3]['fractions']['bottom_outlet']*100:.2f}% через низ; при шаге 12 мм {reflect[3]['fractions']['bottom_outlet']*100:.2f}%, незавершено {reflect[3]['fractions']['unresolved']*100:.2f}%. Разность долей через низ {abs(reflect[3]['fractions']['bottom_outlet']-coarse[3]['fractions']['bottom_outlet'])*100:.2f} процентного пункта. Пространственная сходимость доли удаления **не достигнута**."
seed_text='Не выполнена.'
if seed:
 s=next(v for v in seed if v['diameter_mm']==.25)
 seed_text=f"Для 0,25 мм на поле 12 мм: 128 стартовых точек {reflect[3]['fractions']['bottom_outlet']*100:.2f}%, 256 точек {s['fractions']['bottom_outlet']*100:.2f}% через нижнее отверстие."
step_text='Не выполнена.'
if step:
 s=next(v for v in step if v['diameter_mm']==.25)
 step_text=f"Для 0,25 мм на поле 15 мм: шаг траектории до 5 мм {coarse[3]['fractions']['bottom_outlet']*100:.2f}%, до 2,5 мм {s['fractions']['bottom_outlet']*100:.2f}%."
report=f'''# PT-SHT-10 — демонстрационный расчёт осаждения песка

30 сентября 2026 г. Связан с [повторным расчётом воды](PT-SHT-10_повторный_расчёт_воды.md) для **10 м³/ч**.

## Вывод по критерию 60%

**В расчётной модели с отражением от всех стенок на поле 12 мм частицы d≤0,25 мм дают {direct:.1f}% массы через нижнее отверстие**, если принять иллюстративные массовые доли фракций 0,10/0,15/0,20/0,25 мм равными 10/15/15/20% общего песка. Это {mass_direct:.3f} кг/ч из 0,60 кг/ч песка этих размеров при условной концентрации 100 мг/л. В такой постановке цель 60% формально достигается **по уже завершённым выходам**; незавершённые траектории не добавлены к числителю.

**Это не подтверждение фактической эффективности устройства.** Переход от шага поля 15 к 12 мм изменил прямой выход для d=0,25 мм на {abs(reflect[3]['fractions']['bottom_outlet']-coarse[3]['fractions']['bottom_outlet'])*100:.1f} процентного пункта: пространственная сходимость частиц не доказана. При полностью поглощающих стенках прямой выход песка через низ в этой модели равен 0%; при поглощающей поверхности нижнего бункера песок задерживается там, но не пересекает отверстие. Реальное взаимодействие зерна со стенкой, движение накопившегося песка к отверстию, работа шнека и фактические граничные условия неизвестны. Штатный SOLIDWORKS Particle Study не удалось запустить из-за несохраняемого источника частиц; здесь выполнена **отдельная вычислительная трассировка** по настоящему полю воды SOLIDWORKS.

## Результаты по фракциям

| Диаметр, мм | Свободное оседание, мм/с | Осело в нижнем приёмке¹, % | Через низ², % | Основной выход², % | Незавершено², % |
|---:|---:|---:|---:|---:|---:|
{table}

¹ Верхние стенки отражают, внешняя коническая поверхность нижнего приёмка удерживает частицу при первом контакте. Это накопление в бункере, **не** удаление через нижнее отверстие. Прямой выход через низ в этом сценарии: 0% для всех фракций.

² Все стенки отражают частицу; нормальный коэффициент восстановления 0,2, тангенциальная доля скорости после контакта 0,75. Предел 2000 столкновений, 180 с и 10 000 шагов. Незавершённые траектории не прибавлены к выведенным. Массовая сумма категорий по каждой строке составляет 100% с погрешностью округления.

При условных долях, приведённых выше, **{hopper_aggregate:.1f}%** массы фракций d≤0,25 мм оседает в нижнем приёмке в сценарии ¹. Это {mass_hopper:.3f} кг/ч, которые нужно фактически эвакуировать, чтобы считать удалёнными. Доли фракций в реальных стоках неизвестны; агрегированный процент иллюстрирует только выбранное распределение. Сравнивать с требованием 60% следует именно поток **выведенной массы песка**, а не процент объёма воды.

![Доли по фракциям](PT-SHT-10_осаждение_по_фракциям.png)

![Примеры траекторий](PT-SHT-10_траектории_песка.png)

![Проверка шага выборки поля](PT-SHT-10_чувствительность_сетки_частиц.png)

Изображены 10 из 128 траекторий для трёх фракций. Сечение CAD в сером цвете служит ориентиром; линии являются проекцией пространственных траекторий. Проценты рассчитаны по всем стартовым точкам с весами входного массового потока.

## Как считали

1. Исходное поле скорости — конечный решённый файл Flow Simulation `Модель/2/2.fld`, проверенный на трёх CFD сетках. Из него штатным интерполятором получено **93 621 внутренних узлов** на шаге 12 мм; сравнение выполнено с 48 007 узлами на шаге 15 мм. Это сетки **выборки результатов**, а не две новые CFD сетки. Жидкостная полость извлечена геометрическим ядром из отдельной копии сборки и триангулирована: 0,162397 м³ против объёма CAD 0,162543 м³, расхождение 0,090%.
2. На входной крышке Ø51 мм размещено 128 равномерно распределённых квазислучайных стартовых точек. Каждая траектория взвешена локальной нормальной скоростью воды. Начальная скорость зерна равна местной скорости воды.
3. Вода: плотность **997,574 кг/м³**, динамическая вязкость **0,00100167 Па·с** из решения Flow. Песок: идеальные сферы плотностью **2650 кг/м³**. Решено уравнение движения с сопротивлением Шиллера — Наумана и силой тяжести с архимедовой поправкой. Односторонняя связь допустима только как приближение для условной низкой концентрации 100 мг/л; влияние зерна на воду и столкновения зёрен не рассчитывались.
4. Выход через низ: пересечение плоскости y≈0,004 м внутри отверстия Ø102 мм. Основной выход: пересечение z≈0,353 м в пределах выходного сечения. При контакте с иной поверхностью применяется один из описанных вариантов стенки. Результаты не моделируют шнек или движение осадка после прилипания.
5. Незавершённые траектории остаются отдельной категорией. Особенно для мелких фракций они ограничивают нижнюю оценку прямого выхода.

### Проверки устойчивости

- Пространственная выборка поля: {fine_text}
- Число стартовых точек: {seed_text}
- Шаг движения частицы: {step_text}
- На поле 15 мм повышение предела столкновений с 200 до 2000 для d=0,25 мм изменило прямой выход с 32,8% до {coarse[3]['fractions']['bottom_outlet']*100:.1f}%; прежние 32,8% были численным ограничением. На поле 12 мм повышение предела с 2000 до 5000 оставило прямой выход на {collision[0]['fractions']['bottom_outlet']*100:.2f}%; оставшиеся {collision[0]['fractions']['unresolved']*100:.2f}% не покинули область за 180 с.
- Баланс массы: для каждой фракции сумма нижнего выхода, основного выхода, контактов со стенками и незавершённых траекторий =100%.

## Границы применимости

Постобработка интерполирует поле воды на более редкую сетку, чем сама CFD модель. Модель отражения стенок задана демонстрационно; известные фактические коэффициенты восстановления, шероховатость и налипание отсутствуют. Турбулентное рассеивание, несферичность песка, взаимное влияние частиц, переменная концентрация, свободная поверхность, уровень жидкости, подпор отводящей сети и шнек не включены. Поглощающая стенка описывает предельный случай: частица остаётся на поверхности, а не выходит через отверстие. Ошибка этих допущений не оценивается численной сходимостью траекторий.

**Для приёмочного вывода** нужно проверить режим заполнения и выходной подпор, задать реальные фракции и свойства стенок, включить механизм удаления осадка, выполнить штатный Particle Study или экспериментальный тест с массовым балансом песка на входе и обоих выходах. В интерфейсе также остаётся незавершённым штатный протокол Check Geometry; отдельная проверка CAD полости и жидкостная сетка выполнены.

## Данные и источники метода

- [Таблица по фракциям](PT-SHT-10_осаждение_фракции.csv), [полные численные данные](PT-SHT-10_осаждение_расчёт.json), [архив воспроизведения](PT-SHT-10_осаждение_модель.zip).
- Описание физического Particle Study и контактов со стенками — установленное локальное руководство SOLIDWORKS Flow Simulation, раздел `Particle Studies` и `Wall Conditions (Particle Study)`; [публикация SOLIDWORKS о Particle Study](https://blogs.solidworks.com/products/solidworks/how-long-is-the-flow/).
- [Формула силы сопротивления сферы (NASA)](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/drag-of-a-sphere/); [реализация корреляции Шиллера — Наумана](https://doc.aspherix-dem.com/coupling/forceModel_SchillerNaumannDrag.html).
'''
(out/'PT-SHT-10_расчёт_осаждения.md').write_text(report,encoding='utf-8')
archive=out/'PT-SHT-10_осаждение_модель.zip'
files=[Path('work/cavity_for_particle_model.stl'),Path('work/water_field_3d_15mm.npz'),Path('work/trace_sand_from_water.py'),Path('work/sample_3d_water.py'),Path('work/plot_sand_results.py')]
fine_grid=Path('work/water_field_3d_12mm.npz')
if fine_grid.exists():files.append(fine_grid)
files+=list(root.glob('*.json'))+list(root.glob('*.npz'))
files+=[out/'PT-SHT-10_осаждение_фракции.csv',out/'PT-SHT-10_осаждение_расчёт.json',out/'PT-SHT-10_расчёт_осаждения.md',out/'PT-SHT-10_осаждение_по_фракциям.png',out/'PT-SHT-10_траектории_песка.png',out/'PT-SHT-10_чувствительность_сетки_частиц.png']
with ZipFile(archive,'w',ZIP_DEFLATED,compresslevel=6) as z:
 for p in files:z.write(p,p.resolve().relative_to(Path.cwd()))
with ZipFile(archive) as z:assert z.testzip() is None
print('report',out/'PT-SHT-10_расчёт_осаждения.md','archive',archive,'bytes',archive.stat().st_size,'aggregate_direct',direct,'aggregate_hopper',hopper_aggregate)
