"""Compare saved inputs, native feature dimensions and the resulting solid geometry."""
from pathlib import Path
from datetime import datetime
import ast, math, re, sys, json, operator
import pythoncom, win32com.client as w

base=Path('outputs/Шнек 1 — параметрическая модель').resolve()
sys.path.insert(0,str(base))
import bridge
state=json.loads(bridge.STATE.read_text(encoding='utf-8'))
sw=w.GetActiveObject('SldWorks.Application')
print('Read the rebuilt assembly' if '--read-only' in sys.argv else 'Rebuild and validate the current assembly',flush=True)
result=({'ok':True,**state} if '--read-only' in sys.argv else
        bridge.apply(state['values'],sw,state['selection'],state['design_mode']))
assert result['ok'],result
previous=sw.CommandInProgress;sw.CommandInProgress=True

def arithmetic(text, variables=None):
    variables=variables or {}
    text=re.sub(r'"([^"]+)"',lambda m:str(variables[m[1]]),text)
    text=text.replace('мм','').replace('градусов','').replace('град','').strip()
    operations={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv}
    def visit(node):
        if isinstance(node,ast.Constant) and isinstance(node.value,(float,int)):return node.value
        if isinstance(node,ast.BinOp) and type(node.op) in operations:return operations[type(node.op)](visit(node.left),visit(node.right))
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,ast.USub):return -visit(node.operand)
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='atn' and len(node.args)==1:
            return math.degrees(math.atan(visit(node.args[0])))
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and len(node.args)==1 and node.func.id in ('sin','cos'):
            return getattr(math,node.func.id)(math.radians(visit(node.args[0])))
        raise ValueError('Unexpected equation expression')
    return float(visit(ast.parse(text,mode='eval').body))

def component(kind, text):
    return next(c for c in docs[kind].GetComponents(True) if text in c.Name2)

def value(kind,text,dimension):
    part=component(kind,text).GetModelDoc2
    dimension_object=part.Parameter(dimension)
    assert dimension_object,(text,dimension)
    return float(dimension_object.SystemValue)*1000

def cylinders(part):
    return [list(f.GetSurface.CylinderParams) for b in part.GetBodies2(0,True)
            for f in b.GetFaces() if f.GetSurface.IsCylinder]

def exact_extent(part,direction):
    coordinates=[]
    for body in part.GetBodies2(0,True):
        answer=body.GetExtremePoint(*direction,0.,0.,0.)
        assert answer[0]
        coordinates.append(list(answer[1:]))
    return max(coordinates,key=lambda p:sum(p[i]*direction[i] for i in range(3)))

