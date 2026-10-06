"""Relink one exact existing component in the working CAD copy."""
from datetime import datetime
from pathlib import Path
import shutil
import sys
import win32com.client as win32

project = Path(sys.argv[1]).resolve()
cad = project / 'CAD'
top = next(cad.glob("*20.00.00*Шнек 1*.SLDASM"))
tube = next(cad.rglob("PT.SHT.01.21.00.00 СБ 'Труба в сборе'.SLDASM"))
new_ref = next(cad.rglob("PT.SHT.01.21.00.07 'Сбрасыватель'.SLDPRT"))
assert all(p.is_file() and p.resolve().is_relative_to(cad.resolve()) for p in (top, tube, new_ref))

sw = win32.GetActiveObject('SldWorks.Application')
tube_doc = sw.GetOpenDocumentByName(str(tube))
if tube_doc is None:
    spec = sw.GetOpenDocSpec(str(tube))
    spec.DocumentType = 2
    spec.Silent = True
    tube_doc = sw.OpenDoc7(spec)
old_refs = [c.GetPathName for c in (tube_doc.GetComponents(False) or []) if 'Сбрасыватель' in c.GetPathName]
if len(old_refs) != 1:
    raise RuntimeError(f'Ожидалась одна ссылка на сбрасыватель, обнаружено {len(old_refs)}')
old_ref = old_refs[0]
if Path(old_ref).is_file():
    raise RuntimeError('Исходная ссылка уже разрешена; замена не требуется')
top_doc = sw.GetOpenDocumentByName(str(top))
for document in (top_doc, tube_doc):
    if document is not None and document.GetSaveFlag:
        raise RuntimeError(f'Документ содержит несохранённые изменения: {document.GetPathName}')

backup = project / 'snapshots' / ('relink-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir(parents=True, exist_ok=False)
shutil.copy2(tube, backup / tube.name)
print('BACKUP', backup / tube.name)
if top_doc is not None:
    sw.CloseDoc(top_doc.GetTitle)
sw.CloseDoc(tube_doc.GetTitle)
if sw.GetOpenDocumentByName(str(tube)) is not None:
    raise RuntimeError('Труба в сборе осталась открытой; замена ссылки остановлена')

ok = bool(sw.ReplaceReferencedDocument(str(tube), old_ref, str(new_ref)))
print('REPLACE_RESULT', ok)
if not ok:
    raise RuntimeError('SolidWorks не заменил ссылку')

spec = sw.GetOpenDocSpec(str(tube))
spec.DocumentType = 2
spec.Silent = True
reopened = sw.OpenDoc7(spec)
if reopened is None:
    raise RuntimeError('Подсборка не открылась после замены ссылки')
new_refs = [c.GetPathName for c in (reopened.GetComponents(False) or []) if 'Сбрасыватель' in c.GetPathName]
print('NEW_REFS', new_refs)
if len(new_refs) != 1 or Path(new_refs[0]).resolve() != new_ref.resolve():
    raise RuntimeError('Сохранённая ссылка не совпадает с локальным файлом')
print('VERIFIED', new_ref)
