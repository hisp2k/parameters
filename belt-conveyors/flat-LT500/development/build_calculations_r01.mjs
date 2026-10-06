import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const base='C:/Users/adm/Documents/Codex/2026-10-04/new-chat-2';
const data=JSON.parse(await fs.readFile(path.join(base,'work/project_data_r01.json'),'utf8'));
const wb=Workbook.create();
const calc=wb.worksheets.add('Расчёты');
const inp=wb.worksheets.add('Исходные данные');
const issues=wb.worksheets.add('Открытые вопросы');
const beam=wb.worksheets.add('Пролёты');const start=wb.worksheets.add('Пуск и порция');
function baseStyle(sh,range,widths){
 sh.showGridLines=false;
 sh.getRange(range).format.font={name:'Arial',size:11,color:'#202A33'};
 sh.getRange(range).format.verticalAlignment='center';
 sh.getRange(range).format.rowHeight=26;
 widths.forEach((w,i)=>sh.getRange(`${String.fromCharCode(65+i)}:${String.fromCharCode(65+i)}`).format.columnWidth=w);
 sh.getRange('A2').format.font={name:'Arial',size:15,bold:true,color:'#000000'};
}
function header(sh,range){sh.getRange(range).format.fill='#263C52'; sh.getRange(range).format.font={name:'Arial',size:11,bold:true,color:'#FFFFFF'};sh.getRange(range).format.rowHeight=30;}
baseStyle(inp,'A1:F47',[10,38,43,12,22,65]);
inp.getRange('A2').values=[['Исходные данные ЛТ500 R01']];
inp.getRange('A4:F4').values=[['Код','Параметр','Значение','Единица','Статус','Источник и смысл']];
inp.getRange('A5:F44').values=data.inputs;
header(inp,'A4:F4');inp.freezePanes.freezeRows(4);
inp.getRange('B5:F44').format.wrapText=true;inp.getRange('A5:F44').format.rowHeight=58;
inp.getRange('C5:C14').setNumberFormat('0.000');
inp.getRange('C5:C44').format.fill='#FFF0C2';
inp.getRange('C5:C44').format.horizontalAlignment='right';
inp.getRange('D5:E44').format.horizontalAlignment='center';
inp.getRange('E5:E44').conditionalFormats.add('containsText',{text:'Не задано',format:{fill:'#FDE7E7',font:{color:'#A02020',bold:true}}});
inp.getRange('B46').values=[['Жёлтые ячейки значений — исходные данные. Пустое значение означает отсутствие данных, а не ноль.']];
inp.getRange('B46:F46').merge();inp.getRange('B46:F46').format.wrapText=true;inp.getRange('B46:F46').format.rowHeight=35;
baseStyle(calc,'A1:E29',[45,24,15,39,66]);
calc.getRange('A2').values=[['Расчётный паспорт ЛТ500 R01']];
calc.getRange('A3').values=[['Предварительный расчёт. Размеры силовых деталей и мощность не назначены.']];
calc.getRange('A3:E3').merge();calc.getRange('A3:E3').format.rowHeight=30;
calc.getRange('A5:E5').values=[['Расчёт','Результат','Единица','Зависимость','Применимость']];header(calc,'A5:E5');
const rows=[
 ['Габаритная длина в метрах',null,'м','Lгаб / 1000','Габарит изделия; не длина загруженной ветви'],
 ['Погонный вес материала',null,'Н/м','q × g','Материал без собственной массы оборудования'],
 ['Масса для условных 10 м',null,'кг','q × Lгаб','Ориентир; фактическую массу считать по Lраб'],
 ['Вес для условных 10 м',null,'Н','m × g','Не полный расчёт нагрузки на раму'],
 ['Перепад 1° на линии 10 м',null,'мм','Lгаб × sin(θmin)','Если Lгаб трактовать как длину наклонной линии'],
 ['Перепад 2° на линии 10 м',null,'мм','Lгаб × sin(θmax)','Уточнить реальную длину между выбранными точками'],
 ['Перепад 1° на проекции 10 м',null,'мм','Lгаб × tan(θmin)','Если Lгаб трактовать как горизонтальную проекцию'],
 ['Перепад 2° на проекции 10 м',null,'мм','Lгаб × tan(θmax)','Это альтернативное толкование габарита, не выбранная геометрия'],
 ['Сила вниз для условных 10 м при 1°',null,'Н','q × Lгаб × g × sin(θmin)','Помогает движению вниз; прочие сопротивления не заданы'],
 ['Сила вниз для условных 10 м при 2°',null,'Н','q × Lгаб × g × sin(θmax)','Мощность из этой силы отдельно не выбирается'],
 ['Коэффициент расхода по массе',null,'т/ч на м/с','3,6 × q','Q = коэффициент × v, при указанной погонной массе'],
 ['Массовый расход',null,'т/ч','3,6 × q × v','Не задана скорость; это не требуемая производительность'],
 ['Площадь сечения потока',null,'м²','q / ρ','Не задана плотность'],
 ['Объёмный расход',null,'м³/ч','3600 × A × v','Не заданы скорость и плотность'],
 ['Масса на реальной рабочей длине',null,'кг','q × Lраб','Не задана длина загруженной ветви'],
 ['Сила вниз при 1° на реальной длине',null,'Н','mраб × g × sin(θmin)','Не задана длина загруженной ветви'],
 ['Сила вниз при 2° на реальной длине',null,'Н','mраб × g × sin(θmax)','Не задана длина загруженной ветви'],
];
calc.getRange('A6:E22').values=rows;
const formulas=[
 "='Исходные данные'!C5/1000",
 "='Исходные данные'!C10*'Исходные данные'!C11",
 "='Исходные данные'!C10*B6",
 '=B8*\'Исходные данные\'!C11',
 "='Исходные данные'!C5*SIN(RADIANS('Исходные данные'!C8))",
 "='Исходные данные'!C5*SIN(RADIANS('Исходные данные'!C9))",
 "='Исходные данные'!C5*TAN(RADIANS('Исходные данные'!C8))",
 "='Исходные данные'!C5*TAN(RADIANS('Исходные данные'!C9))",
 "=B9*SIN(RADIANS('Исходные данные'!C8))",
 "=B9*SIN(RADIANS('Исходные данные'!C9))",
 "=3.6*'Исходные данные'!C10",
 "=IF(ISBLANK('Исходные данные'!C12),\"не задано\",IF('Исходные данные'!C12>0,B16*'Исходные данные'!C12,\"ошибка скорости\"))",
 "=IF(ISBLANK('Исходные данные'!C13),\"не задано\",IF('Исходные данные'!C13>0,'Исходные данные'!C10/'Исходные данные'!C13,\"ошибка плотности\"))",
 '=IF(AND(ISNUMBER(B17),ISNUMBER(B18)),3600*B18*\'Исходные данные\'!C12,"не задано")',
 "=IF(ISBLANK('Исходные данные'!C14),\"не задано\",IF('Исходные данные'!C14>0,'Исходные данные'!C10*'Исходные данные'!C14,\"ошибка длины\"))",
 '=IF(ISNUMBER(B20),B20*\'Исходные данные\'!C11*SIN(RADIANS(\'Исходные данные\'!C8)),"не задано")',
 '=IF(ISNUMBER(B20),B20*\'Исходные данные\'!C11*SIN(RADIANS(\'Исходные данные\'!C9)),"не задано")'
];
calc.getRange('B6:B22').formulas=formulas.map(f=>[f]);
calc.getRange('B6:B22').setNumberFormat('0.000');calc.getRange('B6:B22').format.horizontalAlignment='right';
calc.getRange('C6:C22').format.horizontalAlignment='center';
calc.getRange('A6:E22').format.wrapText=true;calc.getRange('A6:E22').format.rowHeight=50;
calc.getRange('B6:B22').conditionalFormats.add('containsText',{text:'не задано',format:{fill:'#FFF0C2',font:{color:'#8A5B00'}}});
calc.getRange('A24').values=[['Метод: баланс массы и сил, геометрия. Коэффициенты динамики и запаса ещё не назначены.']];calc.getRange('A24:E24').merge();calc.getRange('A24:E24').format.rowHeight=32;
calc.getRange('A25').values=[['Открыты: полный тяговый расчёт, натяжение, пуск, прочность и подбор компонентов.']];calc.getRange('A25:E25').merge();
baseStyle(issues,'A1:E20',[9,37,39,74,17]);
issues.getRange('A2').values=[['Открытые вопросы ЛТ500 R01']];
issues.getRange('A4:E4').values=[['Код','Влияние','Недостающие данные','Действие для закрытия','Статус']];header(issues,'A4:E4');
issues.getRange('A5:E16').values=data.issues.map(r=>[...r,'Открыто']);
issues.getRange('A5:E16').format.wrapText=true;issues.getRange('A5:E16').format.rowHeight=86;issues.freezePanes.freezeRows(4);
issues.getRange('E5:E16').dataValidation={rule:{type:'list',values:['Открыто','В работе','Закрыто']}};
issues.getRange('E5:E16').format.fill='#FFF0C2';
baseStyle(beam,'A1:H18',[15,12,20,20,24,24,23,26]);
beam.getRange('A2').values=[['Сравнение пролётов. Статика материала, не полный расчёт рамы']];beam.getRange('A2:H2').merge();
beam.getRange('A3:H3').merge();beam.getRange('A3').values=[['Одна шарнирно опёртая балка. Порция 15 кг целиком в середине пролёта, дополнительно к q. Собственный вес и удар исключены.']];beam.getRange('A3:H3').format.wrapText=true;beam.getRange('A3:H3').format.rowHeight=42;
beam.getRange('A5:H5').values=[['Пролёт s, м','Доля β','w, Н/м','P, Н','Mmax, Н·м','K=δEI, Н·м³','Wтреб, мм³','Iтреб, мм⁴']];header(beam,'A5:H5');
let br=6;for(const fraction of [0.5,1])for(const span of [2,2.5,10/3,5]){beam.getRange(`A${br}:B${br}`).values=[[span,fraction]];beam.getRange(`C${br}:H${br}`).formulas=[[
 `=B${br}*'Расчёты'!B7`,"='Исходные данные'!C36*'Исходные данные'!C11",`=C${br}*A${br}^2/8+D${br}*A${br}/4`,
 `=5*C${br}*A${br}^4/384+D${br}*A${br}^3/48`,
 `=IF(ISBLANK('Исходные данные'!C43),"не задано",IF('Исходные данные'!C43>0,E${br}*1000/'Исходные данные'!C43,"ошибка σ"))`,
 `=IF(OR(ISBLANK('Исходные данные'!C42),ISBLANK('Исходные данные'!C44)),"не задано",IF(AND('Исходные данные'!C42>0,'Исходные данные'!C44>0),F${br}*10^9/('Исходные данные'!C42*'Исходные данные'!C44),"ошибка E/δ"))`
 ]];br++;}
