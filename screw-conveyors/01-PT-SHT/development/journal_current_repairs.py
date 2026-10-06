from pathlib import Path
import json,sys
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import journal
names=json.loads((base/'all_mate_repairs_20261004.json').read_text(encoding='utf-8'))
names+=['Совпадение98','Совпадение99','Концентричный85','Опора: Совпадение18','Опора: Совпадение22','Опора: Расстояние5','Опора: Расстояние6','Опора: Расстояние8','Опора: Расстояние9']
journal.record_assembly_repair(sorted(set(names)),'all-links-20261004')
if not any(x.get('repair_id')=='upper-and-bindings-20261004' for x in journal._read()['entries']):
 changes=[
  {'key':'upper','name':'Верхняя обойма','before':'Пересечения колец, корпуса и манжеты','after':'Локальная ревизия UR04: канавки 2.65 мм, кольца 2.5 мм, манжета 50×70×10; отдельная подсборка: 0 пересечений'},
  {'key':'unused_sketch','name':'Вспомогательный Эскиз1 главной сборки','before':'3 потерянные внешние связи; нет дочерних операций','after':'Геометрия архивирована в archived_auxiliary_sketch_20261004.json; неиспользуемый эскиз удалён'},
  {'key':'cad_binding','name':'Связь программы параметров и чертежей с винтом','before':'Путь к альтернативной копии CAD','after':'Путь к фактическому винту рабочей сборки; контроль принадлежности всех трёх рабочих узлов и перестроение главной сборки'}]
 journal._append({'type':'model_change','repair_id':'upper-and-bindings-20261004','title':'Верхняя обойма и связи проекта','change_count':len(changes),'changes':changes})
print('journal saved')
