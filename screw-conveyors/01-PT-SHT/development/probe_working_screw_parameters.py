exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
c=next(c for c in doc.GetComponents(True) if 'Шнековый вал' in c.Name2);d=c.GetModelDoc2;eq=d.GetEquationMgr
print('SCREW GLOBALS')
for i in range(eq.GetCount):
 expression=eq.Equation(i)
 if '@' not in expression:print(expression,flush=True)
for c in d.GetComponents(True):
 part=c.GetModelDoc2
 print(c.Name2,'box',part.GetPartBox(True),flush=True)
