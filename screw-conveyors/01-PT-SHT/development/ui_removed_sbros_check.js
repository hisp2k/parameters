
const defs=[
 ['working_length','Рабочая длина','мм','bodyFields','Труба + вал · общая база'],
 ['tube_diameter','Диаметр трубы','мм','bodyFields','Наружный размер'],
 ['tube_wall','Стенка трубы','мм','bodyFields','Толщина корпуса'],
 ['incline','Угол наклона','°','bodyFields','Управляет положением патрубков'],
 ['inlet_diameter','Диаметр патрубка','мм','bodyFields','Входной патрубок'],
 ['inlet_length','Длина патрубка','мм','bodyFields','Входной патрубок'],
 ['inlet_wall','Стенка патрубка','мм','bodyFields','Входной патрубок'],
 ['flange_thickness','Толщина фланца','мм','bodyFields','Труба в сборе'],
 ['mounting_hole_diameter','Отверстие крепления','мм','bodyFields','Исходная переменная «Отверстие М8»'],
 ['opening_diameter','Отверстие в корпусе','мм','bodyFields','Сохранённое отверстие после удаления сбрасывателя'],
 ['screw_diameter','Диаметр винта','мм','screwFields','Наружный размер спирали'],
 ['pitch','Шаг винта','мм','screwFields','Осевое расстояние'],
 ['blade_thickness','Толщина лопасти','мм','screwFields','Винтовая поверхность'],
 ['shaft_diameter','Диаметр вала','мм','screwFields','Наружный размер'],
 ['shaft_wall','Стенка вала','мм','screwFields','Полый вал'],
 ['turns','Число витков','шт','screwFields','Целое значение'],
 ['support_short_beam_length','Длина балки 1 опоры','мм','supportFields','Симметричное вытягивание · 250 мм исходно'],
 ['support_long_beam_length','Длина балки 2 опоры','мм','supportFields','Симметричное вытягивание · 500 мм исходно']
];
const PORT_COUNTS={inlet:1,outlet:1,wash:2};let original={},catalog={},materials={},calcReady=false,calcTimer=0,calcSeq=0;const $=id=>document.getElementById(id);
function fmt(n){return Number(n).toLocaleString('ru-RU',{maximumFractionDigits:2})}
function toast(message,bad=false){const el=$('toast');el.textContent=message;el.style.background=bad?'#8f4343':'#172c37';el.classList.add('show');setTimeout(()=>el.classList.remove('show'),5000)}
function values(){return Object.fromEntries(defs.map(([id])=>{const raw=$(id).value.trim();return [id,raw===''?NaN:Number(raw.replace(',','.'))]}))}
function selection(){return {tube:$('tubeChoice').value,screw:$('screwChoice').value,material:$('materialChoice').value}}
function designMode(){return $('angleMode').value}
function schematicPose(angle){
 const radians=Math.max(0,Math.min(angle,89.999))*Math.PI/180;
 const co=Math.cos(radians),si=Math.sin(radians);
 const scale=Math.min(1,640/(690*co+145*si),300/(690*si+145*co));
 const x=110,y=260+135*si,pivotX=88,pivotY=96;
 const a=scale*co,b=-scale*si,c=scale*si,d=scale*co;
 const e=x-a*pivotX-c*pivotY,f=y-b*pivotX-d*pivotY;
 const r=88,arcEndX=x+r*co,arcEndY=y-r*si;
 const arc=radians<0.000001?'':`M ${x+r} ${y} A ${r} ${r} 0 0 0 ${arcEndX} ${arcEndY}`;
 return {matrix:`matrix(${a} ${b} ${c} ${d} ${e} ${f})`,x,y,arc,co,si,scale,
  labelX:x+125,labelY:Math.min(440,y+75*scale+20)};
}
function setSchematicLine(id,x1,y1,x2,y2){
 const line=$(id);line.setAttribute('x1',x1);line.setAttribute('y1',y1);
 line.setAttribute('x2',x2);line.setAttribute('y2',y2);
}
function setSchematicText(id,x,y,label){
 const element=$(id);element.setAttribute('x',x);element.setAttribute('y',y);
 element.textContent=label;
}
function updatePortGeometry(pose,angle){
 const {x,y,co,si,scale}=pose;
 const along=fraction=>({x:x+615*scale*fraction*co,y:y-615*scale*fraction*si});
 const inlet=along(.18),outlet=along(.82);
 const reach=68;
 setSchematicLine('portInTube',inlet.x-reach,inlet.y,inlet.x-9,inlet.y);
 setSchematicLine('portInArrow',inlet.x-reach-5,inlet.y,inlet.x-12,inlet.y);
 setSchematicLine('portOutTube',outlet.x+9,outlet.y,outlet.x+reach,outlet.y);
 setSchematicLine('portOutArrow',outlet.x+12,outlet.y,outlet.x+reach+5,outlet.y);
 const r=30,mainArc=(point)=>angle<.001?'':`M ${point.x+r} ${point.y} A ${r} ${r} 0 0 0 ${point.x+r*co} ${point.y-r*si}`;
 $('portInArc').setAttribute('d',mainArc(inlet));
 $('portOutArc').setAttribute('d',mainArc(outlet));
 setSchematicText('portInText',Math.max(60,inlet.x-reach/2),inlet.y-18,`ВХОД · ${fmt(angle)}°`);
 setSchematicText('portOutText',Math.min(720,outlet.x+reach/2),outlet.y-18,`ВЫХОД · ${fmt(angle)}°`);
}
function updateSchematic(angle){
 const valid=Number.isFinite(angle)&&angle>=0&&angle<90;
 const pose=schematicPose(valid?angle:0);
 $('conveyorDrawing').setAttribute('transform',pose.matrix);updatePortGeometry(pose,valid?angle:0);
 $('angleBase').setAttribute('y1',pose.y);
 $('angleBase').setAttribute('y2',pose.y);
 $('angleArc').setAttribute('d',pose.arc);
 $('angleLabel').setAttribute('x',pose.labelX);
 $('angleLabel').setAttribute('y',pose.labelY);
 const label=valid?`${fmt(angle)}°`:'—';
 $('angleLabel').textContent=label;
 $('angleReadout').textContent=label;
 $('conveyorSchematic').setAttribute('aria-label',valid?`Схема шнекового транспортера, угол наклона ${fmt(angle)} градусов`:'Схема шнекового транспортера, угол не задан');
}
function summaryRow(label,value){
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
 summaryGroup(root,'Вход и выход',[['Направление груза','от нижнего патрубка к верхнему'],['Нижний вход',PORT_COUNTS.inlet+' шт. · Ø '+fmt(v.inlet_diameter)+' мм · '+fmt(v.incline)+'° к корпусу'],['Верхний выход',PORT_COUNTS.outlet+' шт. · Ø '+fmt(v.inlet_diameter)+' мм · '+fmt(v.incline)+'° к корпусу'],['Патрубки промывки',PORT_COUNTS.wash+' шт. · не являются входами груза'],['Отверстие в корпусе','Ø '+fmt(v.opening_diameter)+' мм; деталь сбрасывателя удалена'],]);summaryGroup(root,'Выбор по стандартам',[
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
function render(){const v=values(),bore=v.tube_diameter-2*v.tube_wall,gap=(bore-v.screw_diameter)/2;const gostMode=designMode()==='gost';updateSchematic(v.incline);renderParameterSummary(v);$('incline').min='0';$('incline').max=gostMode?'20':'89.999';$('angleModeHint').textContent=gostMode?'Допустимый ввод: 0–20°. Текущие 55° нужно изменить перед применением.':'Углы свыше 20° относятся к специальному проекту; 55° сохранены по заданию.';$('clearance').innerHTML=fmt(gap)+' <span class="unit">мм</span>';$('clearance').style.color=gap>0?'':'#bf5e5e';$('clearanceNote').textContent=gap>0?'По внутреннему диаметру трубы':'Винт пересекает внутреннюю поверхность трубы';$('clearanceNote').style.color=gap>0?'#839398':'#bf5e5e';$('bore').textContent=fmt(bore)+' мм';$('fullLength').textContent=fmt(v.working_length+270)+' мм';$('turnCount').textContent=fmt(v.turns);$('drawingLength').textContent=fmt(v.working_length)+' мм';$('dimWorking').textContent=fmt(v.working_length)+' мм';$('dimFull').textContent=fmt(v.working_length+270)+' мм';$('dimTube').textContent='Ø '+fmt(v.tube_diameter)+' мм';$('dimInlet').textContent=PORT_COUNTS.inlet+' × Ø '+fmt(v.inlet_diameter)+' мм';$('dimOutlet').textContent=PORT_COUNTS.outlet+' × Ø '+fmt(v.inlet_diameter)+' мм';$('dimPortAngle').textContent=fmt(v.incline)+'°';const cautions=[];if(v.incline>20)cautions.push(`угол ${fmt(v.incline)}° превышает 20°`);if(gap<8||gap>10)cautions.push(`зазор ${fmt(gap)} мм вне диапазона 8–10 мм`);$('standardCheck').textContent=cautions.length?'Совпадение типоразмеров не подтверждает соответствие конвейера: '+cautions.join('; ')+'.':'Угол и номинальный зазор входят в указанные пределы; остальные требования стандарта не проверены.';let d='';for(let i=0;i<15;i++){let x=90+i*43;d+=`M${x} 58 C${x+28} 69 ${x+28} 121 ${x+43} 135 `}$('helix').setAttribute('d',d);$('apply').disabled=gap<=0||v.pitch*v.turns+2*v.blade_thickness>v.working_length+85||v.turns%1!==0||v.incline>=90||(gostMode&&v.incline>20)||defs.some(([id])=>!Number.isFinite(v[id])||v[id]<0||(id!=='incline'&&v[id]===0));if(calcReady)queueCalculation()}
function makeFields(v){for(const [id,label,unit,target,hint] of defs){const card=document.createElement('div');card.className='field';card.innerHTML=`<label for="${id}">${label}</label><div class="inputline"><input id="${id}" type="number" step="any" inputmode="decimal" value="${v[id]}"><span class="unit">${unit}</span></div><small><span>●</span> ${hint}</small>`;$(target).append(card);$(id).addEventListener('input',()=>{if(id==='tube_diameter'||id==='tube_wall')$('tubeChoice').value='custom';if(id==='screw_diameter'||id==='pitch')$('screwChoice').value='custom';render()})}render()}
function makeChoices(saved){for(const [kind,control,custom] of [['tube','tubeChoice','Свой размер трубы'],['screw','screwChoice','Свой диаметр и шаг']]){const select=$(control);select.add(new Option(custom,'custom'));for(const item of catalog[kind].items){const label=kind==='tube'?`Ø${item.diameter} × ${item.wall} мм`:`Ø${item.diameter} · шаг ${item.pitch} мм`;select.add(new Option(label,item.id))}select.value=saved?.[kind]||'custom';$(kind+'Source').href=catalog[kind].url}const mat=$('materialChoice');mat.add(new Option('Не выбран','unspecified'));for(const item of catalog.material.items)mat.add(new Option(item,item));mat.value=saved?.material||'unspecified';$('materialSource').href=catalog.material.url;$('materialChoice').onchange=render;$('tubeChoice').onchange=()=>{const item=catalog.tube.items.find(x=>x.id===$('tubeChoice').value);if(item){$('tube_diameter').value=item.diameter;$('tube_wall').value=item.wall}render()};$('screwChoice').onchange=()=>{const item=catalog.screw.items.find(x=>x.id===$('screwChoice').value);if(item){$('screw_diameter').value=item.diameter;$('pitch').value=item.pitch}render()}}
const calcFields={rpm:'calcRpm',target_m3_h:'calcTarget',bulk_density_kg_m3:'calcDensity',lump_mm:'calcLump',cargo_temp_c:'calcTemp',measured_mass_kg:'calcMass',measured_time_s:'calcTime'};
const checkNames={incline:'Область применения · угол',screw_pair:'Диаметр и шаг винта',radial_clearance:'Номинальный зазор',rpm:'Ряд частот вращения',bulk_density:'Насыпная плотность',lump_size:'Размер куска',cargo_temperature:'Температура груза',capacity_series:'Ряд расчётной подачи',target_geometry_bound:'Геометрическая достижимость подачи',bench_measurement:'Стендовая подача',target_verification:'Проверка заявленной подачи'};
function calcInputs(){const result={material_key:$('cargoPreset').value};for(const [key,id] of Object.entries(calcFields))result[key]=$(id).value.trim()===''?null:Number($(id).value.replace(',','.'));return result}
function queueCalculation(){clearTimeout(calcTimer);$('calcStatus').textContent='ПЕРЕРАСЧЁТ';calcTimer=setTimeout(runCalculation,280)}
function addCalcResult(label,value){const card=document.createElement('div');card.className='calc-result';const caption=document.createElement('small');caption.textContent=label;const big=document.createElement('b');big.textContent=value;card.append(caption,big);$('calcResults').append(card)}
function displayCalculation(data){$('calcStatus').textContent=data.status==='BLOCK'?'БЛОК':data.status==='REQUIRED'?'НУЖНЫ ДАННЫЕ':'ЧАСТИЧНО';$('calcStatus').className='pill '+(data.status==='BLOCK'?'warn':'');$('calcResults').replaceChildren();const r=data.results;addCalcResult('Номинальный радиальный зазор',fmt(r.radial_clearance_mm)+' мм');addCalcResult('Геометрический объём за оборот',fmt(r.geometric_volume_per_rev_m3*1000)+' л/об');if(r.geometric_volume_per_hour_m3!==null)addCalcResult('Условный геометрический объём',fmt(r.geometric_volume_per_hour_m3)+' м³/ч');if(r.minimum_ideal_rpm_for_target!==null)addCalcResult('Теоретический минимум частоты',fmt(r.minimum_ideal_rpm_for_target)+' об/мин');if(r.required_effective_fraction!==null)addCalcResult('Требуемая доля от геометрического предела',fmt(r.required_effective_fraction*100)+' % · не подтверждена');if(r.requested_standard_capacity_m3_h!==null)addCalcResult('Ближайший ряд ГОСТ по заявке',fmt(r.requested_standard_capacity_m3_h)+' м³/ч');if(r.measured_mass_flow_kg_h!==null)addCalcResult('Измеренная массовая подача',fmt(r.measured_mass_flow_kg_h)+' кг/ч');if(r.measured_volume_flow_m3_h!==null)addCalcResult('Измеренная объёмная подача',fmt(r.measured_volume_flow_m3_h)+' м³/ч');$('calcChecks').replaceChildren();for(const check of data.checks){const card=document.createElement('div');card.className='calc-check '+check.status.toLowerCase();const title=document.createElement('b');title.textContent=(checkNames[check.id]||check.id)+' · '+check.status;const detail=document.createElement('span');detail.textContent='Факт: '+(check.actual===null?'не задано':check.actual)+' · '+check.requirement+' · '+check.source;card.append(title,detail);$('calcChecks').append(card)}}
async function runCalculation(){const seq=++calcSeq;try{const response=await fetch('/api/calculate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({values:values(),inputs:calcInputs()})});const data=await response.json();if(seq!==calcSeq)return;if(!data.ok)throw Error((data.errors||['Ошибка расчёта']).join(' '));displayCalculation(data)}catch(e){if(seq!==calcSeq)return;$('calcStatus').textContent='ОШИБКА';$('calcResults').textContent=e.message;$('calcChecks').replaceChildren()}}
function renderCargoChoices(){const select=$('cargoPreset'),selected=select.value,group=$('cargoCategory').value,query=$('cargoSearch').value.trim().toLocaleLowerCase('ru-RU');select.replaceChildren(new Option('Груз пока не выбран',''));const groups=new Map();for(const item of materials.items){if(item.id!==selected&&((group&&item.category!==group)||(query&&!`${item.name} ${item.source_name}`.toLocaleLowerCase('ru-RU').includes(query))))continue;if(!groups.has(item.category))groups.set(item.category,[]);groups.get(item.category).push(item)}for(const [name,items] of groups){const optgroup=document.createElement('optgroup');optgroup.label=name;for(const item of items)optgroup.append(new Option(item.name+(item.vertical_candidate?' · V':''),item.id));select.append(optgroup)}select.value=selected}
function describeCargo(){const item=materials.items.find(x=>x.id===$('cargoPreset').value);if(!item){$('cargoHint').textContent='Справочные значения груза показываются как диапазон; для проектного расчёта нужны данные конкретной партии.';return}const density=item.density_kg_m3[0]===item.density_kg_m3[1]?item.density_kg_m3[0]:item.density_kg_m3.join('–');const particle=item.max_particle_mm===null?`крупность по таблице ${item.particle_spec}`:`размер частиц до ${item.max_particle_mm} мм`;const vertical=item.vertical_candidate?'В справочнике есть отметка V — возможна вертикальная подача после отдельного проектирования.':'В справочнике нет отметки V для вертикальной подачи.';$('cargoHint').textContent=`${item.application}. Справочная плотность ${density} кг/м³; ${particle}. ${vertical} Данные конкретной партии необходимо измерить.`}
function setupMaterials(){for(const category of materials.categories)$('cargoCategory').add(new Option(category,category));renderCargoChoices();$('cargoPreset').onchange=()=>{describeCargo();renderParameterSummary(values());queueCalculation()};$('cargoCategory').onchange=renderCargoChoices;$('cargoSearch').oninput=renderCargoChoices;for(const id of Object.values(calcFields))$(id).addEventListener('input',()=>{renderParameterSummary(values());queueCalculation()});$('calculate').onclick=runCalculation}
function journalValue(value){if(value===null||value===undefined)return 'не задано';if(value==='custom')return 'свой размер';if(value==='unspecified')return 'не выбрана';if(value==='gost')return 'ГОСТ 2037-82 · 0–20°';if(value==='special')return 'специальное исполнение';return typeof value==='number'?fmt(value):String(value)}
function renderJournal(data){$('projectName').textContent=data.project.name;$('projectCode').textContent=data.project.id+' · Параметрическая сборка';$('projectCargo').textContent=data.project.cargo||'не указан';$('projectMode').textContent=(data.project.operating_mode||'не указан').toLowerCase();const summary=$('journalSummary');summary.replaceChildren();for(const [count,label] of [[data.summary.model_changes,'применений'],[data.summary.changed_fields,'изменений параметров'],[data.summary.drawing_files,'чертежей'],[data.summary.specification_changes||0,'решений по проекту'],[data.summary.assembly_repairs||0,'исправлено сопряжений']]){const span=document.createElement('span'),number=document.createElement('b');number.textContent=count;span.append(number,document.createTextNode(label));summary.append(span)}const list=$('journalList');list.replaceChildren();if(!data.entries.length){const empty=document.createElement('span');empty.className='journal-empty';empty.textContent='Новых записей пока нет. Журнал ведётся с '+new Date(data.started_at).toLocaleString('ru-RU')+'.';list.append(empty);return}for(const entry of data.entries){const card=document.createElement('article');card.className='journal-entry';const header=document.createElement('header'),title=document.createElement('b'),time=document.createElement('small');time.textContent=new Date(entry.timestamp).toLocaleString('ru-RU');title.textContent=`№${entry.number} · ${entry.title}`;header.append(title,time);card.append(header);const info=document.createElement('p');info.textContent=entry.type!=='drawings'?`Проект: ${entry.project_name}. ${entry.type==='assembly_repair'?'Исправлено сопряжений':'Изменено полей'}: ${entry.change_count}.`:`Проект: ${entry.project_name}. Построено чертежей: ${entry.drawings.length}.${entry.partial?' Сборка содержит отсутствующие ссылки.':''}`;card.append(info);const ul=document.createElement('ul');if(entry.type!=='drawings'){for(const change of entry.changes){const li=document.createElement('li');li.textContent=`${change.name}: ${journalValue(change.before)} → ${journalValue(change.after)}`;ul.append(li)}}else{for(const drawing of entry.drawings){const li=document.createElement('li');li.textContent=`${drawing.name} · ${drawing.scale} · ${drawing.path}${drawing.missing_references?' · отсутствуют ссылки: '+drawing.missing_references:''}`;ul.append(li)}}card.append(ul);list.append(card)}}
async function refreshJournal(){try{const response=await fetch('/api/journal');if(!response.ok)throw Error('Журнал недоступен');const data=await response.json();renderJournal(data);const p=data.project;if(p.cargo_particle_min_mm!==undefined&&p.cargo_particle_max_mm!==undefined){$('projectParticle').hidden=false;$('projectParticle').textContent=`Фракция: ${fmt(p.cargo_particle_min_mm)}–${fmt(p.cargo_particle_max_mm)} мм`}if(p.cargo_moisture_reported_percent!==undefined){$('projectMoisture').hidden=false;$('projectMoisture').textContent=`Влажность: ${fmt(p.cargo_moisture_reported_percent)}% · основа измерения ${p.cargo_moisture_basis||'не уточнена'}`}}catch(e){$('journalList').textContent=e.message}}
async function refreshDiagnostics(){
 try{
  const response=await fetch('/api/model-diagnostics');if(!response.ok)throw Error('Аудит сборки недоступен');
  const data=await response.json();if(!data.available)throw Error(data.message);
  $('diagnosticsNote').textContent=`Сохранённый аудит ${data.audit_date}. У всех ${data.mates_with_lost_references} ошибочных сопряжений потеряна геометрическая ссылка на восстановленную деталь. После ремонта нужен новый аудит SolidWorks.`;
  const summary=$('diagnosticsSummary');summary.replaceChildren();
  for(const label of [`${data.mates} ошибочных сопряжений`,`${data.other} ошибки элементов`,`${data.assemblies.length} проверенных узла`]){const chip=document.createElement('span');chip.textContent=label;summary.append(chip)}
  const groups=$('diagnosticsGroups');groups.replaceChildren();
  for(const group of data.assemblies){
   const details=document.createElement('details'),heading=document.createElement('summary'),counts=document.createElement('small');
   heading.append(document.createTextNode(group.assembly));counts.textContent=`${group.mates} сопряжений · ${group.other} элементов`;heading.append(counts);details.append(heading);
   if(group.errors.length){const list=document.createElement('ul');for(const issue of group.errors){const row=document.createElement('li'),name=document.createElement('b');name.textContent=issue.name+' · ';row.append(name,document.createTextNode(issue.lost_reference?`потеряна геометрическая ссылка: ${issue.affected_components.join(', ')}`:issue.kind+' требует проверки'));list.append(row)}details.append(list)}
   else{const empty=document.createElement('p');empty.textContent='Ошибок в сохранённом аудите нет.';details.append(empty)}
   groups.append(details);
  }
 }catch(error){$('diagnosticsNote').textContent=error.message}
}
function questionnaireValues(){const number=id=>$(id).value.trim()===''?null:Number($(id).value.replace(',','.'));return {starts_per_hour:number('surveyStarts'),run_minutes:number('surveyDuration'),loaded_start:$('surveyLoaded').value||null,mixture_density_kg_m3:number('surveyDensity')}}
async function loadQuestionnaire(){try{const response=await fetch('/api/questionnaire');if(!response.ok)throw Error('Не удалось загрузить опрос');const data=await response.json();$('surveyStarts').value=data.starts_per_hour??'';$('surveyDuration').value=data.run_minutes??'';$('surveyLoaded').value=data.loaded_start??'';$('surveyDensity').value=data.mixture_density_kg_m3??'';$('questionnaireStatus').textContent=Object.values(data).some(x=>x!==null)?'Сохранённые ответы загружены.':'Ответы ещё не заполнены.';if($('incline'))renderParameterSummary(values())}catch(e){$('questionnaireStatus').textContent=e.message}}
$('saveQuestionnaire').onclick=async()=>{const button=$('saveQuestionnaire');button.disabled=true;try{const response=await fetch('/api/questionnaire',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(questionnaireValues())});const data=await response.json();if(!response.ok||!data.ok)throw Error(data.error||'Не удалось сохранить опрос');$('questionnaireStatus').textContent='Ответы сохранены.';await refreshJournal();toast(data.journal_entry?'Условия работы записаны в журнал.':'Ответы сохранены без изменений.')}catch(e){$('questionnaireStatus').textContent=e.message;toast(e.message,true)}finally{button.disabled=false}};
async function load(){try{const [state,items,bulk,saved]=await Promise.all([fetch('/api/state').then(r=>r.json()),fetch('/api/catalog').then(r=>r.json()),fetch('/api/materials').then(r=>r.json()),fetch('/api/calculation-inputs').then(r=>r.json())]);catalog=items;materials=bulk;original=state.values;$('angleMode').value=state.design_mode||'special';$('angleMode').onchange=render;makeFields(state.values);makeChoices(state.selection);setupMaterials();for(const [key,id] of Object.entries(calcFields))if(saved[key]!==null&&saved[key]!==undefined)$(id).value=saved[key];if(saved.material_key){$('cargoPreset').value=saved.material_key;$('cargoPreset').onchange()}renderParameterSummary(values());calcReady=true;runCalculation();$('applied').textContent=state.last_applied?'Последнее применение: '+new Date(state.last_applied).toLocaleString('ru-RU'):'Исходные значения модели';refreshJournal();refreshDiagnostics()}catch(e){toast('Не удалось загрузить параметры и справочники',true)}}
$('apply').onclick=async()=>{const button=$('apply');button.disabled=true;button.textContent='Перестроение…';try{const res=await fetch('/api/apply',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({values:values(),selection:selection(),design_mode:designMode()})});const data=await res.json();if(!data.ok)throw Error((data.errors||['Ошибка SolidWorks']).join(' '));original=data.values;$('applied').textContent='Применено: '+new Date(data.last_applied).toLocaleString('ru-RU');await refreshJournal();toast(data.journal_entry?`Модель сохранена. В журнале ${data.journal_entry.change_count} изменений.`:'Модель сохранена; значения не изменились.')}catch(e){toast(e.message,true)}finally{button.textContent='Применить к модели';render()}};
$('openCad').onclick=async()=>{const button=$('openCad');button.disabled=true;button.textContent='Открытие…';try{const response=await fetch('/api/open',{method:'POST'});const data=await response.json();if(!response.ok||!data.ok)throw Error(data.error||(data.errors||['Не удалось открыть сборку']).join(' '));toast(data.message||'Сборка открыта в SolidWorks.',Boolean(data.partial))}catch(error){toast(error.message||'Не удалось открыть сборку',true)}finally{button.disabled=false;button.textContent='Открыть CAD ↗'}};
$('buildDrawings').onclick=async()=>{const button=$('buildDrawings');button.disabled=true;button.textContent='Построение…';$('drawingStatus').textContent='SolidWorks строит чертежи по сохранённым моделям…';try{const response=await fetch('/api/drawings',{method:'POST'});const data=await response.json();if(!response.ok||!data.ok)throw Error(data.error||'Не удалось построить чертежи');$('drawingStatus').textContent=`Создано ${data.drawings.length} чертежа в папке ${data.batch}.${data.partial?' В модели остаются ошибки; проверьте сопряжения и виды перед выпуском.':''}`;await refreshJournal();toast(`Создано чертежей: ${data.drawings.length}.${data.partial?' Требуется проверка модели.':''}`,Boolean(data.partial))}catch(error){$('drawingStatus').textContent=error.message;toast(error.message,true)}finally{button.disabled=false;button.textContent='Построить чертежи'}};
for(const id of ['surveyStarts','surveyDuration','surveyDensity'])$(id).addEventListener('input',()=>{if($('incline'))renderParameterSummary(values())});$('surveyLoaded').addEventListener('change',()=>{if($('incline'))renderParameterSummary(values())});load();loadQuestionnaire();
