"""Extract original product BREPs from the supplied solid STEP assembly.

The result is intermediate neutral geometry, not a standards-certified fastener.
"""
from pathlib import Path
import re
import sys

project = Path(sys.argv[1]).resolve()
cad = project / 'CAD'
source = next(cad.glob('*ТТ*.STEP'))
destination = project / 'recovered_from_step'
destination.mkdir(exist_ok=True)
content = source.read_text(encoding='latin1')
header = content[:content.index('DATA;') + len('DATA;')]
entities = {int(i): value for i, value in re.findall(r'#(\d+)\s*=\s*(.*?);', content, re.S)}
back = {}
for number, value in entities.items():
    for ref in set(map(int, re.findall(r'#(\d+)', value))):
        back.setdefault(ref, []).append(number)

targets = [
    'PT.SHT.01.01.00.11  Фланец присоединительный',
    'PT.SHT.01.01.02.03  Опора',
    'Болт М10х90 DIN 933', 'Болт М6х20 DIN 933 А2', 'Болт М8х25 DIN 933',
    'Винт М12х30 DIN 931', 'Винт М8х20 DIN 931',
    'Гайка М10 DIN 934', 'Гайка М6 DIN 934', 'Гайка М8 DIN 934',
    'Шайба пружинная М10 DIN128', 'Шайба пружинная М12 DIN 128',
    'Шайба пружинная М6 DIN128',
    'Шпонка 8x7x63 ГОСТ 23360-78 DIN 6885',
]

def decode_step(value):
    return re.sub(r'\\X2\\([0-9A-Fa-f]+)\\X0\\',
                  lambda m: bytes.fromhex(m.group(1)).decode('utf-16-be'), value)

def unique_child(parent, prefix):
    matches = [i for i in back.get(parent, ()) if entities[i].startswith(prefix)]
    if len(matches) != 1:
        raise RuntimeError(f'{parent}: expected one {prefix}, found {matches}')
    return matches[0]

def closure(seeds):
    found = set(seeds)
    pending = list(seeds)
    while pending:
        number = pending.pop()
        for ref in map(int, re.findall(r'#(\d+)', entities[number])):
            if ref not in entities:
                raise RuntimeError(f'Missing STEP entity #{ref}')
            if ref not in found:
                found.add(ref)
                pending.append(ref)
    return sorted(found)

products = {}
for number, value in entities.items():
    if value.startswith('PRODUCT ('):
        match = re.match(r"PRODUCT \( '([^']+)'", value)
        if match:
            products[decode_step(match.group(1))] = number

for name in targets:
    product = products[name]
    formation = unique_child(product, 'PRODUCT_DEFINITION_FORMATION')
    definition = unique_child(formation, 'PRODUCT_DEFINITION ')
    shape = unique_child(definition, 'PRODUCT_DEFINITION_SHAPE')
    shape_definition = unique_child(shape, 'SHAPE_DEFINITION_REPRESENTATION')
    representation = int(re.findall(r'#(\d+)', entities[shape_definition])[-1])
    relations = [i for i in back.get(representation, ())
                 if entities[i].startswith('SHAPE_REPRESENTATION_RELATIONSHIP')]
    brep_relations = [i for i in relations if any(
        entities[int(ref)].startswith('ADVANCED_BREP_SHAPE_REPRESENTATION')
        for ref in re.findall(r'#(\d+)', entities[i]))]
    if len(brep_relations) != 1:
        raise RuntimeError(f'{name}: expected one BREP relation, found {brep_relations}')
    numbers = closure([product, formation, definition, shape, shape_definition,
                       representation, brep_relations[0]])
    breps = sum(entities[i].startswith('MANIFOLD_SOLID_BREP') for i in numbers)
    if breps < 1:
        raise RuntimeError(f'{name}: no solid BREP')
    out = destination / (name + '.STEP')
    out.write_text(header + '\n' + ''.join(
        f'#{i} = {entities[i]};\n' for i in numbers) +
        'ENDSEC;\nEND-ISO-10303-21;\n', encoding='latin1')
    print(f'{name}: {len(numbers)} entities, {breps} BREP, {out.stat().st_size} bytes')