beam.getRange('A6:H13').setNumberFormat('0.000');beam.getRange('A6:H13').format.rowHeight=34;beam.getRange('A6:B13').format.fill='#FFF0C2';
beam.getRange('A14:H14').merge();beam.getRange('A14').values=[['M=w·s²/8+P·s/4; δ=(5w·s⁴/384+P·s³/48)/(EI). Наклонная нормальная нагрузка для сравнения ограничена значением при 0°.']];beam.getRange('A14:H14').format.wrapText=true;beam.getRange('A14:H14').format.rowHeight=46;
baseStyle(start,'A1:E18',[43,24,15,48,61]);start.getRange('A2').values=[['Нагруженный повторный пуск и порция']];
start.getRange('A4:E4').values=[['Показатель','Результат','Единица','Зависимость','Ограничение']];header(start,'A4:E4');
start.getRange('A5:E14').values=[
 ['Масса разовой порции',null,'кг','mп','Принято суммарно; распределение и длительность сброса неизвестны'],
 ['Статический вес порции',null,'Н','mп × g','Это не сила удара'],
 ['Энергия падения',null,'Дж','mп × g × Hп','Высота падения отсутствует'],
 ['Средняя контактная сила в простой модели',null,'Н','mп × g × (1 + Hп/sт)','Торможение вниз на пути sт; без упругого отскока. Пиковая сила не определена'],
 ['Масса материала при условных 10 м',null,'кг','q × 10','Расчётный сценарий остатка; не утверждённая рабочая длина'],
 ['Разгон материала',null,'Н','m × v / t','Равномерное ускорение. Массы ленты и вращения не включены'],
 ['Кинетическая энергия материала',null,'Дж','0,5 × m × v²','Не энергия всего механизма'],
 ['Сопротивления качения и барабанов','не задано','Н','По принятой методике','Тип ленты, ролики, массы и коэффициенты неизвестны'],
 ['Сопротивление очистителя','не задано','Н','По характеристике узла','Усилие и конструкция не выбраны'],
 ['Полное усилие и мощность привода','не определено','Н; кВт','Полный баланс + КПД','Выбор мотор-редуктора пока не выполнен']];
