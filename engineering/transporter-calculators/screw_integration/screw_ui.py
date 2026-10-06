"""Local screw-conveyor workbench. Source workbook remains read-only."""
import copy
import io
import json
import zipfile
import pandas as pd
import streamlit as st
from screw_engine import (REFERENCE, calculate, source_data, signature, gost_checks, partial_cost,
                          snapshot_bytes, load_snapshot, STANDARD_URL, STANDARD_TEXT)

LABELS = {'length':'Длина корпуса, мм','work_length':'Рабочая длина, мм','diameter':'Диаметр пера, мм',
    'pitch':'Шаг, мм','flight_inner':'Внутренний диаметр пера, мм','flight_thickness':'Толщина пера, мм',
    'shaft_diameter':'Наружный диаметр трубы вала, мм','shaft_wall':'Стенка трубы, мм','shaft_length':'Длина трубы вала, мм',
    'body_thickness':'Стенка желоба, мм','gap':'Радиальный зазор, мм','flange':'Полка желоба, мм',
    'supports':'Количество опор','chutes':'Количество патрубков','full_flights':'Полные перья, шт',
    'cut_flights':'Подрезанные перья, шт','cut_fraction':'Доля массы подрезанного пера',
    'cover_thickness':'Толщина крышки, мм','support_mass':'Масса одной опоры, кг','other_mass':'Прочая конструкция, кг',
    'waste':'Отходы, доля (0,15 = 15%)','angle':'Угол подъёма, °'}
SAFETY = dict(scope='Не проверено',guards='Не проверено',restart='Не проверено',emergency='Не проверено',
    layout='Один конвейер',moving_load='Нет',walkway=0.,height=0.,location='Помещение без постоянных рабочих мест')
STATUS={'OK':'Выполнено по введённым данным','FAIL':'Нарушение','MISSING':'Нет данных / подтверждения',
        'REVIEW':'Требуется проверка','INFO':'Сведения'}


def reset(saved=None):
    for key in list(st.session_state):
        if key.startswith('sc_'):
            del st.session_state[key]
    st.session_state.sc_saved=saved or {}
    for k,v in (saved or {}).get('inputs',REFERENCE).items():
        st.session_state['sc_p_'+k]=v
    for k,v in (saved or {}).get('safety',SAFETY).items():
        st.session_state['sc_s_'+k]=v
    st.session_state.sc_accepted=(saved or {}).get('accepted_signature')
    # A restored geometry is always used literally; no hidden regeneration of saved dimensions.
    st.session_state.sc_auto=False


def display_checks(rows):
    st.dataframe(pd.DataFrame([{'Проверка':x['code'],'Результат':STATUS[x['status']],
        'Что проверить':x['detail'],'Основание':x['basis'],'Пункт':x['clause'],'Источник':x['url']} for x in rows]),
        hide_index=True,width='stretch',column_config={'Источник':st.column_config.LinkColumn()})


