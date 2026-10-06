"""Downsample trusted native CAD exports for display without changing their content."""
from pathlib import Path
from PIL import Image
base=Path('outputs/Шнек 1 — параметрическая модель').resolve()
Image.MAX_IMAGE_PIXELS=250000000
for name in ('Стыки труб — опора 05.10.2026','Стыки труб — сборка 05.10.2026'):
    with Image.open(base/(name+'.png')) as source:
        source.thumbnail((1800,1400),Image.Resampling.LANCZOS)
        target=base/(name+' — просмотр.png')
        source.save(target)
        print(target,source.size,flush=True)
