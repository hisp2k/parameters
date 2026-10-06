from pathlib import Path

page = Path('outputs/Шнек 1 — параметрическая модель/index.html')
html = page.read_text(encoding='utf-8')

def replace_once(before, after):
    global html
    if html.count(before) != 1:
        raise SystemExit(f'Expected one match, found {html.count(before)}: {before[:90]!r}')
    html = html.replace(before, after, 1)

replace_once(
    'let original={},catalog={},materials={},calcReady=false,calcTimer=0,calcSeq=0;',
    'const PORT_COUNTS={inlet:2,outlet:1,wash:2};'
    'let original={},catalog={},materials={},calcReady=false,calcTimer=0,calcSeq=0;',
)
replace_once(
    "$('dimScrew').textContent='Ø '+fmt(v.screw_diameter)+' мм';$('dimPitch').textContent=fmt(v.pitch)+' мм';",
    "$('dimInlet').textContent=PORT_COUNTS.inlet+' × Ø '+fmt(v.inlet_diameter)+' мм';"
    "$('dimOutlet').textContent=PORT_COUNTS.outlet+' × Ø '+fmt(v.discharger_diameter)+' мм';",
)
replace_once(
    "summaryGroup(root,'Выбор по стандартам',[",
    "summaryGroup(root,'Входы и выход',["
    "['Патрубки шнека',PORT_COUNTS.inlet+' шт. · Ø '+fmt(v.inlet_diameter)+' мм'],"
    "['Проём сбрасывателя',PORT_COUNTS.outlet+' шт. · Ø '+fmt(v.discharger_diameter)+' мм'],"
    "['Патрубки промывки',PORT_COUNTS.wash+' шт. · диаметр не задан в форме'],"
    "]);summaryGroup(root,'Выбор по стандартам',[",
)
page.write_text(html, encoding='utf-8')
print('Updated', page)
