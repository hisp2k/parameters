from pathlib import Path

page = Path('outputs/Шнек 1 — параметрическая модель/index.html')
html = page.read_text(encoding='utf-8')

def replace_once(before, after):
    global html
    if html.count(before) != 1:
        raise SystemExit(f'Expected one match, found {html.count(before)}: {before[:100]!r}')
    html = html.replace(before, after, 1)

replace_once('const PORT_COUNTS={inlet:2,outlet:1,wash:2};',
             'const PORT_COUNTS={inlet:1,outlet:1,wash:2};')
replace_once(
    "$('dimOutlet').textContent=PORT_COUNTS.outlet+' × Ø '+fmt(v.discharger_diameter)+' мм';",
    "$('dimOutlet').textContent=PORT_COUNTS.outlet+' × Ø '+fmt(v.inlet_diameter)+' мм';"
    "$('dimPortAngle').textContent=fmt(v.incline)+'°';",
)
replace_once(
    "summaryGroup(root,'Входы и выход',[['Патрубки шнека',PORT_COUNTS.inlet+' шт. · Ø '+fmt(v.inlet_diameter)+' мм'],['Проём сбрасывателя',PORT_COUNTS.outlet+' шт. · Ø '+fmt(v.discharger_diameter)+' мм'],['Патрубки промывки',PORT_COUNTS.wash+' шт. · диаметр не задан в форме'],]);",
    "summaryGroup(root,'Вход и выход',["
    "['Нижний вход',PORT_COUNTS.inlet+' шт. · Ø '+fmt(v.inlet_diameter)+' мм · '+fmt(v.incline)+'° к корпусу'],"
    "['Верхний выход',PORT_COUNTS.outlet+' шт. · Ø '+fmt(v.inlet_diameter)+' мм · '+fmt(v.incline)+'° к корпусу'],"
    "['Патрубки промывки',PORT_COUNTS.wash+' шт. · не являются входами груза'],"
    "['Сбрасыватель','отдельная деталь; назначение не установлено'],"
    "]);",
)
page.write_text(html, encoding='utf-8')
print('Updated', page)
