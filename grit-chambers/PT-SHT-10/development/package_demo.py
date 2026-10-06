from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
root=Path('work/pt-sht-10-demo')
out=Path('outputs/PT-SHT-10_демо_проект_Flow.zip')
files=[p for p in root.rglob('*') if p.is_file() and not p.name.startswith('~$')]
with ZipFile(out,'w',ZIP_DEFLATED,compresslevel=6) as z:
 for p in files:z.write(p,p.relative_to(root.parent))
with ZipFile(out) as z:
 bad=z.testzip(); print('archive',out.resolve(),'files',len(z.namelist()),'bytes',out.stat().st_size,'bad',bad)
 assert bad is None
 assert any(x.endswith('.geom') for x in z.namelist())
 assert any(x.endswith('.SLDASM') for x in z.namelist())
