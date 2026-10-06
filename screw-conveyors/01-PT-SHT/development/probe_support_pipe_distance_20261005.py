from pathlib import Path
import sys,json,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
from support_pipe_joint_helpers import design,verify
sw=w.GetActiveObject('SldWorks.Application');support=sw.GetOpenDocumentByName(str(bridge.FILES['support']))
print('Required brace dimensions',design(support)[2],flush=True)
print('Actual pipe gaps',verify(support),flush=True)
