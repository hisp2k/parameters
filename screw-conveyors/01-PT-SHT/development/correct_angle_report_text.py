from pathlib import Path
base=Path('outputs/Шнек 1 — параметрическая модель')
p=base/'index.html';s=p.read_text(encoding='utf-8');s=s.replace('Целевые 55° остаются невыполненным требованием. Полный диапазон параметров не подтверждён.`', "${data.design_angle_mismatch?'Целевой угол ещё не достигнут.':'Сохранённый угол соответствует заданию.'} Полный диапазон параметров не подтверждён.`");p.write_text(s,encoding='utf-8')
