from pathlib import Path
import hashlib

folder = next(Path('outputs').glob('Шнек 1 — аудит производственного комплекта'))
target = folder / '07_Манифест выдачи.md'
files = sorted(p for p in folder.iterdir() if p.is_file() and p != target)
rows = [
    '# Манифест проектного аудита «Шнек 1»',
    '',
    'Контрольные суммы относятся к байтам перечисленных файлов. Они не подтверждают пригодность CAD к производству.',
    '',
    '| Файл | Байт | SHA-256 |',
    '|---|---:|---|',
]
for file in files:
    rows.append(f'| {file.name} | {file.stat().st_size} | `{hashlib.sha256(file.read_bytes()).hexdigest()}` |')
rows += ['', f'Файлов: {len(files)}.', '']
target.write_text('\n'.join(rows), encoding='utf-8')
print(target, len(files))
