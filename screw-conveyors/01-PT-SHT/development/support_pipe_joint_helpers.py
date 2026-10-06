import math
import pythoncom,win32com.client as w

def point(component,p):
    t=list(component.Transform2.ArrayData)
    return [sum(p[j]*t[j*3+i] for j in range(3))+t[9+i] for i in range(3)]

def direction(component,p):
    t=list(component.Transform2.ArrayData)
    return [sum(p[j]*t[j*3+i] for j in range(3)) for i in range(3)]

def plane_face(component,x):
    choices=[]
    for body in component.GetModelDoc2.GetBodies2(0,True):
        for face in body.GetFaces():
            if not face.GetSurface.IsPlane:continue
            params=list(face.GetSurface.PlaneParams);p=point(component,params[3:6]);n=direction(component,list(face.Normal))
            if abs(p[0]-x)<1e-7 and abs(n[0])>.999999:choices.append((face.GetArea,face,n))
    assert choices,(component.Name2,x)
    return max(choices,key=lambda row:row[0])[1:]

def distance(document,a,b):
    p1=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_VARIANT,None)
    p2=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_VARIANT,None)
    value=document.ClosestDistance(a,b,p1,p2)
    if isinstance(value,tuple):value=value[0]
    assert value>=0,(a.Name2,b.Name2,value)
    return value*1000

def design(support):
    brace=next(c for c in support.GetComponents(True) if ".25.00.09 '" in c.Name2)
    post=next(c for c in support.GetComponents(True) if ".25.00.07 '" in c.Name2)
    bx,by,bz=list(brace.Transform2.ArrayData)[9:12]
    t=list(brace.Transform2.ArrayData)
    lx=(-.020-bx)/(-t[3])
    end_y=by-lx*t[4]
    slope=post.GetModelDoc2.Parameter('D1@Плоскость1').SystemValue
    # Join the brace centreline to the upright centreline at its outer X face.
    rise=-end_y*math.tan(slope)+float(post.Transform2.ArrayData[11])-bz
    angle=math.atan(rise/lx)
    assert lx>0 and 0<angle<math.pi/3,(lx,angle)
    return brace,post,{'length_plane_m':lx,'flare_angle_rad':angle,'join_y_m':end_y,
                       'join_x_m':-.020,'join_z_m':bz+rise,'pin_xyz_m':[bx,by,bz]}

def verify(support):
    rows=[]
    cs=list(support.GetComponents(True))
    post1=next(c for c in cs if ".25.00.07 '" in c.Name2)
    post2=next(c for c in cs if ".25.00.07-01 '" in c.Name2)
    brace1=next(c for c in cs if ".25.00.09 '" in c.Name2)
    brace2=next(c for c in cs if ".25.00.09-01 '" in c.Name2)
    for a,b in [(brace1,post1),(brace2,post2)]+[(c,p) for c in cs if 'Балка' in c.Name2 for p in (post1,post2)]:
        gap=distance(support,a,b)
        rows.append({'first':a.Name2,'second':b.Name2,'gap_mm':gap,'ok':gap<=.001})
    return {'ok':all(r['ok'] for r in rows),'connections':rows,'tolerance_mm':.001}
