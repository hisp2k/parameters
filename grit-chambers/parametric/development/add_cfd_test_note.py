from pathlib import Path

out = Path(r"C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\Песколовка\GRIT_CHAMBER_CODEX_TASK.md")
src = Path(r"C:\Users\adm\.codex\attachments\b8cd7552-32be-41e2-9e27-1bca6330df68\Вставленный текст.txt")
text = out.read_text(encoding="utf-8")
text = text.replace(
    "`FLOW_SIMULATION_STATUS = NOT_RUN_CFD_PROJECT_NOT_CREATED`",
    "`FLOW_SIMULATION_STATUS = NOT_RUN_NO_VALID_CFD_PROJECT_IN_DELIVERABLE`",
)
needle = "Эффективность `ETA_0_20` остаётся `UNKNOWN`, целевой критерий 70% не подтверждён."
note = (
    "Тест API выполнен только на копии `work/CFD_API_TEST.SLDPRT`: "
    "`CreateTemplateProject` перенёс базовые двухфазные настройки из установленного учебного "
    "примера свободной поверхности; `AddProject2` создал проект "
    "`GRIT_PILOT_BASE_FREE_SURFACE`. Ссылки граничных условий учебного примера к геометрии "
    "песколовки неприменимы, поэтому они удалены; после задания расчётной области "
    "`Rebuild3` вернул `false`. Этот тестовый проект не является пригодным CFD-проектом "
    "песколовки и не включён в выдаваемые CAD-файлы.\n\n"
)
if note not in text:
    if needle not in text:
        raise SystemExit("note insertion point not found")
    text = text.replace(needle, note + needle)
out.write_text(text, encoding="utf-8")
src.write_text(text, encoding="utf-8")
print("updated", text.count("GRIT_PILOT_BASE_FREE_SURFACE"))
