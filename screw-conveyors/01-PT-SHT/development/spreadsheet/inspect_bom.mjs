import fs from 'node:fs/promises';
import path from 'node:path';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';

const root = path.resolve(import.meta.dirname, '../..');
const source = path.join(root, 'outputs', 'Шнек 1 — параметрическая модель', 'CAD', '01.PT.SHT BOM.xlsx');
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(source));
const sheet = workbook.worksheets.getItemAt(0);
console.log((await workbook.inspect({kind:'sheet',include:'id,name',maxChars:1200})).ndjson);
console.log('rows 50-59', JSON.stringify(sheet.getRange('A50:G59').values));
const preview = await workbook.render({sheetName:sheet.name,range:'A50:G59',scale:1.5,format:'png'});
await fs.writeFile(path.join(root,'work','spreadsheet','bom_before.png'), new Uint8Array(await preview.arrayBuffer()));
