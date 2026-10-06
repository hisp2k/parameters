"""24.SHT.G: explicit geometry, source-scoped labor and selected GOST checks.

Workbook formulas are reconstructed here, not evaluated from uploaded text.
Masses describe known MAKE groups, not the complete product or a CAD rebuild.
"""
import hashlib
import json
import math
from pathlib import Path

STANDARD_URL = 'https://protect.gost.ru/gost/details/d7686f5d-79ea-4218-9f61-c5e0d0cd10ea'
STANDARD_TEXT = 'https://files.stroyinf.ru/Data2/1/4294852/4294852027.pdf'
REFERENCE = dict(length=6100., work_length=6000., diameter=300., pitch=300., flight_inner=121.,
    flight_thickness=4., shaft_diameter=121., shaft_wall=8., shaft_length=5994., body_thickness=4.,
    gap=9., flange=45., supports=2, chutes=1, full_flights=20, cut_flights=1, cut_fraction=.5,
    cover_thickness=0., support_mass=0., other_mass=0., waste=.15, angle=0.,
    flight_material='AISI 316', shaft_material='AISI 316Ti', body_material='AISI 316')


def source_data():
    return json.loads((Path(__file__).parent / 'references/screw_conveyors/workbook_v11.json').read_text(encoding='utf-8'))


