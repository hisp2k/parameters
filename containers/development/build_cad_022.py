from pathlib import Path
import sys
import win32com.client as win32

OUT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent
OUT.mkdir(exist_ok=True)
TEMPLATE=Path(r'C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2026\templates')
MATDB=Path(r'C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2024\Настроенный пользователем материал\Библиотека материалов (ГОСТ).sldmat')
if not MATDB.exists():
    raise FileNotFoundError(f'Укажите путь к библиотеке материалов 09Г2С: {MATDB}')
sw=win32.Dispatch('SldWorks.Application')
sw.Visible=True

def feats(doc):
    out=[]; f=doc.FirstFeature
    while f:
        out.append(f); f=f.GetNextFeature
    return out

def plane(doc,name):
    return next(f for f in feats(doc) if f.Name==name)

def sketch_on(doc,pl):
    doc.ClearSelection2(True)
    assert pl.Select2(False,0)
    doc.SketchManager.InsertSketch(True)

def last_sketch(doc):
    return [f for f in feats(doc) if f.GetTypeName2=='ProfileFeature'][-1]

def save(doc,path):
    if path.exists():
        raise FileExistsError(f'Выберите пустую папку вывода: {path}')
    status=doc.SaveAs3(str(path),0,1)
    if not path.exists() or path.stat().st_size < 10000:
        raise RuntimeError(f'SolidWorks SaveAs3 failed: {path} status={status}')
    print('SAVED',path,'status',status,'bytes',path.stat().st_size)

body=sw.NewDocument(str(TEMPLATE/'gost-part.prtdot'),0,0,0)
top=plane(body,'Сверху')
sketch_on(body,top)
body.SketchManager.CreateCornerRectangle(-.295,-.295,0,.295,.295,0)
body.SketchManager.InsertSketch(True)
sk1=last_sketch(body)
body.ClearSelection2(True); top.Select2(False,0)
pl1=body.FeatureManager.InsertRefPlane(8,.62,0,0,0,0)
assert pl1
sketch_on(body,pl1)
body.SketchManager.CreateCornerRectangle(-.30,-.30,0,.30,.30,0)
body.SketchManager.InsertSketch(True)
sk2=last_sketch(body)
body.ClearSelection2(True); sk1.Select2(False,1); sk2.Select2(True,1)
loft=body.FeatureManager.InsertProtrusionBlend2(False,False,False,1,0,0,1,1,True,True,False,0,0,0,True,True,True,0)
assert loft
loft.Name='Корпус 590-600, H620'
topface=next(f for f in body.GetBodies2(0,False)[0].GetFaces() if f.Normal[1]>.9)
body.ClearSelection2(True)
seldata=body.SelectionManager.CreateSelectData; seldata.Mark=1
assert topface.Select4(False,seldata)
body.InsertFeatureShell(.0015,False)
shell=[f for f in feats(body) if f.GetTypeName2=='Shell'][-1]
shell.Name='Стенка и дно 1,5 мм'
body.ForceRebuild3(False)
body.SetMaterialPropertyName2('',str(MATDB),'09Г2С ГОСТ 4543-71')
body.SetUserPreferenceToggle(198,True)
body.ViewZoomtofit2()
body_path=OUT/'bin_022_body.SLDPRT'
save(body,body_path)

def wheel_part(kind):
    doc=sw.NewDocument(str(TEMPLATE/'gost-part.prtdot'),0,0,0)
    front=plane(doc,'Спереди')
    sketch_on(doc,front)
    doc.SketchManager.CreateCircleByRadius(0,0,0,.0625)
    doc.SketchManager.InsertSketch(True)
    sk=last_sketch(doc)
    doc.ClearSelection2(True); sk.Select2(False,0)
    ft=doc.FeatureManager.FeatureExtrusion2(False,False,False,0,0,.0175,.0175,False,False,False,False,0,0,False,False,False,False,True,True,True,0,0,False)
    assert ft,kind
    ft.Name='Колесо Ø125 × 35 (упрощено)'
    doc.ForceRebuild3(False)
    doc.SetUserPreferenceToggle(198,True)
    path=OUT/('wheel_fixed_D125.SLDPRT' if kind=='неповоротное' else 'wheel_swivel_D125.SLDPRT')
    save(doc,path)
    return doc,path

fixed,fixed_path=wheel_part('неповоротное')
swivel,swivel_path=wheel_part('поворотное')

plate=sw.NewDocument(str(TEMPLATE/'gost-part.prtdot'),0,0,0)
sketch_on(plate,plane(plate,'Сверху'))
plate.SketchManager.CreateCornerRectangle(-.05,-.05,0,.05,.05,0)
for xx in (-.035,.035):
    for zz in (-.035,.035):
        plate.SketchManager.CreateCircleByRadius(xx,zz,0,.0055)
plate.SketchManager.InsertSketch(True)
psk=last_sketch(plate)
plate.ClearSelection2(True); psk.Select2(False,0)
pft=plate.FeatureManager.FeatureExtrusion2(True,False,False,0,0,.004,0,False,False,False,False,0,0,False,False,False,False,True,True,True,0,0,False)
assert pft
pft.Name='Пластина 100х100х4, 4 отв. Ø11'
plate.ForceRebuild3(False)
plate.SetMaterialPropertyName2('',str(MATDB),'09Г2С ГОСТ 4543-71')
plate.SetUserPreferenceToggle(198,True)
plate_path=OUT/'mount_plate_100x100x4.SLDPRT'
save(plate,plate_path)

asm=sw.NewDocument(str(TEMPLATE/'gost-assy.asmdot'),0,0,0)
assert asm
def add(path,x,y,z):
    comp=asm.AddComponent5(str(path),0,'',False,'',x,y,z)
    assert comp, path
    print('ADDED',comp.Name2,x,y,z)
    return comp
add(body_path,0,.31,0)
for z in (-.22,.22):
    add(plate_path,-.22,-.002,z)
    add(plate_path,.22,-.002,z)
    add(fixed_path,-.22,-.08,z)
    add(swivel_path,.22,-.08,z)
asm.ForceRebuild3(False)
asm.SetUserPreferenceToggle(198,True)
asm.ViewZoomtofit2()
asm_path=OUT/'bin_022m3.SLDASM'
save(asm,asm_path)

# Native SolidWorks drawing with standard views; annotated manufacturing PDF is
# produced by build_drawings.py.
dwg=sw.NewDocument(str(TEMPLATE/'gost-assly drw.drwdot'),0,0,0)
assert dwg
ok=dwg.Create3rdAngleViews2(str(asm_path))
print('THREE VIEWS',ok)
dwg.ForceRebuild3(False)
dwg.SetUserPreferenceToggle(198,True)
dwg_path=OUT/'bin_022_assembly.SLDDRW'
save(dwg,dwg_path)

for model_path,drw_name in [(body_path,'bin_022_body.SLDDRW'),
                            (plate_path,'bin_022_mount_plate.SLDDRW')]:
    dr=sw.NewDocument(str(TEMPLATE/'gost-part drw.drwdot'),0,0,0)
    assert dr and dr.Create3rdAngleViews2(str(model_path))
    dr.ForceRebuild3(False)
    dr.SetUserPreferenceToggle(198,True)
    save(dr,OUT/drw_name)
