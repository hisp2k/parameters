from pathlib import Path

page = Path('outputs/Шнек 1 — параметрическая модель/index.html')
html = page.read_text(encoding='utf-8')
needle = '</svg></section>'
if html.count(needle) != 1 or 'id="dimensionsPanel"' in html:
    raise SystemExit('Schematic location is not unique or dimensions already exist')
panel = '''<g id="dimensionsPanel">
<rect x="316" y="407" width="474" height="51" rx="10" fill="#102a35" fill-opacity=".94" stroke="#63828a" stroke-width="1"/>
<path d="M411 415v35 M506 415v35 M601 415v35 M696 415v35" stroke="#54727a" stroke-width="1"/>
<g fill="#a8c1c5" font-size="9" font-weight="700" text-anchor="middle">
<text x="364" y="426">L РАБОЧАЯ</text><text x="459" y="426">L ПОЛНАЯ</text>
<text x="554" y="426">Ø ТРУБЫ</text><text x="649" y="426">Ø ВИНТА</text><text x="743" y="426">ШАГ</text>
</g>
<g fill="#f1f7f1" font-size="14" font-weight="800" text-anchor="middle">
<text id="dimWorking" x="364" y="447">—</text><text id="dimFull" x="459" y="447">—</text>
<text id="dimTube" x="554" y="447">—</text><text id="dimScrew" x="649" y="447">—</text>
<text id="dimPitch" x="743" y="447">—</text>
</g></g>'''
html = html.replace(needle, panel + needle, 1)
needle = "$('drawingLength').textContent=fmt(v.working_length)+' мм';"
if html.count(needle) != 1:
    raise SystemExit('Render length assignment not unique')
assignments = (
    "$('dimWorking').textContent=fmt(v.working_length)+' мм';"
    "$('dimFull').textContent=fmt(v.working_length+270)+' мм';"
    "$('dimTube').textContent='Ø '+fmt(v.tube_diameter)+' мм';"
    "$('dimScrew').textContent='Ø '+fmt(v.screw_diameter)+' мм';"
    "$('dimPitch').textContent=fmt(v.pitch)+' мм';"
)
html = html.replace(needle, needle + assignments, 1)
page.write_text(html, encoding='utf-8')
print('Updated', page)
