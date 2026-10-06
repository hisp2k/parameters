from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import sys
import win32com.client as win32

root=Path(sys.argv[1]).resolve()
sw=win32.Dispatch('SldWorks.Application')
for p in root.iterdir():
    if p.suffix.upper() in ('.SLDPRT','.SLDASM','.SLDDRW'):
        sw.CloseDoc(p.name)

out=root/'Комплект_КМ022_SolidWorks_DXF.zip'
with ZipFile(out,'w',ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(root.iterdir()):
        if p.is_file() and p!=out and not p.name.startswith('~$'):
            z.write(p,p.name)
with ZipFile(out) as z:
    assert z.testzip() is None
    print('ZIP',out,len(z.namelist()),'files',out.stat().st_size,'bytes')
