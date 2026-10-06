from pathlib import Path
import json
import sys

sys.path.insert(0, str((Path('outputs') / 'Шнек 1 — параметрическая модель').resolve()))
import bridge

baseline = json.loads(bridge.STATE.read_text(encoding='utf-8'))['values']
cases = {
    'current_values': (baseline, True),
    'interference': ({**baseline, 'tube_diameter': baseline['screw_diameter'] + 2*baseline['tube_wall']}, False),
    'negative_pitch': ({**baseline, 'pitch': -1}, False),
    'fractional_turns': ({**baseline, 'turns': 25.5}, False),
    'turns_exceed_length': ({**baseline, 'turns': 100}, False),
    'shaft_wall_exceeds_radius': ({**baseline, 'shaft_wall': baseline['shaft_diameter']/2}, False),
    'inlet_wall_exceeds_radius': ({**baseline, 'inlet_wall': baseline['inlet_diameter']/2}, False),
    'vertical_angle': ({**baseline, 'incline': 90}, False),
    'unknown_key': ({**baseline, 'fictional': 1}, False),
    'nonfinite': ({**baseline, 'pitch': float('inf')}, False),
}
for name,(values,expected) in cases.items():
    actual = not bridge.validate(values)
    print(name, 'PASS' if actual == expected else 'FAIL', bridge.validate(values)[:1])
    assert actual == expected

gap = (baseline['tube_diameter'] - 2*baseline['tube_wall'] - baseline['screw_diameter']) / 2
full = baseline['working_length'] + 270
print('calculator', {'nominal_gap_mm':gap,'full_length_mm':full})
