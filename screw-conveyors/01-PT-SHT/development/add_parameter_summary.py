from pathlib import Path

page = Path('outputs/Шнек 1 — параметрическая модель/index.html')
html = page.read_text(encoding='utf-8')

def replace_once(before, after):
    global html
    if html.count(before) != 1:
        raise SystemExit(f'Expected one match: {before[:100]!r}; found {html.count(before)}')
    html = html.replace(before, after, 1)

replace_once(
    '</div><div><div class="rule"></div><div class="caption">',
    '</div><div id="parameterSummary" class="parameter-summary"></div>'
    '<div><div class="rule"></div><div class="caption">',
)
replace_once('</style>', '''
.hero{grid-template-columns:minmax(0,1fr) 320px}
.visual{min-height:520px}
.metric-card{height:520px;display:block;overflow-y:auto;scrollbar-color:#b9c9c9 transparent}
.parameter-summary{margin-top:18px;border-top:1px solid var(--line);padding-top:15px}
.parameter-summary h3{font-size:13px;margin:0 0 9px}
.summary-group{margin:0 0 14px}
.summary-group h4{font-size:10px;letter-spacing:.09em;text-transform:uppercase;color:#75898c;margin:0 0 5px}
.summary-row{display:flex;justify-content:space-between;gap:12px;padding:5px 0;border-bottom:1px solid #eef2f0;font-size:10px;line-height:1.35}
.summary-row span{color:#6b7d82;min-width:0}.summary-row b{color:#203842;text-align:right;max-width:58%;overflow-wrap:anywhere}
@media(max-width:1100px){.hero{grid-template-columns:minmax(0,1fr) 290px}}
@media(max-width:760px){.hero{grid-template-columns:1fr}.visual{min-height:400px}.metric-card{height:440px}}
</style>''')

helper = '''function summaryRow(label,value){
 const row=document.createElement('div');row.className='summary-row';
 const name=document.createElement('span');name.textContent=label;
 const number=document.createElement('b');number.textContent=value;
 row.append(name,number);return row;
}
function summaryGroup(root,title,rows){
 const group=document.createElement('section');group.className='summary-group';
 const heading=document.createElement('h4');heading.textContent=title;group.append(heading);
 for(const [label,value] of rows)group.append(summaryRow(label,value));root.append(group);
}
function inputSummary(id,unit){
 const raw=$(id).value.trim();if(!raw)return 'не задано';
 const value=Number(raw.replace(',','.'));
 return Number.isFinite(value)?`${fmt(value)} ${unit}`:'не задано';
}
function selectedText(id){return $(id).selectedOptions[0]?.textContent||'не выбран'}
function renderParameterSummary(v){
 const root=$('parameterSummary'),scroll=root.parentElement.scrollTop;
 root.replaceChildren();const heading=document.createElement('h3');
 heading.textContent='Выбранные параметры';root.append(heading);
 for(const [title,target] of [['Корпус и патрубок','bodyFields'],['Винт и вал','screwFields'],['Опора','supportFields']]){
  const rows=defs.filter(([, , ,place])=>place===target).map(([id,label,unit])=>
   [label,Number.isFinite(v[id])?`${fmt(v[id])} ${unit}`:'не задано']);
  summaryGroup(root,title,rows);
 }
 summaryGroup(root,'Выбор по стандартам',[
  ['Труба',selectedText('tubeChoice')],['Винт',selectedText('screwChoice')],
  ['Марка стали',selectedText('materialChoice')],['Режим угла',selectedText('angleMode')],
  ['Груз',selectedText('cargoPreset')],
 ]);
 summaryGroup(root,'Данные расчёта',[
  ['Частота винта',inputSummary('calcRpm','об/мин')],
  ['Требуемая подача',inputSummary('calcTarget','м³/ч')],
  ['Плотность груза',inputSummary('calcDensity','кг/м³')],
  ['Крупность',inputSummary('calcLump','мм')],
  ['Температура',inputSummary('calcTemp','°C')],
  ['Масса на испытании',inputSummary('calcMass','кг')],
  ['Время испытания',inputSummary('calcTime','с')],
 ]);
 summaryGroup(root,'Режим эксплуатации',[
  ['Пусков в час',inputSummary('surveyStarts','1/ч')],
  ['Длительность включения',inputSummary('surveyDuration','мин')],
  ['Пуск с заполненным шнеком',selectedText('surveyLoaded')],
  ['Плотность смеси',inputSummary('surveyDensity','кг/м³')],
 ]);
 root.parentElement.scrollTop=scroll;
}
'''
replace_once('function render(){', helper + 'function render(){')
replace_once('updateSchematic(v.incline);',
             'updateSchematic(v.incline);renderParameterSummary(v);')
replace_once("$('materialSource').href=catalog.material.url;",
             "$('materialSource').href=catalog.material.url;$('materialChoice').onchange=render;")
replace_once("$('cargoPreset').onchange=()=>{describeCargo();queueCalculation()};",
             "$('cargoPreset').onchange=()=>{describeCargo();renderParameterSummary(values());queueCalculation()};")
replace_once("$(id).addEventListener('input',queueCalculation);",
             "$(id).addEventListener('input',()=>{renderParameterSummary(values());queueCalculation()});")
replace_once('calcReady=true;runCalculation();',
             'renderParameterSummary(values());calcReady=true;runCalculation();')
replace_once("$('questionnaireStatus').textContent=Object.values(data).some(x=>x!==null)?'Сохранённые ответы загружены.':'Ответы ещё не заполнены.'",
             "$('questionnaireStatus').textContent=Object.values(data).some(x=>x!==null)?'Сохранённые ответы загружены.':'Ответы ещё не заполнены.';if($('incline'))renderParameterSummary(values())")
replace_once('load();loadQuestionnaire();',
             "for(const id of ['surveyStarts','surveyDuration','surveyDensity'])$(id).addEventListener('input',()=>{if($('incline'))renderParameterSummary(values())});"
             "$('surveyLoaded').addEventListener('change',()=>{if($('incline'))renderParameterSummary(values())});"
             'load();loadQuestionnaire();')
page.write_text(html, encoding='utf-8')
print('Updated', page)
