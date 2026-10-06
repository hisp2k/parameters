"""Persistent project change journal for successful CAD actions."""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent
JOURNAL = BASE / "journal.json"
PROJECT = json.loads((BASE / "project.json").read_text(encoding="utf-8"))
PARAMETER_NAMES = {
    "working_length": "Рабочая длина", "tube_diameter": "Диаметр трубы",
    "tube_wall": "Стенка трубы", "incline": "Угол наклона",
    "inlet_diameter": "Диаметр патрубка", "inlet_length": "Длина патрубка",
    "inlet_wall": "Стенка патрубка", "screw_diameter": "Диаметр винта",
    "flange_thickness": "Толщина фланца", "mounting_hole_diameter": "Отверстие М8",
    "opening_diameter": "Отверстие в корпусе",
    "discharger_length": "Положение сбрасывателя",
    "support_short_beam_length": "Полная длина балки 1 опоры",
    "support_long_beam_length": "Полная длина балки 2 опоры",
    "pitch": "Шаг винта", "blade_thickness": "Толщина лопасти",
    "shaft_diameter": "Диаметр вала", "shaft_wall": "Стенка вала",
    "turns": "Число витков", "tube": "Выбор трубы",
    "screw": "Выбор винта", "material": "Марка стали", "design_mode": "Режим угла наклона",
}


def _now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _read():
    if JOURNAL.exists():
        return json.loads(JOURNAL.read_text(encoding="utf-8"))
    return {"started_at": _now(), "entries": []}


def _write(data):
    temporary = JOURNAL.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, JOURNAL)


def _append(entry):
    data = _read()
    entry["number"] = max((x["number"] for x in data["entries"]), default=0) + 1
    entry["timestamp"] = _now()
    entry["project_id"] = PROJECT["id"]
    entry["project_name"] = PROJECT["name"]
    data["entries"].append(entry)
    _write(data)
    return entry


def record_apply(previous: dict, current: dict):
    changes = []
    for section in ("values", "selection"):
        fallback = {"tube": "custom", "screw": "custom", "material": "unspecified"} if section == "selection" else {}
        before, after = previous.get(section, fallback), current.get(section, {})
        for key in sorted(after):
            if before.get(key) != after[key]:
                changes.append({"key": key, "name": PARAMETER_NAMES.get(key, key),
                                "before": before.get(key), "after": after[key]})
    if previous.get("design_mode", "special") != current.get("design_mode", "special"):
        changes.append({"key": "design_mode", "name": PARAMETER_NAMES["design_mode"],
                        "before": previous.get("design_mode", "special"),
                        "after": current.get("design_mode", "special")})
    if not changes:
        return None
    return _append({"type": "model_change", "title": "Применение параметров к модели",
                    "change_count": len(changes), "changes": changes})


def record_failed_apply(previous: dict, requested: dict, result: dict):
    changes = [{"key": key, "name": "Запрошено, не сохранено: " + PARAMETER_NAMES.get(key, key),
                "before": previous["values"].get(key), "after": value}
               for key, value in requested.get("values", {}).items()
               if previous["values"].get(key) != value]
    return _append({"type": "model_apply_failed",
                    "title": "Перестроение отклонено; " + ("модель восстановлена и проверена"
                        if result.get("rollback_verified") else "изменения не применены"),
                    "change_count": 0, "request_count": len(changes), "changes": changes,
                    "errors": result.get("errors", []),
                    "rollback_verified": result.get("rollback_verified", False),
                    "snapshot": result.get("snapshot")})


def record_drawings(result: dict):
    return _append({"type": "drawings", "title": "Построение чертежей",
                    "change_count": 0, "batch": result["batch"],
                    "drawings": result["drawings"], "partial": result["partial"]})


def record_specification(decisions: list[dict], decision_id: str):
    existing = next((x for x in _read()["entries"] if x.get("decision_id") == decision_id), None)
    if existing:
        return existing
    return _append({"type": "specification_change", "title": "Уточнение задания и состава",
                    "decision_id": decision_id, "change_count": len(decisions), "changes": decisions})


def record_assembly_repair(names: list[str], repair_id: str):
    existing = next((x for x in _read()["entries"] if x.get("repair_id") == repair_id), None)
    if existing:
        return existing
    changes = [{"key": name, "name": f"Сопряжение {name}",
                "before": "ошибка 48", "after": "исправлено"} for name in names]
    return _append({"type": "assembly_repair", "title": "Исправление сопряжений SolidWorks",
                    "repair_id": repair_id, "change_count": len(changes), "changes": changes})


def record_questionnaire(previous: dict, current: dict):
    names = {
        "starts_per_hour": "Пусков в час",
        "run_minutes": "Длительность включения, мин",
        "loaded_start": "Пуск с заполненным шнеком",
        "mixture_density_kg_m3": "Измеренная плотность смеси, кг/м³",
    }
    changes = [
        {"key": key, "name": name, "before": previous.get(key), "after": current.get(key)}
        for key, name in names.items() if previous.get(key) != current.get(key)
    ]
    if not changes:
        return None
    return _append({"type": "questionnaire_change", "title": "Уточнение условий работы",
                    "change_count": len(changes), "changes": changes})


def view():
    data = _read()
    entries = data["entries"]
    changes = [x for x in entries if x["type"] == "model_change"]
    drawings = [x for x in entries if x["type"] == "drawings"]
    specifications = [x for x in entries if x["type"] == "specification_change"]
    questionnaire_changes = [x for x in entries if x["type"] == "questionnaire_change"]
    assembly_repairs = [x for x in entries if x["type"] == "assembly_repair"]
    return {"project": PROJECT, "started_at": data["started_at"],
            "summary": {"model_changes": len(changes),
                        "changed_fields": sum(x["change_count"] for x in changes),
                        "drawing_batches": len(drawings),
                        "drawing_files": sum(len(x["drawings"]) for x in drawings),
                        "specification_changes": len(specifications),
                        "questionnaire_changes": len(questionnaire_changes),
                        "assembly_repairs": sum(x["change_count"] for x in assembly_repairs)},
            "entries": list(reversed(entries))}
