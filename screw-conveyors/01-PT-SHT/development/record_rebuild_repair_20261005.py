from pathlib import Path
import sys,json
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import journal
entries=journal._read()['entries']
if not any(e.get('repair_id')=='rebuild-dependencies-braces-20261005' for e in entries):
 journal._append({'type':'model_change','title':'Зависимости трубы и непрерывные подкосы для 55°','repair_id':'rebuild-dependencies-braces-20261005','change_count':4,'changes':[
 {'key':'ear_saddle','name':'Уши крепления корпуса','before':'Высота постоянная; седло Ø133 не пересекало тело','after':'Высота и седло связаны с диаметром трубы'},
 {'key':'upper_port','name':'Верхний патрубок и его вырез','before':'Профиль фиксирован; при изменении угла вырез уходил за корпус','after':'Положение оси, базовая плоскость и профиль зависят от длины и угла'},
 {'key':'left_brace','name':'Подкос опоры','before':'При 55° пересекал трубу и винт','after':'Непрерывный обход корпуса; места крепления сохранены; прочность требует расчёта'},
 {'key':'right_brace','name':'Зеркальный подкос','before':'Повторял пересечение','after':'Обновлён через исходный подкос; одно тело; ошибки и пересечения отсутствуют'}]})
if not any(e.get('interface_id')=='persistent-apply-result-20261005' for e in entries):
 journal._append({'type':'interface_change','title':'Результат перестроения и причины блокировки','interface_id':'persistent-apply-result-20261005','change_count':3,'changes':[
 {'key':'apply_status','name':'Результат применения','before':'Кратковременное сообщение','after':'Постоянная панель; запрос и фактически сохранённые значения; результат сохраняется после обновления страницы'},
 {'key':'disabled_reason','name':'Недоступная кнопка применения','before':'Причина не показана рядом с кнопкой','after':'Показаны несовместимые размеры, пустые поля и ограничения угла'},
 {'key':'rollback_audit','name':'Откат и журнал','before':'Нативные ошибки без структурированного результата','after':'Проверка восстановленной геометрии; отклонённая попытка не учитывается как применённое изменение'}]})
print('Native and interface changes recorded')