def signature(values):
    return hashlib.sha256(json.dumps(values, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()


def finite(value, label, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < minimum:
        raise ValueError(f'{label}: требуется конечное число не меньше {minimum}')
    return value


def validate(p):
    if set(p) != set(REFERENCE):
        raise ValueError('Состав параметров проекта не соответствует версии шнекового калькулятора')
    for k, default in REFERENCE.items():
        if isinstance(default, (float, int)):
            finite(p[k], k)
    for k in ('length','work_length','diameter','pitch','flight_inner','flight_thickness',
              'shaft_diameter','shaft_wall','shaft_length','body_thickness','gap','supports','chutes'):
        if p[k] <= 0:
            raise ValueError(f'{k}: значение должно быть больше нуля')
    for k in ('supports','chutes','full_flights','cut_flights'):
        if p[k] != int(p[k]):
            raise ValueError(f'{k}: требуется целое количество')
    if p['full_flights'] + p['cut_flights'] <= 0:
        raise ValueError('Нужен хотя бы один виток')
    if not 0 < p['cut_fraction'] <= 1:
        raise ValueError('Доля подрезанного пера должна быть больше 0 и не больше 1')
    if p['flight_inner'] >= p['diameter'] or p['shaft_diameter'] >= p['diameter']:
        raise ValueError('Диаметр пера должен превышать внутренний диаметр и диаметр вала')
    if 2*p['shaft_wall'] >= p['shaft_diameter']:
        raise ValueError('У трубы должен оставаться положительный внутренний диаметр')
    if p['work_length'] > p['length'] or p['shaft_length'] > p['length']:
        raise ValueError('Рабочая часть и трубчатый вал не должны выходить за длину корпуса семейства 24')
    if p['flight_inner'] < p['shaft_diameter']:
        raise ValueError('Перо пересекается с валом: внутренний диаметр меньше наружного диаметра трубы')
    if p['flight_thickness'] >= p['pitch']:
        raise ValueError('Толщина пера должна быть меньше шага')
    if p['angle'] >= 90 or p['waste'] > 1:
        raise ValueError('Угол должен быть меньше 90°, отходы — от 0 до 100%')
    for k in ('flight_material','shaft_material','body_material'):
        if p[k] not in ('AISI 316','AISI 316L','AISI 316Ti'):
            raise ValueError('Неизвестная марка материала')


def check(code, status, detail, basis, clause='', url=''):
    return dict(code=code, status=status, detail=detail, basis=basis, clause=clause, url=url)


def calculate(p, source=None):
    validate(p)
    source = source or source_data()
    pi = math.pi
    ro, ri, a = p['diameter']/2, p['flight_inner']/2, p['pitch']/(2*pi)
    area = pi*(ro*math.sqrt(ro**2+a**2)-ri*math.sqrt(ri**2+a**2)
               +a*a*math.log((ro+math.sqrt(ro**2+a**2))/(ri+math.sqrt(ri**2+a**2))))/1e6
    flight_mass = area*p['flight_thickness']/1000*8000
    mass = [
        ('Полные перья',p['full_flights']*flight_mass,p['flight_material'],'Mass24_v8!D4'),
        ('Подрезанные перья',p['cut_flights']*p['cut_fraction']*flight_mass,p['flight_material'],'Mass24_v8!D5'),
        ('Трубчатый вал',pi/4*((p['shaft_diameter']/1000)**2-((p['shaft_diameter']-2*p['shaft_wall'])/1000)**2)*p['shaft_length']/1000*8000,p['shaft_material'],'Mass24_v8!D6'),
        ('Желоб — оценка',((pi*(p['diameter']+2*p['gap'])/2+2*p['flange'])/1000)*p['length']/1000*p['body_thickness']/1000*8000,p['body_material'],'Mass24_v8!D7'),
        ('Крышка — оценка',(p['diameter']+2*p['gap']+2*p['flange'])/1000*p['length']/1000*p['cover_thickness']/1000*8000,p['body_material'],'Mass24_v8!D8'),
        ('Опоры — ручная масса',p['supports']*p['support_mass'],p['body_material'],'Ручной ввод'),
        ('Прочая конструкция — ручная масса',p['other_mass'],'Смешанный','Ручной ввод')]
    masses = [dict(name=n,net_kg=m,blank_kg=m*(1+p['waste']),material=g,source=s) for n,m,g,s in mass]
    for m in masses:
        finite(m['net_kg'],'Расчётная масса')
        finite(m['blank_kg'],'Расчётная потребность')
    l, d, ls = p['length']/6100, p['diameter']/300, p['shaft_length']/5994
    n = (p['full_flights']+p['cut_flights'])/21
    factors = [.5*(l*d*p['body_thickness']/4+n*d*d*p['flight_thickness']/4), .5*(l+ls),
               l*d, .5*(l*d+n), l, .5*(l+p['chutes']), (l+p['supports']/2+p['chutes'])/3,
               ls*p['shaft_diameter']/121, p['shaft_diameter']/121, 1, l, l]
    scope = all(p[k]==REFERENCE[k] for k in ('diameter','pitch','flight_thickness','flight_material'))
    operations = []
    for i, (op, factor) in enumerate(zip(source['operations'],factors)):
        ph, mh = op['person_h']*factor, op['machine_h']*factor
        if i == 9:
            ph = mh = .084*(p['full_flights']+p['cut_flights']) if scope else None
        if ph is not None:
            finite(ph,'Расчётная трудоёмкость')
            finite(mh,'Расчётное машинное время')
        operations.append(op | dict(person_h=ph,machine_h=mh, status=('Норма эталона' if scope else 'Нужна новая норма') if i==9 else 'Оценка; нужна калибровка'))
    changed = any(p[k] != REFERENCE[k] for k in REFERENCE)
    checks = [check('MODEL','REVIEW' if changed else 'INFO',
        'Изменена конструкция: нужны КД, проверка прочности, привода, опор и комплектации.' if changed else 'Эталон 24.SHT.G; исходный v11 не прошёл полную приёмку.', 'Эталон / инженерная проверка'),
        check('BOM','MISSING','В книге 30 из 74 MAKE; 23 уникальных BUY. 44 MAKE отсутствуют. Полная себестоимость не определена.','BOM24_v10!A4:D10'),
        check('PRICE_GRADE','MISSING','Цена AISI 316L 6 мм из книги не применяется к AISI 316 4 мм или трубе AISI 316Ti.','Металлсервис!A7:L7'),
        check('FLIGHT_NORM','OK' if scope else 'MISSING','0,084 ч/перо: только D300 / P300 / t4 / AISI 316.','Op24_v9!H13'),
        check('FLIGHT_LAYOUT','REVIEW','Количество полных перьев, подрезка и перекрытия проверяются по КД. Доля подрезки задаёт массу, а не осевую длину.','Param24_v8!F11:F13'),
        check('MASS_SCOPE','INFO','Показана масса известных групп MAKE. Плотность 8000 кг/м³ — допущение исходной книги; масса BUY не включена.','Mass24_v8'),
        check('DRIVE','MISSING','Производительность, груз, обороты, мощность, прогиб и критическая частота требуют отдельной проверки. Привод из BOM не подобран заново.','Инженерная проверка')]
    if p['flight_inner'] != p['shaft_diameter']:
        checks.append(check('FIT','REVIEW','Зазор между пером и трубой требует проверки сварного соединения.','Геометрия, не ГОСТ'))
    if not p['cover_thickness'] or not p['support_mass'] or not p['other_mass']:
        checks.append(check('MASS_INPUTS','MISSING','Не заданы крышка, масса опоры или прочая конструкция. Нули не подтверждают отсутствие деталей.','Input24_v10!C4:C6'))
    return dict(profile='24.SHT.G',inputs=p,masses=masses,operations=operations,checks=checks,
        net_kg=sum(x['net_kg'] for x in masses),blank_kg=sum(x['blank_kg'] for x in masses),
        person_h=sum(x['person_h'] or 0 for x in operations),machine_h=sum(x['machine_h'] or 0 for x in operations),
        labor_complete=scope,changed=changed,geometry_signature=signature(p),source_sha256=source['sha256'],
        full_cost=None,selling_price=None)


def gost_checks(p, s, accepted_signature=None):
    """Selected checks only. User attestations are bound to all geometry and safety inputs."""
    current = signature({'geometry':p,'safety':s})
    attested = accepted_signature == current
    basis = 'ГОСТ 12.2.022-80, изменения 1, 2; статус проверен 06.09.2026'
    rows = []
    def add(code, status, detail, clause):
        rows.append(check(code,status,detail,basis,clause,STANDARD_TEXT))
    if s.get('scope') != 'Применим':
        add('GOST_SCOPE','REVIEW','Применимость к данной установке не подтверждена; автоматические проверки стандарта не засчитываются.','Область применения')
        return rows
    def declaration(code, field, text, clause):
        value=s.get(field,'Не проверено')
        status='FAIL' if value=='Нет' else ('OK' if value=='Да' and attested else 'MISSING')
        add(code,status,text,clause)
    declaration('GUARD','guards','Ограждение доступных движущихся частей и удержание ограждений проверены; необходимость блокировки рассмотрена.','3.1–3.3')
    emergency=s.get('emergency','Не проверено')
    valid = emergency=='Остановка с любого места трассы' or (p['length']<=10000 and emergency=='Кнопки в голове и хвосте')
    add('EMERGENCY','MISSING' if emergency=='Не проверено' else ('FAIL' if not valid else ('OK' if attested else 'MISSING')),
        'До 10 м — кнопки на обоих концах; свыше 10 м — остановка с любого места. Трос по всей трассе может заменить кнопки.','3.8')
    declaration('RESTART','restart','Исключён повторный пуск до устранения аварии.','3.9')
    layout=s.get('layout','Один конвейер')
    widths={'Один конвейер':750.,'Между параллельными':1000.,'Между полностью ограждёнными':700.}
    need=1000. if s.get('moving_load')=='Да' else widths.get(layout,1000.)
    width=s.get('walkway',0.)
    finite(width,'Ширина прохода')
    add('WALKWAY','MISSING' if width<=0 else ('OK' if width>=need else 'FAIL'),f'Ширина прохода {width:g} мм; требуется ≥ {need:g} мм. Местные сужения оцениваются отдельно.','4.4')
    location=s.get('location','Помещение без постоянных рабочих мест')
    heights={'Помещение с постоянными рабочими местами':2100.,'Помещение без постоянных рабочих мест':2000.,'Галерея / тоннель / эстакада':1900.}
    height=s.get('height',0.)
    finite(height,'Высота прохода')
    hneed=heights.get(location,2100.)
    add('HEADROOM','MISSING' if height<=0 else ('OK' if height>=hneed else 'FAIL'),f'Высота прохода {height:g} мм; требуется ≥ {hneed:g} мм.','4.6')
    add('GOST_COVERAGE','REVIEW','Выбранные проверки не заменяют проверку всей КД, осмотр, измерения и испытания после изготовления и монтажа.','5.1–5.2')
    return rows


def partial_cost(result, materials, buys, rates, overhead=0., margin=0., vat=0.):
    for name, value in [('Накладные',overhead),('Маржа',margin),('НДС',vat)]:
        finite(value,name)
    if overhead>100 or vat>100 or margin>=100:
        raise ValueError('Накладные и НДС: 0–100%; маржа: 0–<100%')
    issues=[]
    total_material=total_buy=total_labor=0.
    for m in result['masses']:
        row=materials.get(m['name'],{})
        price=finite(row.get('price',0.),m['name'])
        if m['blank_kg'] and (not price or not str(row.get('source','')).strip()):
            issues.append('Цена / источник: '+m['name'])
        total_material+=m['blank_kg']*price
    for row in buys:
        qty=finite(row.get('qty',0.),'Количество BUY')
        price=finite(row.get('price',0.),'Цена BUY')
        if qty and (not isinstance(row.get('name'),str) or not row['name'].strip()):
            raise ValueError('Для каждой покупной позиции с количеством нужно наименование')
        if qty and (not price or not str(row.get('price_source','')).strip()):
            issues.append('Цена / источник: '+row.get('name','BUY'))
        total_buy+=qty*price
    for op in result['operations']:
        row=rates.get(op['resource'],{})
        ph=finite(row.get('person_rate',0.),'Ставка труда')
        mh=finite(row.get('machine_rate',0.),'Ставка оборудования')
        if not ph or (op['machine_h'] and not mh) or not str(row.get('source','')).strip():
            issues.append('Ставка / основание: '+op['name'])
        if op['person_h'] is None:
            issues.append('Новая норма: '+op['name'])
        total_labor+=(op['person_h'] or 0)*ph+(op['machine_h'] or 0)*mh
    direct=total_material+total_buy+total_labor
    finite(direct*(1+overhead/100),'Сумма затрат')
    return dict(materials=total_material,buy=total_buy,labor_and_machines=total_labor,
        known_direct=direct,known_with_overhead=direct*(1+overhead/100),issues=issues,
        full_cost=None,selling_price=None,reason='Отсутствуют 44 MAKE и подтверждённая полная калькуляция. Итог — только учтённая часть затрат.')


def snapshot_bytes(p,s,materials,buys,rates,settings,accepted_signature=None):
    calculate(p)
    return json.dumps(dict(format='tech-aero-screw-v1',inputs=p,safety=s,materials=materials,buys=buys,rates=rates,
        settings=settings,accepted_signature=accepted_signature,source_sha256=source_data()['sha256']),ensure_ascii=False,indent=2,allow_nan=False).encode('utf-8')


def load_snapshot(raw):
    if len(raw)>5_000_000:
        raise ValueError('Проект превышает 5 МБ')
    obj=json.loads(raw)
    if obj.get('format')!='tech-aero-screw-v1' or obj.get('source_sha256')!=source_data()['sha256']:
        raise ValueError('Другая версия или источник проекта')
    result=calculate(obj['inputs'])
    gost_checks(obj['inputs'],obj['safety'],obj.get('accepted_signature'))
    partial_cost(result,obj['materials'],obj['buys'],obj['rates'],**obj['settings'])
    return obj
