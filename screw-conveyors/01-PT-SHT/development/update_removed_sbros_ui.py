from pathlib import Path
import json
base=Path('outputs/Шнек 1 — параметрическая модель')
p=base/'bridge.py';s=p.read_text(encoding='utf-8');s=s.replace('"discharger_diameter": [("tube", "Диаметр сбрасывателя")],','"opening_diameter": [("tube", "Диаметр отверстия корпуса")],').replace('    "discharger_length": [("tube", "Длина сбрасывателя")],\n','');p.write_text(s,encoding='utf-8')
p=base/'index.html';s=p.read_text(encoding='utf-8');s=s.replace("['discharger_diameter','Проём сбрасывателя в трубе','мм','bodyFields','Диаметр выреза в трубе']","['opening_diameter','Отверстие в корпусе','мм','bodyFields','Сохранённое отверстие после удаления сбрасывателя']");s=s.replace(" ['discharger_length','Положение сбрасывателя','мм','bodyFields','Управляет расстоянием в подсборке'],\n",'');s=s.replace("['Сбрасыватель','отдельная деталь; назначение не установлено']","['Отверстие в корпусе','Ø '+fmt(v.opening_diameter)+' мм; деталь сбрасывателя удалена']");s=s.replace('v.pitch*v.turns+v.blade_thickness>','v.pitch*v.turns+2*v.blade_thickness>');p.write_text(s,encoding='utf-8')
p=base/'state.json';state=json.loads(p.read_text(encoding='utf-8'));v=state['values'];v['opening_diameter']=v.pop('discharger_diameter');v.pop('discharger_length',None);p.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
print('UI and parameter mapping updated')
