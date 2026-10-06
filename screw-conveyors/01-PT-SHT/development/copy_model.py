from pathlib import Path
import shutil

src = next(Path(r'C:\Users\adm\Desktop\РАЗРАБОТКА').rglob("PT.SHT.01.20.00.00 СБ 'Шнек 1'.SLDASM")).parent
dst = Path('outputs') / 'Шнек 1 — параметрическая модель' / 'CAD'
if dst.exists():
    raise SystemExit(f'Target already exists: {dst}')
shutil.copytree(src, dst, ignore=shutil.ignore_patterns('~$*'))
print(dst.resolve())
print(sum(p.is_file() for p in dst.rglob('*')))