def render_screw_app():
    if 'sc_saved' not in st.session_state:
        reset()
    elif 'sc_p_length' not in st.session_state and 'sc_draft' in st.session_state:
        reset(st.session_state.sc_draft)
    data=source_data()
    saved=st.session_state.sc_saved
    st.subheader('Шнековый транспортер · 24.SHT.G')
    st.caption('Эталон D300 / P300 / корпус 6100 мм. Параметрическая оценка по вашей книге v11. Все данные остаются на этом ПК.')
    with st.sidebar:
        st.header('Шнек 24.SHT.G')
        st.button('Вернуть эталон 24',on_click=reset,key='sc_reset')
        f=st.file_uploader('Открыть проект шнека',type=['json'],key='sc_upload')
        if st.button('Прочитать проект шнека',disabled=f is None,key='sc_load'):
            try:
                obj=load_snapshot(f.getvalue())
                reset(obj)
                st.rerun()
            except (ValueError,KeyError,TypeError,AttributeError,OverflowError) as exc:
                st.error(f'Проект не загружен: {exc}')
        st.caption('25.SHT.G сохранён как отдельный эталон в источниках. Его нормы не применяются к 24.SHT.G.')
    geo,cost,checks,reference=st.tabs(['1 · Конструкция','2 · Затраты','3 · Ограничения и ГОСТ','4 · Источник и выгрузка'])
    p={}
    with geo:
        st.info('Перестроение здесь обновляет расчётные размеры, массу и трудоёмкость. CAD-модель и рабочие чертежи приложение не изменяет.')
        auto=st.checkbox('Связать длины и количество полных перьев с корпусом и шагом',key='sc_auto')
        st.caption('При связи: рабочая длина = корпус − 100 мм; труба = корпус − 106 мм; полные перья = целая часть рабочей длины / шага. Подрезка задаётся отдельно по КД.')
        cols=st.columns(3)
        keys=['length','diameter','pitch','flight_inner','flight_thickness','shaft_diameter','shaft_wall',
              'body_thickness','gap','flange','angle','work_length','shaft_length','full_flights','cut_flights','cut_fraction','supports','chutes']
        for i,k in enumerate(keys):
            if auto and k in ('work_length','shaft_length','full_flights'):
                value=p['length']-100 if k=='work_length' else (p['length']-106 if k=='shaft_length' else int((p['length']-100)/p['pitch']) if p['pitch']>0 else 0)
                st.session_state['sc_p_'+k]=value
            with cols[i%3]:
                p[k]=st.number_input(LABELS[k],step=1 if isinstance(REFERENCE[k],int) else (0.05 if k=='cut_fraction' else 1.),
                    key='sc_p_'+k,disabled=auto and k in ('work_length','shaft_length','full_flights'))
        for i,(k,label) in enumerate([('flight_material','Материал пера'),('shaft_material','Материал вала'),('body_material','Материал корпуса')]):
            with cols[i]:
                p[k]=st.selectbox(label,['AISI 316','AISI 316L','AISI 316Ti'],key='sc_p_'+k)
        with st.expander('Массы недостающих групп и отходы'):
            for k in ('cover_thickness','support_mass','other_mass','waste'):
                p[k]=st.number_input(LABELS[k],step=.01 if k=='waste' else 1.,key='sc_p_'+k)
        try:
            result=calculate(p,data)
        except (ValueError,OverflowError) as exc:
            st.error(f'Расчёт остановлен: {exc}')
            st.stop()
        a,b,c=st.columns(3)
        a.metric('Известная масса MAKE',f"{result['net_kg']:.3f} кг")
        b.metric('Потребность с отходами',f"{result['blank_kg']:.3f} кг")
        c.metric('Труд по известным нормам',f"{result['person_h']:.3f} ч")
        if not result['labor_complete']:
            st.warning('Трудоёмкость неполная: норма формирования пера вышла за область применения.')
        st.caption(f"Машинное время: {result['machine_h']:.3f} ч. BUY и отсутствующие MAKE в массу изделия не включены.")
        st.dataframe(pd.DataFrame(result['masses']).rename(columns={'name':'Группа','net_kg':'Нетто, кг',
            'blank_kg':'С отходами, кг','material':'Материал','source':'Основание'}),hide_index=True,width='stretch')
        st.caption('Желоб рассчитан как полуцилиндр с двумя полками. Формы патрубков, торцевых деталей, сварных швов и крепежа уточняются по КД.')
    s={}
    with checks:
        st.markdown(f'[ГОСТ 12.2.022-80 — действующий статус Росстандарта]({STANDARD_URL}) · [Текст с изменениями 1 и 2]({STANDARD_TEXT})')
        st.caption('Выбранные проверки для отдельного конвейера. ГОСТ не распространяется на транспорт людей, установки на судах, в шахтах/карьерах и конвейеры как узлы другого технологического оборудования. Для исключений нужен свой нормативный набор.')
        s['scope']=st.selectbox('Применимость ГОСТ 12.2.022-80 к установке',['Не проверено','Применим','Требуется другой нормативный набор'],key='sc_s_scope')
        s['guards']=st.selectbox('Ограждения и удержание / блокировки проверены по КД',['Не проверено','Да','Нет'],key='sc_s_guards')
        s['restart']=st.selectbox('Блокировка повторного пуска проверена',['Не проверено','Да','Нет'],key='sc_s_restart')
        s['emergency']=st.selectbox('Аварийная остановка',['Не проверено','Кнопки в голове и хвосте','Остановка с любого места трассы','Отсутствует'],key='sc_s_emergency')
        cols=st.columns(2)
        with cols[0]:
            s['layout']=st.selectbox('Расположение прохода',['Один конвейер','Между параллельными','Между полностью ограждёнными'],key='sc_s_layout')
            s['moving_load']=st.selectbox('Над трассой движутся загрузочные / разгрузочные устройства',['Нет','Да'],key='sc_s_moving_load')
            s['walkway']=st.number_input('Ширина прохода в свету, мм',min_value=0.,step=50.,key='sc_s_walkway')
        with cols[1]:
            s['location']=st.selectbox('Место установки',['Помещение без постоянных рабочих мест','Помещение с постоянными рабочими местами','Галерея / тоннель / эстакада'],key='sc_s_location')
            s['height']=st.number_input('Высота прохода в свету, мм',min_value=0.,step=50.,key='sc_s_height')
        st.caption('Подтверждение относится к текущим размерам и размещению. После их изменения ограждения и управление проверяются заново.')
        if st.button('Зафиксировать проверку введённых решений для этой конструкции',key='sc_attest'):
            st.session_state.sc_accepted=signature({'geometry':p,'safety':s})
        normative=gost_checks(p,s,st.session_state.sc_accepted)
        display_checks(normative+result['checks'])
        if any(r['status']=='FAIL' for r in normative):
            st.error('Есть нарушения выбранных требований ГОСТ. Исправьте размещение или защитные устройства.')
        st.warning('Полная проверка по ГОСТ и выпуск КД не завершены. Диаметр, шаг, допустимая нагрузка и прочность не объявляются соответствующими ГОСТ на основании этих проверок.')
    with cost:
        st.warning('Полная себестоимость не определена: в источнике отсутствуют 44 MAKE, цены BUY и утверждённые ставки. Ниже можно оценивать известную часть затрат.')
        st.caption('Цены — рубли без НДС. Указывайте точную марку, сортамент, дату и поставщика в основании цены. Исторический коэффициент ×1,25 автоматически не начисляется.')
        mat_default=[dict(name=m['name'],material=m['material'],price=0.,source='') for m in result['masses']]
        for row in mat_default:
            row.update(saved.get('materials',{}).get(row['name'],{}))
        # Prices are specification-specific: changing geometry or grades resets editors to unpriced inputs.
        quote_sig=signature(p)
        if st.session_state.get('sc_quote_sig') not in (None,quote_sig):
            st.session_state.sc_saved={}
            saved={}
            mat_default=[dict(name=m['name'],material=m['material'],price=0.,source='') for m in result['masses']]
            st.info('Конструкция изменена. Цены и ставки для нового варианта нужно проверить и ввести заново.')
        st.session_state.sc_quote_sig=quote_sig
        mat_df=st.data_editor(pd.DataFrame(mat_default),hide_index=True,width='stretch',key='sc_materials_'+quote_sig,
            disabled=['name','material'],column_config={'name':'Группа','material':'Материал','price':st.column_config.NumberColumn('₽/кг',min_value=0.),'source':'Основание цены'})
        materials={r['name']:{'price':r['price'],'source':r['source']} for r in mat_df.to_dict('records')}
        st.subheader('Покупные изделия')
        st.caption('Количество из эталона не масштабируется автоматически. При перестроении проверьте крепёж, опоры, привод и добавьте новые строки.')
        default_buy=saved.get('buys') or [r|dict(price=0.,price_source='') for r in data['buy']]
        buy_df=st.data_editor(pd.DataFrame(default_buy),num_rows='dynamic',hide_index=True,width='stretch',key='sc_buys_'+quote_sig,
            column_config={'name':'Наименование','qty':st.column_config.NumberColumn('Количество',min_value=0.),
                'price':st.column_config.NumberColumn('₽/шт',min_value=0.),'price_source':'Основание цены','source':'Источник состава'})
        for column in ('name','source','price_source'):
            buy_df[column]=buy_df[column].fillna('')
        buys=buy_df.to_dict('records')
        st.subheader('Труд и оборудование')
        op_df=pd.DataFrame(result['operations']).rename(columns={'name':'Операция','person_h':'Нормо-ч','machine_h':'Машино-ч','resource':'Центр','source':'Основание','status':'Статус нормы'})
        st.dataframe(op_df,hide_index=True,width='stretch')
        rate_rows=[dict(resource=op['resource'],person_rate=0.,machine_rate=0.,source='') for op in result['operations']]
        for row in rate_rows:
            row.update(saved.get('rates',{}).get(row['resource'],{}))
        rates_df=st.data_editor(pd.DataFrame(rate_rows),hide_index=True,width='stretch',key='sc_rates_'+quote_sig,disabled=['resource'],
            column_config={'resource':'Центр','person_rate':st.column_config.NumberColumn('Труд, ₽/ч',min_value=0.),
                'machine_rate':st.column_config.NumberColumn('Оборудование, ₽/ч',min_value=0.),'source':'Основание ставки / дата'})
        rates={r['resource']:{k:v for k,v in r.items() if k!='resource'} for r in rates_df.to_dict('records')}
        settings={}
        for k,label in [('overhead','Накладные на учтённые прямые затраты, %'),('margin','Рентабельность в цене, %'),('vat','НДС при продаже, %')]:
            settings[k]=st.number_input(label,min_value=0.,max_value=99.9 if k=='margin' else 100.,
                value=float(saved.get('settings',{}).get(k,0.)),key='sc_cfg_'+k)
        try:
            costs=partial_cost(result,materials,buys,rates,**settings)
        except (ValueError,TypeError) as exc:
            st.error(f'Затраты не рассчитаны: {exc}')
            st.stop()
        st.metric('Учтённые затраты с накладными',f"{costs['known_with_overhead']:,.0f} ₽".replace(',',' '))
        st.caption('Маржа и НДС сохранены для проекта. Цена продажи появится после закрытия состава и проверки полной калькуляции; сейчас она не рассчитывается.')
        st.dataframe(pd.DataFrame([{'Статья':label,'Учтено, ₽':costs[k]} for k,label in [('materials','Известные материалы'),('buy','Покупные'),('labor_and_machines','Труд и оборудование'),('known_direct','Всего прямые')]]),hide_index=True,width='stretch')
        with st.expander(f"Не заполнено цен и ставок: {len(costs['issues'])}"):
            st.write('\n'.join('• '+x for x in costs['issues']))
    with reference:
        st.write(data['filename'])
        st.caption('Источник сохранён как отдельный снимок значений и формул. Исходный Excel не изменён. Ссылки на листы доступны в таблицах.')
        st.dataframe(pd.DataFrame([
            {'Показатель':'Известная масса MAKE, кг','Эталон v11':294.0871777022552,'Текущий вариант':result['net_kg']},
            {'Показатель':'Потребность с отходами, кг','Эталон v11':338.2002543575934,'Текущий вариант':result['blank_kg']},
            {'Показатель':'Труд, ч','Эталон v11':312.907,'Текущий вариант':result['person_h']},
            {'Показатель':'Машины, ч','Эталон v11':152.74,'Текущий вариант':result['machine_h']}]),hide_index=True,width='stretch')
        st.caption('Это сверка переноса формул, а не подтверждение полноты конструкции или себестоимости. Неполные часы отмечены в разделе конструкции.')
        with st.expander('30 исходных MAKE — справочная структура, без повторного включения в массу'):
            st.dataframe(pd.DataFrame(data['make']),hide_index=True,width='stretch')
        with st.expander('Отдельный эталон 25.SHT.G'):
            st.write('D200 / P200; винтовая часть 2873 мм; сборка с осями 3165,5 мм. Масса сборки по чертежу 63,16 кг. Семейство 25 не пересчитывается нормами семейства 24.')
        raw=snapshot_bytes(p,s,materials,buys,rates,settings,st.session_state.sc_accepted)
        st.session_state.sc_draft=json.loads(raw)
        st.download_button('Сохранить проект шнека',raw,'Шнек_24_проект.json',mime='application/json')
        report=io.BytesIO()
        with zipfile.ZipFile(report,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('Проект.json',raw)
            z.writestr('Итоги.json',json.dumps(dict(result=result,costs=costs,checks=normative),ensure_ascii=False,indent=2,allow_nan=False))
            for name,rows in [('Масса',result['masses']),('Операции',result['operations']),('Проверки',normative+result['checks']),('BUY',buys),('MAKE_справочно',data['make'])]:
                frame=pd.DataFrame(rows)
                # Protect spreadsheet users from formula interpretation of editable strings.
                for col in frame.columns:
                    frame[col]=frame[col].map(lambda x: "'"+x if isinstance(x,str) and x.startswith(('=','+','-','@')) else x)
                z.writestr(name+'.csv',frame.to_csv(index=False,sep=';').encode('utf-8-sig'))
            z.writestr('Прочитать.txt','Предварительный расчёт 24.SHT.G. CSV открываются в Excel. Полная себестоимость и соответствие всем требованиям ГОСТ не подтверждены.\nИсточник: '+data['filename']+'\nSHA256: '+data['sha256']+'\nГОСТ: '+STANDARD_URL+'\n'+STANDARD_TEXT)
        st.download_button('Скачать расчёт и протокол проверок',report.getvalue(),'Шнек_24_расчет.zip',mime='application/zip')
