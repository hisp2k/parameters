from pathlib import Path

page = Path('outputs/Шнек 1 — параметрическая модель/index.html')
html = page.read_text(encoding='utf-8')

def replace_once(before, after):
    global html
    if html.count(before) != 1:
        raise SystemExit(f'Expected one match, found {html.count(before)}: {before[:100]!r}')
    html = html.replace(before, after, 1)

replace_once(
    '<clipPath id="tubeClip"><rect x="88" y="55" width="615" height="82" rx="5"/></clipPath></defs>',
    '<clipPath id="tubeClip"><rect x="88" y="55" width="615" height="82" rx="5"/></clipPath>'
    '<marker id="flowIn" viewBox="0 0 18 18" markerWidth="18" markerHeight="18" '
    'refX="14" refY="9" orient="auto" markerUnits="userSpaceOnUse">'
    '<path d="M2 2l13 7-13 7z" fill="#c7ed62"/></marker>'
    '<marker id="flowOut" viewBox="0 0 18 18" markerWidth="18" markerHeight="18" '
    'refX="14" refY="9" orient="auto" markerUnits="userSpaceOnUse">'
    '<path d="M2 2l13 7-13 7z" fill="#f8cc83"/></marker></defs>',
)
replace_once(
    '<path d="M230 44v-28h95v28M565 44v-28h95v28" fill="none" stroke="#aac3c5" stroke-width="7"/>',
    '',
)
replace_once(
    '</g><path id="angleArc"',
    '''</g><g id="flowPorts">
<line id="portInTube" stroke="#a9c5c5" stroke-width="17" stroke-linecap="round"/>
<line id="portOutTube" stroke="#a9c5c5" stroke-width="17" stroke-linecap="round"/>
<line id="portInArrow" stroke="#c7ed62" stroke-width="5" stroke-linecap="round" marker-end="url(#flowIn)"/>
<line id="portOutArrow" stroke="#f8cc83" stroke-width="5" stroke-linecap="round" marker-end="url(#flowOut)"/>
<path id="portInArc" fill="none" stroke="#c7ed62" stroke-width="2"/>
<path id="portOutArc" fill="none" stroke="#f8cc83" stroke-width="2"/>
<g fill="#f4f7f0" font-size="13" font-weight="800" stroke="#102a35" stroke-width="3" paint-order="stroke" text-anchor="middle">
<text id="portInText">ВХОД</text><text id="portOutText">ВЫХОД</text>
</g></g><path id="angleArc"''',
)
replace_once(
    'return {matrix:`matrix(${a} ${b} ${c} ${d} ${e} ${f})`,x,y,arc,',
    'return {matrix:`matrix(${a} ${b} ${c} ${d} ${e} ${f})`,x,y,arc,co,si,scale,',
)
helper = '''function setSchematicLine(id,x1,y1,x2,y2){
 const line=$(id);line.setAttribute('x1',x1);line.setAttribute('y1',y1);
 line.setAttribute('x2',x2);line.setAttribute('y2',y2);
}
function setSchematicText(id,x,y,label){
 const element=$(id);element.setAttribute('x',x);element.setAttribute('y',y);
 element.textContent=label;
}
function updatePortGeometry(pose,angle){
 const {x,y,co,si,scale}=pose;
 const along=fraction=>({x:x+615*scale*fraction*co,y:y-615*scale*fraction*si});
 const inlet=along(.18),outlet=along(.82);
 const reach=68;
 setSchematicLine('portInTube',inlet.x-reach,inlet.y,inlet.x-9,inlet.y);
 setSchematicLine('portInArrow',inlet.x-reach-5,inlet.y,inlet.x-12,inlet.y);
 setSchematicLine('portOutTube',outlet.x+9,outlet.y,outlet.x+reach,outlet.y);
 setSchematicLine('portOutArrow',outlet.x+12,outlet.y,outlet.x+reach+5,outlet.y);
 const r=30,mainArc=(point)=>angle<.001?'':`M ${point.x+r} ${point.y} A ${r} ${r} 0 0 0 ${point.x+r*co} ${point.y-r*si}`;
 $('portInArc').setAttribute('d',mainArc(inlet));
 $('portOutArc').setAttribute('d',mainArc(outlet));
 setSchematicText('portInText',Math.max(60,inlet.x-reach/2),inlet.y-18,`ВХОД · ${fmt(angle)}°`);
 setSchematicText('portOutText',Math.min(720,outlet.x+reach/2),outlet.y-18,`ВЫХОД · ${fmt(angle)}°`);
}
'''
replace_once('function updateSchematic(angle){', helper + 'function updateSchematic(angle){')
replace_once("$('conveyorDrawing').setAttribute('transform',pose.matrix);",
             "$('conveyorDrawing').setAttribute('transform',pose.matrix);updatePortGeometry(pose,valid?angle:0);")
page.write_text(html, encoding='utf-8')
print('Updated', page)
