from pathlib import Path
b=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');s=(b/'work/build_calculations.mjs').read_text(encoding='utf8')
s=s.replace('project_data.json','project_data_r01.json').replace('R00','R01').replace('A1:F38','A1:F47').replace('A5:F35','A5:F44').replace('B5:F35','B5:F44').replace('C5:C35','C5:C44').replace('D5:E35','D5:E44').replace('E5:E35','E5:E44').replace('B37','B46').replace('F37','F46')
s=s.replace("const issues=wb.worksheets.add('Открытые вопросы');", "const issues=wb.worksheets.add('Открытые вопросы');\nconst beam=wb.worksheets.add('Пролёты');const start=wb.worksheets.add('Пуск и порция');")
s=s.replace('wb.recalculate();', (b/'work/extra_calculations.mjs.txt').read_text(encoding='utf8')+'\nwb.recalculate();',1)
s=s.replace("work/xlsx_error_scan.txt","work/xlsx_error_scan_r01.txt").replace('work/calculation_qa.json','work/calculation_qa_r01.json').replace('`work/${name}_qa.png`','`work/r01_${name}_qa.png`')
s=s.replace("[inp,'A15:F35','inputs_tail']","[inp,'A15:F30','inputs_tail'],[inp,'A31:F44','inputs_last'],[beam,'A2:H14','beam'],[start,'A2:E14','start']")
(b/'work/build_calculations_r01.mjs').write_text(s,encoding='utf8')
