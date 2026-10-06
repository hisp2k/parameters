from pathlib import Path
import sys,json,copy
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import journal,bridge
p=base/'state.json';before=json.loads(p.read_text(encoding='utf-8'));after=copy.deepcopy(before);after['values']['turns']=24
assert not bridge.validate(after['values'])
after['last_applied']=journal._now();p.write_text(json.dumps(after,ensure_ascii=False,indent=2),encoding='utf-8')
journal.record_apply(before,after)
if not any(x.get('repair_id')=='screw-clearance-20261004' for x in journal._read()['entries']):
 changes=[
  {'key':'screw_extent','name':'Винтовая часть и верхняя торцевая деталь','before':'26×105 мм; торец на 2765 мм','after':'24×105 мм; верхний торец на 85 + шаг × витки = 2605 мм; нижний торец перенесён на 5 мм ниже начала лопасти'},
  {'key':'prototype_body','name':'Скрытое тело По траектории1','before':'Дублирует первый листовой виток','after':'Удалено финальной операцией Удаление тела; 24 рабочих листовых тела и развёртки сохранены'},
  {'key':'retainer_mate','name':'Осевая связь ограничителя привода','before':'Ограничитель имел только соосность; пересекал вал','after':'Добавлена посадка на торец верхнего вала; смещение 10 мм наружу'},
  {'key':'guard','name':'Проверка длины винтовой части','before':'Проверялась только полная длина вала','after':'Для геометрии этой модели: шаг × витки + толщина лопасти ≤ рабочая длина + 85 мм'}]
 journal._append({'type':'model_change','repair_id':'screw-clearance-20261004','title':'Исправление винта и осевой фиксации привода','change_count':len(changes),'changes':changes})
html=base/'index.html';text=html.read_text(encoding='utf-8');text=text.replace('v.pitch*v.turns>v.working_length+270','v.pitch*v.turns+v.blade_thickness>v.working_length+85');html.write_text(text,encoding='utf-8')
print('state, journal, UI updated')
