from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path('outputs') / 'Шнек 1 — параметрическая модель'))
import journal

with tempfile.TemporaryDirectory(dir='work') as temp:
    journal.JOURNAL = Path(temp) / 'journal.json'
    before = {'values': {'pitch': 105, 'tube_diameter': 141}, 'selection': {'material': 'unspecified'}}
    after = {'values': {'pitch': 110, 'tube_diameter': 141}, 'selection': {'material': '12Х18Н10Т'}}
    entry = journal.record_apply(before, after)
    assert entry['change_count'] == 2
    assert journal.record_apply(after, after) is None
    journal.record_drawings({'batch': 'Чертежи/test', 'drawings': [{'name': 'test'}], 'partial': False})
    summary = journal.view()['summary']
    assert summary == {'model_changes': 1, 'changed_fields': 2, 'drawing_batches': 1, 'drawing_files': 1}, summary
    print(summary)
