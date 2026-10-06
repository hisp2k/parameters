from pathlib import Path
p=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2\work\loading_workbook_r09.mjs')
s=p.read_text(encoding='utf8')
s=s.replace('C${row}*${U(25)}/4*${U(22)}/(2*E${row})','(C${row}+${U(30)}*${S(29)}*${ct})*${U(25)}/4*${U(22)}/(2*E${row})')
s=s.replace('C${row}*${U(25)}^3/(48*${U(29)}*E${row})','(C${row}+${U(30)}*${S(29)}*${ct})*${U(25)}^3/(48*${U(29)}*E${row})')
s=s.replace("wb.recalculate();d.cases.forEach", "s.getRange('B5').setNumberFormat('0.00');wb.recalculate();d.cases.forEach")
p.write_text(s,encoding='utf8')
print('Workbook builder updated')
