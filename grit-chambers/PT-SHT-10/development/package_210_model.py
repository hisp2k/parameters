from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import hashlib,json

root=Path('work/pt-sht-10-210l')
out=Path('outputs/PT-SHT-10-210L_модель_и_Flow.zip')
files=[]
for p in (root/'Модель').iterdir():
    if p.is_file() and (p.suffix.lower() in ('.sldasm','.sldprt','.html') or p.name=='Goals.DAT'):
        files.append(p)
for p in (root/'CADparts').iterdir():
    if p.suffix.lower() in ('.sldprt','.stl','.npz'):
        files.append(p)
for p in (root/'particle_results').iterdir():
    if p.suffix.lower() in ('.json','.npz'):
        files.append(p)
for i in (4,5):
    for p in (root/'Модель'/str(i)).iterdir():
        if p.is_file() and not p.name.startswith(('~','$')) and p.name!='r_000000.fld' and p.suffix.lower() not in ('.bak','.swp'):
            files.append(p)
assert any(p.name=='PT-SHT-10-210L.SLDASM' for p in files)
assert any(p.name=='4.fld' for p in files) and any(p.name=='5.fld' for p in files)
assert len([p for p in files if p.name.startswith('CAD210_') and p.suffix.lower()=='.sldprt'])>=16
with ZipFile(out,'w',ZIP_DEFLATED,compresslevel=4) as z:
    for p in files:z.write(p,p.relative_to(root.parent))
with ZipFile(out) as z:
    assert z.testzip() is None
    manifest={'archive':str(out.resolve()),'file_count':len(z.namelist()),'bytes':out.stat().st_size,
              'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),
              'contains':{'cad':any(n.endswith('PT-SHT-10-210L.SLDASM') for n in z.namelist()),
                          'q10':any(n.endswith('4/4.fld') for n in z.namelist()),
                          'q2p09':any(n.endswith('5/5.fld') for n in z.namelist())}}
Path('outputs/PT-SHT-10-210L_архив_проверка.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(manifest,ensure_ascii=False),flush=True)
