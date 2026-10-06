from pathlib import Path
import pythoncom
import win32com.client as w

root = Path('work/simulation_test/25.SHT.G_parameterized').resolve()
part = list(root.glob('*02.00.00.02*Вал*SLDPRT'))[0]
sw = w.Dispatch('SldWorks.Application')
lib = Path(sw.GetExecutablePath) / 'lang/english/sldmaterials/solidworks materials.sldmat'
print('material library', lib, lib.exists(), flush=True)
e = w.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
warn = w.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
m = sw.OpenDoc6(str(part), 1, 1, '', e, warn)
sw.ActivateDoc2(m.GetTitle, False, e)
add = sw.GetAddInObject('SldWorks.Simulation')
if not add:
    print('load', sw.LoadAddIn(str(Path(sw.GetExecutablePath) / 'Simulation/cosworks.dll')), flush=True)
    add = sw.GetAddInObject('SldWorks.Simulation')
cw = add.COSMOSWORKS
doc = cw.ActiveDoc
sm = doc.StudyManager
study = sm.CreateNewStudy3('PROBE_LOADS_5', 0, 0, e)
print('study', bool(study), e.value, flush=True)
solid = study.SolidManager
comp = solid.GetComponentAt(0, e)
body = comp.GetSolidBodyAt(0, e)
print('body', bool(body), e.value, flush=True)
print('material', body.SetLibraryMaterial(str(lib), 'Plain Carbon Steel'), flush=True)
faces = m.GetBodies2(0, False)[0].GetFaces()
fixed = next(f for f in faces if f.GetSurface.IsPlane and abs(f.GetBox[2]) < 1e-8 and abs(f.GetBox[5]) < 1e-8 and f.GetArea > .004)
free = next(f for f in faces if f.GetSurface.IsPlane and abs(f.GetBox[2]+.3075) < 1e-8 and abs(f.GetBox[5]+.3075) < 1e-8 and f.GetArea > .002)
cyl = next(f for f in faces if f.GetSurface.IsCylinder and f.GetArea > .05)
print('faces', fixed.GetArea, free.GetArea, cyl.GetArea, flush=True)
mgr = study.LoadsAndRestraintsManager
e.value = 0
fixed_array = w.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_VARIANT, [fixed])
free_array = w.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_VARIANT, [free])
null_disp = w.VARIANT(pythoncom.VT_DISPATCH, None)
fixture = mgr.AddRestraint(0, fixed_array, null_disp, e)
print('fixture', bool(fixture), e.value, flush=True)
e.value = 0
force = mgr.AddForce2(1, 0, free_array, null_disp, e)
print('force', bool(force), e.value, flush=True)
if force:
    print('begin edit', force.ForceBeginEdit(), flush=True)
    force.Unit = 0
    force.NormalForceOrTorqueValue = 1000.0
    print('end edit', force.ForceEndEdit, flush=True)
e.value = 0
torque = mgr.AddForce2(2, 0, free_array, cyl, e)
print('torque', bool(torque), e.value, flush=True)
if torque:
    print('begin edit torque', torque.ForceBeginEdit(), flush=True)
    torque.Unit = 0
    torque.NormalForceOrTorqueValue = 100.0
    print('end edit torque', torque.ForceEndEdit, flush=True)
mesh = study.Mesh
mesh.MesherType = 0
mesh.Quality = 1
el = w.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_R8, 0.0)
tol = w.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_R8, 0.0)
print('default size', mesh.GetDefaultElementSizeAndTolerance(0, el, tol), el.value, tol.value, flush=True)
print('create mesh', study.CreateMesh(0, el.value, tol.value), flush=True)
print('run analysis', study.RunAnalysis, flush=True)
res = study.Results
print('results', bool(res), flush=True)
if res:
    e.value = 0
    print('stress', res.GetMinMaxStress(9, 0, 0, None, 0, e), e.value, flush=True)
    e.value = 0
    print('disp', res.GetMinMaxDisplacement(3, 0, None, 0, e), e.value, flush=True)
print('save', m.Save3(1, e, warn), e.value, warn.value, flush=True)
sw.CloseDoc(m.GetTitle)
