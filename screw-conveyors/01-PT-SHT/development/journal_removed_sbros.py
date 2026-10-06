from pathlib import Path
import sys,json,py_compile
b=Path('outputs/Шнек 1 — параметрическая модель').resolve();p=b/'journal.py';s=p.read_text(encoding='utf-8').replace('    "discharger_diameter": "Проём сбрасывателя в трубе",','    "opening_diameter": "Отверстие в корпусе",');p.write_text(s,encoding='utf-8')
sys.path.insert(0,str(b));import journal,bridge
state=json.loads((b/'state.json').read_text(encoding='utf-8'));assert not bridge.validate(state['values'])
if not any(e.get('repair_id')=='remove-sbrosivatel-20261004' for e in journal._read()['entries']):
 changes=[{'key':'sbrosivatel','name':'Сбрасыватель','before':'1 компонент в рабочей сборке','after':'Удалён; 204 компонента вместо 205; 3 зависимых сопряжения удалены'}, {'key':'opening_diameter','name':'Отверстие в корпусе','before':'Ø110 мм с установленной деталью','after':'Ø110 мм сохранено по указанию пользователя; отдельный параметр интерфейса'}, {'key':'sbrosivatel_parameters','name':'Параметры удалённой детали','before':'Размеры детали и зависимые уравнения','after':'Уравнения удалены; поле положения детали убрано из интерфейса'}]
 journal._append({'type':'model_change','repair_id':'remove-sbrosivatel-20261004','title':'Удаление сбрасывателя с сохранением отверстия','change_count':len(changes),'changes':changes})
for name in ['bridge.py','journal.py']:py_compile.compile(str(b/name),doraise=True)
print('validation and journal OK')
