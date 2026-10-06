from pathlib import Path
import re

page = Path('outputs/Шнек 1 — параметрическая модель/index.html')
html = page.read_text(encoding='utf-8')
match = re.search(r'<svg viewBox="0 0 800 190"[^>]*>(.*?)</svg>', html, re.S)
if not match:
    raise SystemExit('Original schematic not found')
head, drawing = match.group(1).split('</defs>', 1)
svg = (
    '<svg id="conveyorSchematic" viewBox="0 0 800 460" role="img" '
    'aria-label="Схема шнекового транспортера, наклон 55 градусов">'
    + head + '</defs>'
    + '<line id="angleBase" x1="110" y1="370" x2="360" y2="370" '
      'stroke="#80a9ae" stroke-width="2" stroke-dasharray="8 6"/>'
    + '<g id="conveyorDrawing">' + drawing + '</g>'
    + '<path id="angleArc" fill="none" stroke="#f8cc83" stroke-width="3"/>'
    + '<text id="angleLabel" fill="#f8cc83" font-size="17" font-weight="800" '
      'text-anchor="middle">55°</text>'
    + '<text x="755" y="44" fill="#d4e4df" font-size="12" text-anchor="end">'
      'УГОЛ НАКЛОНА <tspan id="angleReadout" fill="#f8cc83">55°</tspan></text>'
    + '</svg>'
)
html = html[:match.start()] + svg + html[match.end():]
html = html.replace('</style>',
    '.visual{min-height:420px}.visual svg{top:15%;height:81%}'
    '@media(max-width:760px){.visual{min-height:340px}.visual svg{top:17%;height:78%}}\n'
    '</style>', 1)
helper = '''function schematicPose(angle){
 const radians=Math.max(0,Math.min(angle,89.999))*Math.PI/180;
 const co=Math.cos(radians),si=Math.sin(radians);
 const scale=Math.min(1,640/(690*co+145*si),300/(690*si+145*co));
 const x=110,y=260+135*si,pivotX=88,pivotY=96;
 const a=scale*co,b=-scale*si,c=scale*si,d=scale*co;
 const e=x-a*pivotX-c*pivotY,f=y-b*pivotX-d*pivotY;
 const r=88,arcEndX=x+r*co,arcEndY=y-r*si;
 const arc=radians<0.000001?'':`M ${x+r} ${y} A ${r} ${r} 0 0 0 ${arcEndX} ${arcEndY}`;
 return {matrix:`matrix(${a} ${b} ${c} ${d} ${e} ${f})`,x,y,arc,
  labelX:x+125,labelY:Math.min(440,y+75*scale+20)};
}
function updateSchematic(angle){
 const valid=Number.isFinite(angle)&&angle>=0&&angle<90;
 const pose=schematicPose(valid?angle:0);
 $('conveyorDrawing').setAttribute('transform',pose.matrix);
 $('angleBase').setAttribute('y1',pose.y);
 $('angleBase').setAttribute('y2',pose.y);
 $('angleArc').setAttribute('d',pose.arc);
 $('angleLabel').setAttribute('x',pose.labelX);
 $('angleLabel').setAttribute('y',pose.labelY);
 const label=valid?`${fmt(angle)}°`:'—';
 $('angleLabel').textContent=label;
 $('angleReadout').textContent=label;
 $('conveyorSchematic').setAttribute('aria-label',valid?`Схема шнекового транспортера, угол наклона ${fmt(angle)} градусов`:'Схема шнекового транспортера, угол не задан');
}
'''
needle = 'function render(){'
if html.count(needle) != 1:
    raise SystemExit('Render entry point not unique')
html = html.replace(needle, helper + needle, 1)
needle = "const gostMode=designMode()==='gost';"
if html.count(needle) != 1:
    raise SystemExit('Render mode check not unique')
html = html.replace(needle, needle + 'updateSchematic(v.incline);', 1)
page.write_text(html, encoding='utf-8')
print('Updated', page)
