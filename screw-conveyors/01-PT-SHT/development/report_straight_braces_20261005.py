from pathlib import Path
import json,sys
from datetime import datetime
import pythoncom,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base))
import bridge,journal,server
state=json.loads(bridge.STATE.read_text(encoding='utf-8'))
proof_path=base/'straight_brace_restore_20261005.json'
proof=json.loads(proof_path.read_text(encoding='utf-8'))
assert proof['saved'] and state['values']['incline']==55 and state['cad_verification']['pin_joints']['ok']
sw=w.GetActiveObject('SldWorks.Application');root=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY));assert root
original_shape_features=['Проход корпуса — выборка для 55 градусов',
    'Полость обхода — нижний переход','Полость обхода — наружная ветвь','Полость обхода — верхний переход',
    'Обход корпуса — нижний переход','Обход корпуса — наружная ветвь','Обход корпуса — верхний переход']
for row in proof['working']['braces']:
    part=sw.GetOpenDocumentByName(row['file']);assert part
    bodies=list(part.GetBodies2(0,True));assert len(bodies)==1
    for name in original_shape_features:
        feature=part.FeatureByName(name)
        assert not feature or feature.IsSuppressed,name
    row['solid_bodies']=len(bodies)
    row['volume_mm3']=sum(b.GetMassProperties(1)[3] for b in bodies)*1e9
    row['bbox_m']=list(part.GetPartBox(True))
    row['shape']='original straight hollow profile; bypass features inactive'
tests=json.loads((base/'pin_joint_angle_test_20261005.json').read_text(encoding='utf-8'))
assert [r['angle'] for r in tests['checks']]==[35,55]
proof['angle_tests']=tests;proof['verification']=state['cad_verification']
proof_path.write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
if not any(row.get('repair_id')=='straight-braces-restored-20261005' for row in journal._read()['entries']):
    journal._append({'type':'model_change','title':'Возврат подкосов к прямой трубе',
        'repair_id':'straight-braces-restored-20261005','change_count':2,'snapshot':proof['snapshot'],
        'changes':[{'key':'straight_brace_1','name':'Подкос 1','before':'Обход корпуса с переходами и местной выборкой',
                    'after':'Исходная прямая полая труба; одно тело; сопряжение со втулкой сохранено'},
                   {'key':'straight_brace_2','name':'Зеркальный подкос 1','before':'Зеркальная форма обхода',
                    'after':'Зеркальная прямая полая труба; одно тело; соосность проверена'}]})
server.save_apply_outcome(state,{'ok':True,'snapshot':proof['snapshot']})
report=f'''# Возврат подкосов к прямой трубе — 05.10.2026

В рабочей сборке SolidWorks восстановлена исходная прямая форма обоих подкосов. Операции обхода корпуса, переходов, полостей обхода и местной выборки подавлены. У каждого подкоса одно сплошное тело, сохраняющее полый профиль исходной трубы. Зеркальный подкос обновлён от исходного.

Сопряжение «Подкос 1 — втулка 2 — соосность», посадка втулки между ушами 3 и 4 и связь нижней оси опоры с углом корпуса сохранены.

## Проверка

- В отдельной полной копии: перестроение успешное; ошибок и объёмных пересечений более 0,001 мм³ нет.
- Рабочая сборка после восстановления: тот же результат; файлы сохранены.
- Программа последовательно применила 35° и 55°; соосность ушей, втулки и обоих подкосов, торцевые посадки и пересечения проверены перед сохранением.
- Заданные параметры восстановлены: длина 2510 мм, труба Ø133×4 мм, винт Ø121 мм, угол 55°. Остальные параметры сохранены.
- Последняя проверка: {state['cad_verification']['components']} компонентов; ошибок сопряжений {state['cad_verification']['broken_mates']}, ошибок элементов {state['cad_verification']['feature_errors']}, объёмных пересечений более 0,001 мм³ {state['cad_verification']['positive_interferences']}.
- Два изменения записаны в журнал проекта. Полный диапазон параметров и прочность конструкции не подтверждены.

## Файлы

- Рабочая сборка: `{bridge.TOP_ASSEMBLY}`.
- Резервная копия формы с обходом: `{proof['snapshot']}`.
- `straight_brace_restore_20261005.json`: независимая копия, рабочая модель, геометрия и результаты проверки.
- `pin_joint_angle_test_20261005.json`: проверка угла с прямыми подкосами.
- `pin_joint_angle_test_before_straight_20261005.json`: предыдущая проверка с формой обхода.

Исходные файлы на рабочем столе не изменялись.
'''
(base/'Прямые подкосы — восстановление 05.10.2026.md').write_text(report,encoding='utf-8')
print('Straight brace report and journal updated',flush=True)
