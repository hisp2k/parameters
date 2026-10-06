"""Restore imported large archives from 16 MiB parts; verify every SHA-256."""
from pathlib import Path
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda: f.read(4*1024*1024), b''): h.update(data)
    return h.hexdigest()

def inside(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT): raise ValueError('Path outside repository')
    return path

def restore(info):
    target = inside(info['original_path'])
    if target.exists():
        if target.stat().st_size == info['size'] and digest(target) == info['sha256']:
            print('Already restored:', target.relative_to(ROOT)); return
        raise FileExistsError(f'Different file already exists: {target}')
    temporary = target.with_name(target.name + '.restore.tmp')
    h = hashlib.sha256()
    total = 0
    try:
        with temporary.open('xb') as out:
            for part in info['parts']:
                source = inside(part['path'])
                if source.stat().st_size != part['size'] or digest(source) != part['sha256']:
                    raise ValueError(f'Part verification failed: {source}')
                with source.open('rb') as f:
                    for data in iter(lambda: f.read(4*1024*1024), b''):
                        out.write(data); h.update(data); total += len(data)
        if total != info['size'] or h.hexdigest() != info['sha256']:
            raise ValueError('Restored archive verification failed')
        os.replace(temporary, target)
        print('Restored:', target.relative_to(ROOT))
    except Exception:
        if temporary.exists(): temporary.unlink()
        raise

if __name__ == '__main__':
    manifest = ROOT / 'docs/import-2026-10-06/large-files.json'
    for info in json.loads(manifest.read_text(encoding='utf-8')): restore(info)
