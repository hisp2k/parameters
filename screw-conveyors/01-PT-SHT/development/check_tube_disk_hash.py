from pathlib import Path
import hashlib,json
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();p=base/'CAD_восстановленный'/'Шнек'/"PT.SHT.01.21.00.00 СБ 'Труба в сборе' — восстановлено.SLDASM";b=base/'snapshots'/'20261004-all-interferences-before'/p.relative_to(base)
print('tube disk unchanged',hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256(b.read_bytes()).digest())
