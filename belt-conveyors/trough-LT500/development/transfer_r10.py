from pathlib import Path
import hashlib, json, shutil, zipfile
from datetime import datetime
from zoneinfo import ZoneInfo

root = Path(__file__).resolve().parents[1]
src = Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2\outputs\Ленточный_транспортер_ЛТ500_R10.zip')
dst = root / 'outputs' / src.name
history = root / 'outputs' / 'История_R10'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
before = sha(src)
if dst.exists():
    assert sha(dst) == before, 'Existing destination differs'
else:
    shutil.copy2(src, dst)
assert sha(dst) == before
assert not history.exists(), 'History destination already exists'
with zipfile.ZipFile(dst) as z:
    assert z.testzip() is None, 'ZIP CRC check failed'
    entries = [e for e in z.infolist() if not e.is_dir()]
    for e in entries:
        target = (history / e.filename).resolve()
        assert target.is_relative_to(history.resolve()), 'Unsafe archive path'
    z.extractall(history)
    manifest = []
    for e in entries:
        p = history / e.filename
        assert p.stat().st_size == e.file_size
        manifest.append({'path': e.filename, 'bytes': e.file_size, 'zip_crc32': f'{e.CRC:08x}', 'sha256': sha(p)})
assert sha(src) == before, 'Source changed'
report = {'date_local': '2026-10-04', 'timezone': 'Europe/Samara', 'source': str(src), 'copy': str(dst), 'extracted_to': str(history), 'archive_bytes': dst.stat().st_size, 'archive_sha256': before, 'zip_crc_all_pass': True, 'files_count': len(manifest), 'source_hash_unchanged': True, 'files': manifest}
(root/'outputs'/'Проверка_переноса_R10.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='files'},ensure_ascii=False,indent=2))
print('\n'.join(e['path'] for e in manifest))