try:
    docs={k:sw.GetOpenDocumentByName(str(p)) for k,p in bridge.FILES.items()}
    variables={kind:{} for kind in docs}
    globals_checked=[];bindings=[]
    for key,targets in bridge.FIELDS.items():
        for kind,name in targets:
            expected=arithmetic(bridge.equation_for(name,key,state['values'][key]).split('=',1)[1])
            variables[kind][name]=expected
            manager,globals_=bridge.globals_in(docs[kind])
            actual=arithmetic(globals_[name][1].split('=',1)[1])
            globals_checked.append({'parameter':key,'kind':kind,'variable':name,'expected':expected,'actual':actual,'match':abs(actual-expected)<1e-6})
    for kind,doc in docs.items():
        manager=doc.GetEquationMgr
        parts={Path(c.GetPathName).stem:c.GetModelDoc2 for c in doc.GetComponents(True) if c.GetPathName}
        pending=[]
        for i in range(manager.GetCount):
            lhs,rhs=manager.Equation(i).split('=',1);lhs=lhs.strip().strip('"')
            if '@' not in lhs:pending.append((lhs,rhs))
        while pending:
            remaining=[]
            for name,expression in pending:
                try:variables[kind][name]=arithmetic(expression,variables[kind])
                except KeyError:remaining.append((name,expression))
            assert len(remaining)<len(pending),remaining
            pending=remaining
        for i in range(manager.GetCount):
            equation=manager.Equation(i)
            lhs,rhs=equation.split('=',1);lhs=lhs.strip().strip('"')
            if '@' not in lhs:continue
            expected=arithmetic(rhs,variables[kind])
            tokens=lhs.split('@',2)
            target=doc
            if len(tokens)==3:
                target=parts[tokens[2].rsplit('<',1)[0]]
            dimension_name='@'.join(tokens[:2])
            dimension=target.Parameter(dimension_name)
            assert dimension,(kind,lhs)
            raw=float(dimension.SystemValue)
            if ((kind=='support' and dimension_name in ('D1@ПЛОСКОСТЬ3','D1@Плоскость1')) or
                (('Угол наклона' in rhs or 'град' in rhs) and 'sin(' not in rhs and 'cos(' not in rhs)):
                actual=math.degrees(raw);unit='degrees'
            elif dimension_name=='D1@Линейный массив1':
                actual=raw;unit='count'
            else:
                actual=raw*1000;unit='mm'
            bindings.append({'kind':kind,'dimension':lhs,'equation':equation,'expected':expected,
                             'actual':actual,'unit':unit,'match':abs(actual-expected)<1e-5})
    measured=result['cad_verification']['measured_geometry']
    native={
        'working_length':value('tube','Труба шнека','D1@Вытянуть-Тонкостенный1')-270,
        'tube_diameter':measured['tube_diameter'],
        'tube_wall':value('tube','Труба шнека','D5@Вытянуть-Тонкостенный1'),
        'incline':measured['incline'],
        'inlet_diameter':value('tube','Патрубок шнека','D1@Эскиз1'),
        'inlet_length':value('tube','Патрубок шнека','D1@Вытянуть-Тонкостенный1'),
        'inlet_wall':value('tube','Патрубок шнека','D5@Вытянуть-Тонкостенный1'),
        'flange_thickness':value('tube','Фланец трубы','D1@Бобышка-Вытянуть1'),
        'mounting_hole_diameter':value('tube','Фланец трубы','D4@Эскиз1'),
        'opening_diameter':value('tube','Труба шнека','D1@Эскиз10'),
        'screw_diameter':value('screw','Торец шнека','D1@Эскиз1'),
        'pitch':value('screw','Винт шнека','D4@Спираль1'),
        'blade_thickness':value('screw','Винт шнека','D2@Эскиз5'),
        'shaft_diameter':value('screw','Сердечник','D1@Эскиз1'),
        'shaft_wall':value('screw','Сердечник','D5@Вытянуть-Тонкостенный1'),
        'turns':value('screw','Винт шнека','D1@Линейный массив1')/1000,
    }
    for key,(path,names) in bridge.PART_FIELDS.items():
        part=sw.GetOpenDocumentByName(str(path))
        native[key]=sum(float(part.Parameter(name).SystemValue)*1000 for name in names)
    pipe=component('tube','Труба шнека').GetModelDoc2
    port=component('tube','Патрубок шнека').GetModelDoc2
    core=component('screw','Сердечник').GetModelDoc2
    flange=component('tube','Фланец трубы').GetModelDoc2
    blade=component('screw','Винт шнека').GetModelDoc2
    cut=pipe.FeatureByName('Вырез-Вытянуть5')
    opening_present=not bool(cut.IsSuppressed)
    parameters=[]
    for key,requested in state['values'].items():
        expected=requested+.8 if key=='mounting_hole_diameter' else requested
        present=opening_present if key=='opening_diameter' else True
        parameters.append({'parameter':key,'requested':requested,'expected_native':expected,
                           'native':native[key],'dimensions_match':abs(native[key]-expected)<1e-5,
                           'feature_active':present,'match':abs(native[key]-expected)<1e-5 and present,
                           'note':'M nominal; clearance hole is M + 0.8 mm' if key=='mounting_hole_diameter' else
                                  'Sketch dimension exists; cut is suppressed, so the opening is absent' if key=='opening_diameter' and not present else ''})
    physical={}
    for name,part in [('pipe',pipe),('port',port),('core',core),('flange',flange)]:
        physical[name]={'cylinders':cylinders(part),'bbox':list(part.GetPartBox(True)),
                        'axis_y_length_mm':(exact_extent(part,(0.,1.,0.))[1]-exact_extent(part,(0.,-1.,0.))[1])*1000}
    physical['blade']={'solid_bodies':len(blade.GetBodies2(0,True)), 'bbox_approximate':list(blade.GetPartBox(True))}
    braces=[]
    for brace in docs['support'].GetComponents(True):
        if 'Подкос' in brace.Name2:
            part=brace.GetModelDoc2;bodies=list(part.GetBodies2(0,True))
            assert len(bodies)==1,brace.Name2
            braces.append({'component':brace.Name2,'file':brace.GetPathName,'solid_bodies':len(bodies),
                           'volume_mm3':sum(body.GetMassProperties(1)[3] for body in bodies)*1e9,
                           'strength_verified':False})
    assert len(braces)==2
    physical['support_braces']=braces
    project=json.loads((base/'project.json').read_text(encoding='utf-8'))
    audit={'timestamp':datetime.now().astimezone().isoformat(timespec='seconds'),
           'requested_values':state['values'],'parameters':parameters,'globals':globals_checked,'bindings':bindings,
           'verification':result['cad_verification'],'physical':physical,
           'project_angle':{'requested':project['target_incline_deg'],'actual':measured['incline'],
                            'match':abs(project['target_incline_deg']-measured['incline'])<1e-5},
           'opening_cut':{'name':cut.Name,'suppressed':bool(cut.IsSuppressed),'error':cut.GetErrorCode}}
    (base/'parameter_correspondence_20261005.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Parameters:',[(r['parameter'],r['match'],r['native']) for r in parameters],flush=True)
    print('Bound dimensions:',len(bindings),'mismatches:',[r for r in bindings if not r['match']],flush=True)
    print('Physical axial lengths:',{k:v.get('axis_y_length_mm') for k,v in physical.items() if isinstance(v,dict)},flush=True)
    print('Angle target:',audit['project_angle'],'opening:',audit['opening_cut'],flush=True)
finally:
    sw.CommandInProgress=previous
