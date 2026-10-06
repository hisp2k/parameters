exec(open('work/efd_save.py',encoding='utf-8').read().split("print('path'")[0])
db=typed(app.GetEngineeringDatabase(),'IEngineeringDatabase')
items=typed(db.GetEDBItems(3),'IEDBItemsCollection')
print('count',items.GetCount())
for name in ['Water','Вода']:
    try:
        raw=items.GetItemByName(name)
        print('lookup',name,bool(raw))
        if raw:
            item=typed(raw,'IEDBItem')
            print(item.GetName(),item.GetGUID())
    except Exception as exc:print('lookup error',name,repr(exc))
