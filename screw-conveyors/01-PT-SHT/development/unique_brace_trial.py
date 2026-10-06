from pathlib import Path
p=Path('work/fix_brace_clearance_20261005.py');s=p.read_text(encoding='utf-8').replace("f'Подкос {index+1} — контроль.SLDPRT'","f'Подкос {index+1} — {trial_dir.name}.SLDPRT'");p.write_text(s,encoding='utf-8')
