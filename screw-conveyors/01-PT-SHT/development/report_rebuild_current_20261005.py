from pathlib import Path
from datetime import datetime
import sys,json

base=Path('outputs/Шнек 1 — параметрическая модель').resolve()
sys.path.insert(0,str(base))
import journal
rows=json.loads((base/'geometry_rebuild_latest.json').read_text(encoding='utf-8'))
assert [r['parameter'] for r in rows]==['working_length','tube_diameter','incline']
state=json.loads((base/'state.json').read_text(encoding='utf-8'))
names={'working_length':'Рабочая длина','tube_diameter':'Наружный диаметр трубы','incline':'Угол к горизонтали'}
lines=['# Повторная проверка перестроения — 05.10.2026','',
       'Проверка выполнена после установки параметрических седел ушей. Сначала принудительно перестроена исходная общая сборка, затем отдельно изменены длина, диаметр и угол. После каждого испытания исходные значения восстановлены через программный мост с повторным контролем и сохранением.','',
       '| Параметр | Цикл проверки | Результат |','|---|---|---|']
changes=[]
for row in rows:
    verification=row['restored_verification']
    assert verification['components']==204
    assert all(verification[k]==0 for k in ('suppressed','broken_mates','feature_errors','positive_interferences'))
    if row['applied']:
        assert all(row['verification'][k]==0 for k in ('suppressed','broken_mates','feature_errors','positive_interferences'))
    unit='°' if row['parameter']=='incline' else 'мм'
    cycle=f"{row['before']:g} → {row['tested']:g} → {row['before']:g} {unit}"
    outcome='Перестроение успешно; ошибки и пересечения отсутствуют' if row['applied'] else 'Вариант отклонён; исходная сборка восстановлена без ошибок и пересечений'
    lines.append(f"| {names[row['parameter']]} | {cycle} | {outcome} |")
    changes.append({'key':row['parameter'],'name':names[row['parameter']], 'before':cycle,'after':outcome})
lines.extend(['','## Ограничения и ошибки',''])
for row in rows:
    if not row['applied']:
        lines.extend([f"### {names[row['parameter']]}: {row['tested']:g}",'',*row.get('errors',[]),''])
lines.extend(['Проверены отдельные варианты; полный диапазон и одновременное изменение нескольких параметров не подтверждены. Диаметры всех четырёх седел ушей дополнительно измерены в успешных вариантах и после восстановления. Контроль объёмных пересечений выполнен с порогом 0,001 мм³ и условным сборочным представлением резьбы.','',
              '## Сохранённое состояние',''])
v=state['cad_verification'];g=v['measured_geometry']
assert all(v[k]==0 for k in ('suppressed','broken_mates','feature_errors','positive_interferences'))
lines.extend([f"- Контрольная проверка: {v['timestamp']}.",
              f"- Рабочая длина {g['working_length']:g} мм; полная длина {g['working_length']+270:g} мм.",
              f"- Наружный диаметр трубы {g['tube_diameter']:g} мм; стенка {state['values']['tube_wall']:g} мм.",
              f"- Фактический угол {g['incline']:.2f}° от горизонтали; заданные 55° остаются невыполненным требованием.",
              '- 204 компонента; 0 подавленных; 0 ошибок сопряжений и элементов; 0 пересечений выше порога.','',
              'Для изменения угла остаётся необходимой доработка отверстия верхнего патрубка и проверка опоры при целевых 55°. Производительность, привод, прочность и готовность к производству этой проверкой не подтверждены.','',
              '## Протокол','',
              '`geometry_rebuild_latest.json` содержит результаты трёх испытаний, ошибки отклонённого варианта, реальные размеры и проверки восстановления. Идентичный протокол сохранён в отдельном файле `geometry_rebuild_YYYYMMDD-HHMMSS.json`. Перед каждым применением программа создала резервную копию в `snapshots/`.',''])
(base/'Повторная проверка перестроения 05.10.2026.md').write_text('\n'.join(lines),encoding='utf-8')
identity='rebuild-check-'+v['timestamp']
if not any(e.get('verification_id')==identity for e in journal._read()['entries']):
    journal._append({'type':'model_check','title':'Повторная проверка перестроения: длина, диаметр, угол',
                    'verification_id':identity,'change_count':0,'check_count':3,'changes':changes})
print('Results:',[(r['parameter'],r['applied']) for r in rows],flush=True)
print('Restored geometry:',g,flush=True)
