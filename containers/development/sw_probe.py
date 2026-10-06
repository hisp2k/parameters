import win32com.client as win32
sw=win32.Dispatch('SldWorks.Application')
sw.Visible=True
print('revision', sw.RevisionNumber)
tpl=r'C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2026\templates\gost-part.prtdot'
doc=sw.NewDocument(tpl,0,0,0)
print('doc',doc.GetTitle)
f=doc.FirstFeature
while f:
    print(f.Name.encode('unicode_escape').decode(),f.GetTypeName2)
    f=f.GetNextFeature