start.getRange('B5:B11').formulas=[['=\'Исходные данные\'!C36'],['=B5*\'Исходные данные\'!C11'],['=IF(ISBLANK(\'Исходные данные\'!C39),"не задано",IF(\'Исходные данные\'!C39>=0,B6*\'Исходные данные\'!C39,"ошибка H"))'],['=IF(OR(ISBLANK(\'Исходные данные\'!C39),ISBLANK(\'Исходные данные\'!C40)),"не задано",IF(AND(\'Исходные данные\'!C39>=0,\'Исходные данные\'!C40>0),B6*(1+\'Исходные данные\'!C39/\'Исходные данные\'!C40),"ошибка H/s"))'],['=\'Расчёты\'!B8'],['=IF(OR(ISBLANK(\'Исходные данные\'!C12),ISBLANK(\'Исходные данные\'!C41)),"не задано",IF(AND(\'Исходные данные\'!C12>0,\'Исходные данные\'!C41>0),B9*\'Исходные данные\'!C12/\'Исходные данные\'!C41,"ошибка v/t"))'],['=IF(ISBLANK(\'Исходные данные\'!C12),"не задано",IF(\'Исходные данные\'!C12>0,0.5*B9*\'Исходные данные\'!C12^2,"ошибка v"))']];
start.getRange('A5:E14').format.wrapText=true;start.getRange('A5:E14').format.rowHeight=63;start.getRange('B5:B11').setNumberFormat('0.000');
wb.recalculate();
if(Math.abs(beam.getRange('E6').values[0][0]-147.09975)>1e-7||Math.abs(beam.getRange('F6').values[0][0]-55.16240625)>1e-7)throw Error('Beam anchor case failed');
inp.getRange('C12').values=[[0.1]];inp.getRange('C39:C44').values=[[0.5],[0.01],[2],[200000],[120],[2]];wb.recalculate();
const restartProbe=start.getRange('B7:B11').values.map(r=>r[0]);
if(Math.abs(restartProbe[0]-73.549875)>1e-7||Math.abs(restartProbe[1]-7502.08725)>1e-7||Math.abs(restartProbe[3]-15)>1e-7||Math.abs(restartProbe[4]-1.5)>1e-7)throw Error('Impact/start scenario failed');
if(Math.abs(beam.getRange('G6').values[0][0]-1225.83125)>1e-7||Math.abs(beam.getRange('H6').values[0][0]-137906.015625)>1e-6)throw Error('Beam stiffness units failed');
inp.getRange('C12').values=[[null]];inp.getRange('C39:C44').values=[[null],[null],[null],[null],[null],[null]];wb.recalculate();
if(beam.getRange('G6').values[0][0]!=='не задано'||start.getRange('B8').values[0][0]!=='не задано')throw Error('Restored missing data failed');
await fs.writeFile(path.join(base,'work/extra_qa_r01.json'),JSON.stringify({beamAnchor:'passed',impactStartProbe:restartProbe,unitsAndBlankRestoration:'passed'},null,2));

