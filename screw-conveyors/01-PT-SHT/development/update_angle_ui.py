from pathlib import Path

path = next(Path('outputs').glob('Шнек 1 — параметрическая модель')) / 'index.html'
html = path.read_text(encoding='utf-8')

def replace_once(old, new):
    global html
    count = html.count(old)
    if count != 1:
        raise RuntimeError(f'Expected one match, got {count}: {old[:80]}')
    html = html.replace(old, new)

replace_once(
    "function selection(){return {tube:$('tubeChoice').value,screw:$('screwChoice').value,material:$('materialChoice').value}}",
    "function selection(){return {tube:$('tubeChoice').value,screw:$('screwChoice').value,material:$('materialChoice').value}}\nfunction designMode(){return $('angleMode').value}",
)
replace_once(
    "function render(){const v=values(),bore=v.tube_diameter-2*v.tube_wall,gap=(bore-v.screw_diameter)/2;",
    "function render(){const v=values(),bore=v.tube_diameter-2*v.tube_wall,gap=(bore-v.screw_diameter)/2;const gostMode=designMode()==='gost';$('incline').min='0';$('incline').max=gostMode?'20':'89.999';$('angleModeHint').textContent=gostMode?'Допустимый ввод: 0–20°. Текущие 55° нужно изменить перед применением.':'Углы свыше 20° относятся к специальному проекту; 55° сохранены по заданию.';",
)
replace_once(
    "$('apply').disabled=gap<=0||v.pitch*v.turns>v.working_length+270||v.turns%1!==0||defs.some(([id])=>!Number.isFinite(v[id])||v[id]<=0);",
    "$('apply').disabled=gap<=0||v.pitch*v.turns>v.working_length+270||v.turns%1!==0||v.incline>=90||(gostMode&&v.incline>20)||defs.some(([id])=>!Number.isFinite(v[id])||v[id]<0||(id!=='incline'&&v[id]===0));",
)
replace_once(
    "if(value==='unspecified')return 'не выбрана';",
    "if(value==='unspecified')return 'не выбрана';if(value==='gost')return 'ГОСТ 2037-82 · 0–20°';if(value==='special')return 'специальное исполнение';",
)
replace_once(
    "catalog=items;materials=bulk;original=state.values;makeFields(state.values);",
    "catalog=items;materials=bulk;original=state.values;$('angleMode').value=state.design_mode||'special';$('angleMode').onchange=render;makeFields(state.values);",
)
replace_once(
    "body:JSON.stringify({values:values(),selection:selection()})",
    "body:JSON.stringify({values:values(),selection:selection(),design_mode:designMode()})",
)
path.write_text(html, encoding='utf-8')
