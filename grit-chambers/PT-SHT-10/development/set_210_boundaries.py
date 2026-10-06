from pathlib import Path
import json
import win32com.client as win32
exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
assert p.GetName()=='PT-SHT-10-210L-cloned'
sw=win32.Dispatch('SldWorks.Application')
cad=sw.ActiveDoc
assert 'PT-SHT-10-210L.SLDASM' in cad.GetPathName
ui=sw.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI().IActiveDoc.IActiveProject
features=typed(p.GetFeatures(),'IProjectFeatures')
existing=features.GetFeatures2(True,0) or []
assert len(existing)<=1, [(x.GetName(),x.GetUUID()) for x in existing]
log=[]
app.SetSilent()
try:
    for comp,axis,coord,fc,param,val,label in [
        ('CAD210_shift_06-1',2,.329,1,18,10/3600,'Inlet 10 m3h'),
        ('CFD_outlet_flange_lid-2',2,0.,10,3,101325.,'Main outlet pressure')]:
        if comp=='CAD210_shift_06-1' and existing:
            continue
        c=next(x for x in cad.GetComponents(False) if x.Name2==comp)
        face_candidates=[]
        for i,face in enumerate(c.GetBody.GetFaces()):
            box=face.GetBox
            print('FACE',comp,i,box,flush=True)
            if abs(box[axis]-coord)<1e-8 and abs(box[axis+3]-coord)<1e-8:
                face_candidates.append(face)
        assert len(face_candidates)==1, (comp,len(face_candidates))
        cad.ClearSelection2(True)
        assert face_candidates[0].Select2(False,0)
        assert cad.SelectionManager.GetSelectedObjectsComponent4(1,-1).Name2==comp
        bc_ui=ui.CreateTemplateBoundaryCondition()
        bc_ui.FCType=fc
        bc_ui.Name_=label
        refs=ui.UpdateFeatureTopolReferenciesFromSelection(0,bc_ui)
        print('REFS',comp,refs,bc_ui.GetReferencesNames(),flush=True)
        assert refs
        applied=bc_ui.ApplyUIChanges(ui,False,False)
        print('APPLIED',comp,applied,flush=True)
        assert applied
        stored=next(x for x in features.GetFeatures2(True,0) if x.GetUUID()==bc_ui.UUID_)
        bc=typed(stored,'IBoundaryCondition')
        bc.put_FCType(fc)
        bc.GetParameter(param).SetValue(val)
        log.append({'component':comp,'label':label,'type':fc,'parameter':param,'value':val,
                    'uuid':bc.GetUUID(),'refs':bc.GetTopologicalReferencesUUIDsAndNames(None,None)})
    cad.ClearSelection2(True)
    print('REBUILD',p.Rebuild(False,True,True,False,False,False),p.GetLastRebuildError(),flush=True)
    save_er=win32.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    save_wr=win32.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    print('SAVE',cad.Save3(1,save_er,save_wr),save_er.value,save_wr.value,flush=True)
finally:
    app.ResetSilent()
    Path('work/210_boundary_log.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