wb.recalculate();
const values=calc.getRange('B6:B22').values.map(r=>r[0]);
const close=(a,b)=>Math.abs(a-b)<1e-7;
if(!close(values[2],300)||!close(values[3],2941.995)||!close(values[10],108))throw Error('Independent numeric verification failed');
if(values.slice(11).some(v=>v!=='не задано'))throw Error('Missing input is not exposed');
inp.getRange('C12').values=[[0.1]];inp.getRange('C13').values=[[600]];inp.getRange('C14').values=[[9]];
wb.recalculate();
const probe=calc.getRange('B17:B22').values.map(r=>r[0]);
if(!close(probe[0],10.8)||!close(probe[1],0.05)||!close(probe[2],18)||!close(probe[3],270))throw Error('Input recalculation test failed');
inp.getRange('C12').values=[[0]];inp.getRange('C13').values=[[0]];inp.getRange('C14').values=[[0]];wb.recalculate();
if(calc.getRange('B17').values[0][0]!=='ошибка скорости'||calc.getRange('B18').values[0][0]!=='ошибка плотности'||calc.getRange('B20').values[0][0]!=='ошибка длины')throw Error('Zero boundary failed');
inp.getRange('C12:C14').values=[[null],[null],[null]];wb.recalculate();
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:30},maxChars:1500});
await fs.writeFile(path.join(base,'work/xlsx_error_scan_r01.txt'),errors.ndjson);
await fs.writeFile(path.join(base,'work/calculation_qa_r01.json'),JSON.stringify({initial:values,inputProbe:probe,blankAndZeroTests:'passed',engine:'Artifact Tool; native Excel not tested'},null,2));
for(const [sh,range,name] of [[calc,'A2:E22','calc'],[inp,'A2:F14','inputs'],[inp,'A15:F30','inputs_tail'],[inp,'A31:F44','inputs_last'],[beam,'A2:H14','beam'],[start,'A2:E14','start'],[issues,'A2:E16','issues']]){
 const blob=await wb.render({sheetName:sh.name,range,scale:1.3,format:'png'});
 await fs.writeFile(path.join(base,`work/r01_${name}_qa.png`),new Uint8Array(await blob.arrayBuffer()));
}
const file=await SpreadsheetFile.exportXlsx(wb);
await file.save(path.join(base,'outputs/Ленточный_транспортер/02_Расчеты/ЛТ500_Расчётный_паспорт_R01.xlsx'));
console.log(JSON.stringify({rows:rows.length,mass_kg:values[2],weight_N:values[3],Q_coefficient:values[10],tests:'passed'}));
