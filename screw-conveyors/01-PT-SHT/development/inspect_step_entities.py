from pathlib import Path
import re

step = next(Path('outputs').rglob('*КТ*.STEP'))
source = step.read_text(encoding='latin1')
entities = {int(i): s for i, s in re.findall(r'#(\d+)\s*=\s*(.*?);', source, re.S)}
back = {}
for i, s in entities.items():
    for ref in set(int(n) for n in re.findall(r'#(\d+)', s)):
        back.setdefault(ref, []).append(i)

matches = [(i, s) for i, s in entities.items() if s.startswith('PRODUCT (') and 'DIN 933' in s]
for prod, string in matches:
    print('PRODUCT', prod, string[:180])
    frontier = [prod]
    seen = set(frontier)
    for depth in range(5):
        next_frontier = []
        for i in frontier:
            for child in back.get(i, []):
                if child in seen:
                    continue
                t = entities[child]
                if t.startswith(('PRODUCT_DEFINITION_FORMATION', 'PRODUCT_DEFINITION ', 'PRODUCT_DEFINITION_SHAPE', 'SHAPE_DEFINITION_REPRESENTATION', 'SHAPE_REPRESENTATION_RELATIONSHIP')):
                    print(' ', depth, child, t[:220].replace('\n',' '))
                    seen.add(child)
                    next_frontier.append(child)
        frontier = next_frontier
print('ENTITIES', len(entities))
