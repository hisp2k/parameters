exec(open(r'work\efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
s=p.GetLastRebuildError()
open(r'work\last_rebuild_error.txt','w',encoding='utf-8').write(s)
print(repr(s))
