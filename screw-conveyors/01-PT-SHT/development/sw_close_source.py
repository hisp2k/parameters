import win32com.client as win32

sw = win32.GetActiveObject('SldWorks.Application')
docs = sw.GetDocuments or []
titles = [d.GetTitle for d in docs if '\\Desktop\\РАЗРАБОТКА\\01.PT.SHT.01.20.00.00' in d.GetPathName]
for title in reversed(titles):
    try:
        sw.CloseDoc(title)
    except Exception:
        pass
print('requested_close', len(titles))
