from pathlib import Path
import sys

project = next(Path('outputs').glob('Шнек 1 — параметрическая модель'))
sys.path.insert(0, str(project))
import journal

decisions = [
    {'name': 'Стопорное кольцо D80 DIN 472 А2, шт.', 'before': 1, 'after': 2},
    {'name': 'Шайба М8, обозначение', 'before': 'DIN 128 А2 в BOM', 'after': 'DIN 127 B А2 — проектное решение по имеющейся CAD-детали'},
    {'name': 'Сбрасыватель, шт.', 'before': 'нет в BOM', 'after': 1},
    {'name': 'Транспортируемый груз', 'before': None, 'after': 'песок с очистных сооружений'},
    {'name': 'Требуемая подача, м³/ч', 'before': None, 'after': 10},
    {'name': 'Режим работы', 'before': None, 'after': 'прерывный'},
    {'name': 'Угол установки, °', 'before': 55, 'after': '55 — подтверждён'},
    {'name': 'Частота для проверки, об/мин', 'before': None, 'after': '190 — кандидат; фактическая подача не подтверждена'},
]
entry = journal.record_specification(decisions, 'USER-2026-10-02-SAND-10M3H')
print(entry['number'], entry['decision_id'], entry['change_count'])
