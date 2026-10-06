"""Summarize the latest saved SolidWorks mate audit for the local panel."""

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta


BASE = Path(__file__).resolve().parent
REPORT = BASE / "mate_diagnostics_20261004.json"


def summary():
    if not REPORT.exists():
        return {"available": False, "message": "Сохранённый аудит сопряжений не найден."}

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    groups = []
    total_mates = 0
    total_other = 0
    lost_references = 0
    for assembly in report:
        errors = []
        for item in assembly.get("errors", []):
            is_mate = item.get("type", "").startswith("Mate")
            entities = item.get("entities", [])
            affected = [entity.get("component", "").split("/")[-1]
                        for entity in entities if not entity.get("reference_present", True)]
            total_mates += is_mate
            total_other += not is_mate
            lost_references += bool(is_mate and affected)
            errors.append({
                "name": item.get("name", "Без имени"),
                "kind": "сопряжение" if is_mate else "элемент",
                "lost_reference": bool(affected),
                "affected_components": affected,
            })
        groups.append({
            "assembly": Path(assembly.get("assembly", "")).name,
            "mates": sum(error["kind"] == "сопряжение" for error in errors),
            "other": sum(error["kind"] == "элемент" for error in errors),
            "errors": errors,
        })
    verification_path = BASE / "open_verification_20261004.json"
    verification = json.loads(verification_path.read_text(encoding="utf-8")) if verification_path.exists() else {}
    interference_path = BASE / "full_interference_audit_20261004_final.json"
    interference = json.loads(interference_path.read_text(encoding="utf-8")) if interference_path.exists() else {}
    significant = sum(row.get("volume_mm3", 0) > 0.001 for row in interference.get("interferences", [])) if interference else None
    state = json.loads((BASE / "state.json").read_text(encoding="utf-8"))
    verification_current = state.get("cad_verification", {})
    project = json.loads((BASE / "project.json").read_text(encoding="utf-8"))
    actual_angle = verification_current.get("measured_geometry", {}).get("incline")
    target_angle = project.get("target_incline_deg")
    mismatch = target_angle is not None and (actual_angle is None or abs(actual_angle - target_angle) > 0.001)
    parameter_checks = []
    correspondence_path = BASE / "parameter_correspondence_20261005.json"
    correspondence = None
    if correspondence_path.exists():
        audit = json.loads(correspondence_path.read_text(encoding="utf-8"))
        correspondence = {
            "checked_at": audit["timestamp"],
            "parameters": len(audit["parameters"]),
            "matched_parameters": sum(row["match"] for row in audit["parameters"]),
            "bindings": len(audit["bindings"]),
            "matched_bindings": sum(row["match"] for row in audit["bindings"]),
            "port_axial_length_mm": audit["physical"]["port"]["axis_y_length_mm"],
            "port_extrusion_length_mm": audit["requested_values"]["inlet_length"],
            "mounting_nominal_mm": audit["requested_values"]["mounting_hole_diameter"],
            "mounting_actual_mm": next(row["native"] for row in audit["parameters"]
                                       if row["parameter"] == "mounting_hole_diameter"),
            "opening_active": not audit["opening_cut"]["suppressed"],
            "opening_mm": audit["requested_values"]["opening_diameter"],
        }
    for filename in ("geometry_roundtrip_20261005.json", "geometry_after_fixes_20261005.json",
                     "geometry_native_ear_20261005.json", "geometry_rebuild_latest.json"):
        path = BASE / filename
        if path.exists():
            for row in json.loads(path.read_text(encoding="utf-8")):
                if "restored_audit" not in row and "restored_geometry" not in row:
                    continue
                parameter_checks = [r for r in parameter_checks if r["parameter"] != row["parameter"]]
                parameter_checks.append({"parameter": row["parameter"], "before": row["before"],
                    "tested": row["tested"], "ok": bool(row["applied"]), "errors": row.get("errors", []),
                    "simultaneous": row.get("simultaneous", False)})
    return {
        "checked_at": verification_current.get("timestamp"),
        "actual_incline_deg": actual_angle, "target_incline_deg": target_angle,
        "design_angle_mismatch": mismatch, "parameter_checks": parameter_checks,
        "parameter_correspondence": correspondence,
        "verification_current": verification_current,
        "pin_joints": verification_current.get("pin_joints"),
        "support_pipe_joints": verification_current.get("support_pipe_joints"),
        "component_count": verification_current.get("components", verification.get("components")),
        "missing_files": verification.get("missing_files"),
        "checked_feature_errors": verification_current.get("feature_errors", verification.get("other_feature_errors")),
        "interferences": verification_current.get("positive_interferences", significant),
        "interference_threshold_mm3": 0.001,
        "available": True,
        "audit_date": datetime.fromtimestamp(REPORT.stat().st_mtime, timezone(timedelta(hours=4))).strftime("%d.%m.%Y"),
        "mates": total_mates,
        "other": total_other,
        "mates_with_lost_references": lost_references,
        "assemblies": groups,
        "is_live": False,
    }
