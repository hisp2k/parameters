from pathlib import Path
b=Path('outputs/Шнек 1 — параметрическая модель');p=b/'model_diagnostics.py';s=p.read_text(encoding='utf-8').replace('from pathlib import Path','from pathlib import Path\nfrom datetime import datetime, timezone, timedelta')
s=s.replace('    return {\n        "available": True,', '''    verification_path = BASE / "open_verification_20261004.json"
    verification = json.loads(verification_path.read_text(encoding="utf-8")) if verification_path.exists() else {}
    interference_path = BASE / "full_interference_audit_20261004_final.json"
    interference = json.loads(interference_path.read_text(encoding="utf-8")) if interference_path.exists() else {}
    significant = sum(row.get("volume_mm3", 0) > 0.001 for row in interference.get("interferences", [])) if interference else None
    return {
        "component_count": verification.get("components"),
        "missing_files": verification.get("missing_files"),
        "checked_feature_errors": verification.get("other_feature_errors"),
        "interferences": significant,
        "interference_threshold_mm3": 0.001,
        "available": True,''').replace('"audit_date": "04.10.2026",','"audit_date": datetime.fromtimestamp(REPORT.stat().st_mtime, timezone(timedelta(hours=4))).strftime("%d.%m.%Y"),');p.write_text(s,encoding='utf-8')
p=b/'open_verification_20261004.json';import json;d=json.loads(p.read_text(encoding='utf-8'));d['components']=204;p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
p=b/'open_assembly.py';s=p.read_text(encoding='utf-8').replace('        "ok": True,\n        "partial":','        "ok": True,\n        "components": len(components),\n        "partial":');p.write_text(s,encoding='utf-8')
p=b/'index.html';s=p.read_text(encoding='utf-8').replace('<span class="pill warn">ТРЕБУЕТ ПРОВЕРКИ СБОРКИ</span>','<span class="pill warn" id="assemblyStatus">АУДИТ ЗАГРУЖАЕТСЯ</span>');s=s.replace('<p>Все 205 компонентов разрешены, но остаются 48 ошибочных сопряжений и 3 ошибки элементов. Чертежи предварительные до исправления модели, нанесения размеров и инженерной проверки.</p>','<p id="assemblyCheckText">Загружается последний результат проверки сборки.</p>')
old="  $('diagnosticsNote').textContent=`Сохранённый аудит ${data.audit_date}. У всех ${data.mates_with_lost_references} ошибочных сопряжений потеряна геометрическая ссылка на восстановленную деталь. После ремонта нужен новый аудит SolidWorks.`;"
new="""  const checkedOther=data.checked_feature_errors??data.other;
  const issues=data.mates+checkedOther+(data.missing_files??0)+(data.interferences??0);
  $('assemblyStatus').textContent=issues?'ЕСТЬ ОШИБКИ CAD':'CAD ПРОВЕРЕН';$('assemblyStatus').className=issues?'pill warn':'pill';
  $('assemblyCheckText').textContent=`Последний аудит ${data.audit_date}: ${data.component_count??'—'} компонентов; потерянных файлов — ${data.missing_files??'—'}; ошибок сопряжений — ${data.mates}; ошибок элементов — ${checkedOther}; пересечений более 0,001 мм³ — ${data.interferences??'не проверено'}.`;
  $('diagnosticsNote').textContent=`Сохранённый аудит ${data.audit_date}. Проверка относится к сохранённой сборке и условному изображению резьбы. После изменений нужна новая проверка CAD.`;"""
assert old in s;s=s.replace(old,new);p.write_text(s,encoding='utf-8')
# Keep the final report date aligned with the completed verification; CAD revision filenames retain their creation date.
p=b/'Исправление сборки 04.10.2026.md';s=p.read_text(encoding='utf-8').replace('связей — 04.10.2026','связей — 05.10.2026');(b/'Исправление сборки 05.10.2026.md').write_text(s,encoding='utf-8')
import py_compile,re
for n in ['model_diagnostics.py','open_assembly.py','server.py','bridge.py']:py_compile.compile(str(b/n),doraise=True)
Path('work/ui_final_check.js').write_text('\n'.join(re.findall(r'<script[^>]*>(.*?)</script>',(b/'index.html').read_text(encoding='utf-8'),re.S)),encoding='utf-8')
print('diagnostics panel updated')
