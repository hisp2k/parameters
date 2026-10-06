import fs from 'node:fs/promises';
import path from 'node:path';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';

const root = path.resolve(import.meta.dirname, '../..');
const source = path.join(root, 'outputs', 'Шнек 1 — параметрическая модель', 'CAD', '01.PT.SHT BOM.xlsx');
const outputDir = path.join(root, 'outputs', 'Шнек 1 — аудит производственного комплекта');
const destination = path.join(outputDir, '05_BOM — проектная правка.xlsx');
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(source));
const sheet = workbook.worksheets.getItemAt(0);

if (sheet.getRange('B54').values[0][0] !== 'Стопорное кольцо D80 DIN 472 А2' ||
    sheet.getRange('G54').values[0][0] !== 1 ||
    sheet.getRange('B58').values[0][0] !== 'Шайба пружинная М8 DIN128 А2' ||
    sheet.getRange('B60').values[0][0] != null) {
  throw new Error('Исходная BOM изменилась; автоматическая правка остановлена');
}

sheet.getRange('G54').values = [[2]];
sheet.getRange('B58').values = [['Шайба пружинная М8 DIN 127 B А2']];
sheet.getRange('A60:G60').copyFrom(sheet.getRange('A59:G59'), 'all');
sheet.getRange('A60:G60').values = [['59', "PT.SHT.01.21.00.07 'Сбрасыватель'", null, null, null, null, 1]];
sheet.getRange('A60:G60').format.font.italic = true;
sheet.getRange('A60:G60').format.horizontalAlignment = 'center';

workbook.recalculate();
console.log('changed', JSON.stringify(sheet.getRange('A54:G60').values));
const errors = await workbook.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},maxChars:1000});
console.log('errors',errors.ndjson);
const preview = await workbook.render({sheetName:sheet.name,range:'A54:G60',scale:1.5,format:'png'});
await fs.writeFile(path.join(root,'work','spreadsheet','bom_after.png'),new Uint8Array(await preview.arrayBuffer()));
await fs.mkdir(outputDir,{recursive:true});
const blob = await SpreadsheetFile.exportXlsx(workbook);
await blob.save(destination);
console.log('saved',destination);
