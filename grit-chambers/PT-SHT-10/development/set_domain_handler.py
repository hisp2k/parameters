import win32com.client as w
s=w.Dispatch('SldWorks.Application')
print('doc',s.ActiveDoc.GetPathName,flush=True)
h=s.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI().IActiveDoc.IActiveProject
for n in ['ComputationalDomainXmin','ComputationalDomainXmax','ComputationalDomainYmin','ComputationalDomainYmax','ComputationalDomainZmin','ComputationalDomainZmax']:
 try:print(n,getattr(h,n),flush=True)
 except Exception as e:print(n,'ERR',repr(e),flush=True)
for n,v in [('ComputationalDomainXmin',-.38),('ComputationalDomainXmax',.38),('ComputationalDomainYmin',-.02),('ComputationalDomainYmax',.90),('ComputationalDomainZmin',-.38),('ComputationalDomainZmax',.40)]:
 try:setattr(h,n,v);print('set',n,'ok',flush=True)
 except Exception as e:print('set',n,repr(e),flush=True)
for n in ['ComputationalDomainXmin','ComputationalDomainXmax','ComputationalDomainYmin','ComputationalDomainYmax','ComputationalDomainZmin','ComputationalDomainZmax']:
 try:print('after',n,getattr(h,n),flush=True)
 except Exception as e:print('after',n,'ERR',repr(e),flush=True)
