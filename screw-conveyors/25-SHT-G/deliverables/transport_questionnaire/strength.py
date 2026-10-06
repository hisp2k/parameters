"""Preliminary static FEA of the supplied keyed screw shaft in Simulation.

The study uses an idealized fixed end and applies axial force and torque at
the opposite end. It is a component check, not whole-conveyor certification.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from cad_bridge import apply_to_model, default_model_dir, prepare


SHAFT_GLOB = "*02.00.00.03*Вал*SLDPRT"
G = 9.80665


def _positive(value, label: str, *, allow_zero: bool = False) -> float:
    try:
        result = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        raise ValueError(f"{label}: требуется число") from None
    if not math.isfinite(result) or (result < 0 if allow_zero else result <= 0):
        raise ValueError(f"{label}: значение должно быть {'неотрицательным' if allow_zero else 'положительным'}")
    return result


def prepare_strength(raw: dict, model_dir: str | Path) -> dict:
    """Validate inputs and produce a readable, mutation-free load plan."""
    cad = prepare(raw, model_dir)
    if cad["blocked"]:
        raise ValueError("Текущая модель несовместима:\n" + "\n".join(cad["blocked"]))
    material = cad["inputs"]["material"]
    density = material["bulk_density_kg_m3"]
    if density is None:
        raise ValueError("Для расчётного блока укажите насыпную плотность вручную")
    controls = raw.get("strength") or {}
    torque = _positive(controls.get("torque_nm"), "Расчётный крутящий момент, Н·м")
    axial = _positive(controls.get("axial_force_n"), "Расчётная осевая сила, Н", allow_zero=True)
    yield_mpa = _positive(controls.get("yield_strength_mpa"), "Предел текучести, МПа")
    safety_required = _positive(controls.get("required_safety_factor"), "Требуемый коэффициент запаса")
    if safety_required < 1:
        raise ValueError("Требуемый коэффициент запаса должен быть не менее 1")
    mesh_raw = controls.get("mesh_size_mm")
    mesh_size = None if mesh_raw is None or str(mesh_raw).strip() == "" else _positive(mesh_raw, "Размер элемента сетки, мм")
    material_name = str(controls.get("simulation_material") or "").strip()
    if not material_name:
        raise ValueError("Выберите точное имя материала из библиотеки SolidWorks")

    root = Path(cad["model_dir"])
    shafts = [p for p in root.glob(SHAFT_GLOB) if not p.name.startswith("~$")]
    if len(shafts) != 1:
        raise FileNotFoundError("В копии модели не найден ровно один вал 25.SHT.G.02.00.00.03")
    general = cad["inputs"]["general"]
    density_confirmed = material.get("density_status") != "requires_wet_material_confirmation"
    mass = density * general["batch_volume_m3"] if density_confirmed else None
    return {
        "cad": cad, "shaft_part": str(shafts[0]),
        "controls": {
            "torque_nm": torque, "axial_force_n": axial,
            "simulation_material": material_name, "yield_strength_mpa": yield_mpa,
            "required_safety_factor": safety_required, "mesh_size_mm": mesh_size,
        },
        "material_context": {
            "bulk_density_kg_m3": density,
            "density_status": material.get("density_status"),
            "batch_mass_kg": mass,
            "batch_weight_n": mass * G if mass is not None else None,
            "mass_flow_kg_h": density * general["throughput_m3_h"] if density_confirmed else None,
            "note": ("Плотность влажной смеси не подтверждена; масса партии и расход не рассчитаны."
                     if not density_confirmed else
                     "Масса партии и массовый расход справочные; их нельзя напрямую считать нагрузкой на вал."),
        },
        "boundary_conditions": {
            "fixed_face": "плоский торец z=0 мм вала 25.SHT.G.02.00.00.03",
            "load_face": "плоский торец z=-363 мм",
            "loads": "осевая сила по нормали к торцу и крутящий момент вокруг оси вала",
            "limitation": "Идеализированное закрепление; шнек, второй вал, опоры, контакты и динамика не включены.",
        },
    }


def _select_shaft_faces(model):
    bodies = model.GetBodies2(0, False) or []
    if len(bodies) != 1:
        raise RuntimeError("Геометрия вала изменилась: ожидалось одно твёрдое тело")
    faces = bodies[0].GetFaces() or []
    fixed, load, cylinder = [], [], []
    for face in faces:
        surf = face.GetSurface
        box = face.GetBox
        if surf.IsPlane and abs(box[2]) < 1e-6 and abs(box[5]) < 1e-6 and face.GetArea > .004:
            fixed.append(face)
        if surf.IsPlane and abs(box[2] + .363) < 1e-6 and abs(box[5] + .363) < 1e-6 and face.GetArea > .002:
            load.append(face)
        if surf.IsCylinder and face.GetArea > .05:
            cylinder.append(face)
    if tuple(map(len, (fixed, load, cylinder))) != (1, 1, 1):
        raise RuntimeError("Не удалось однозначно найти расчётные поверхности вала; исследование отменено")
    return fixed[0], load[0], cylinder[0]


def _material_library(sw, material_name: str) -> tuple[Path, float | None]:
    lib = Path(sw.GetExecutablePath) / "lang/english/sldmaterials/solidworks materials.sldmat"
    if not lib.exists():
        raise FileNotFoundError(f"Библиотека материалов SolidWorks не найдена: {lib}")
    tree = ET.parse(lib)
    chosen = next((element for element in tree.iter("material") if element.get("name") == material_name), None)
    if chosen is None:
        raise ValueError(f"Материал «{material_name}» не найден в библиотеке SolidWorks")
    yield_node = chosen.find("./physicalproperties/SIGYLD")
    library_yield_mpa = (float(yield_node.get("value")) / 1e6) if yield_node is not None else None
    return lib, library_yield_mpa


def _simulate(plan: dict) -> dict:
    import pythoncom
    import win32com.client as win32

    pythoncom.CoInitialize()
    sw = win32.Dispatch("SldWorks.Application")
    lib, library_yield_mpa = _material_library(sw, plan["controls"]["simulation_material"])
    if library_yield_mpa is not None and plan["controls"]["yield_strength_mpa"] > library_yield_mpa * 1.005:
        raise ValueError(f"Введённый предел текучести выше значения библиотеки SolidWorks ({library_yield_mpa:g} МПа)")
    path = plan["shaft_part"]
    was_open = sw.GetOpenDocumentByName(path)
    errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    warnings = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    model = sw.OpenDoc6(path, 1, 1, "", errors, warnings)
    if not model:
        raise RuntimeError(f"SolidWorks не открыл приводной вал (код {errors.value})")
    title = model.GetTitle
    try:
        sw.ActivateDoc2(title, False, errors)
        fixed, load, cylinder = _select_shaft_faces(model)
        addin = sw.GetAddInObject("SldWorks.Simulation")
        if not addin:
            dll = Path(sw.GetExecutablePath) / "Simulation/cosworks.dll"
            code = sw.LoadAddIn(str(dll))
            if code not in (0, 2):
                raise RuntimeError(f"Simulation не загрузился (код {code})")
            addin = sw.GetAddInObject("SldWorks.Simulation")
        if not addin:
            raise RuntimeError("API SolidWorks Simulation недоступен")
        doc = addin.COSMOSWORKS.ActiveDoc
        if not doc:
            raise RuntimeError("Simulation не распознал активную деталь")
        manager = doc.StudyManager
        name = "AUTO_SHAFT_" + datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:4]
        study = manager.CreateNewStudy3(name, 0, 0, errors)
        if not study or errors.value != 0:
            raise RuntimeError(f"Simulation не создал статическое исследование (код {errors.value})")
        solid = study.SolidManager
        component = solid.GetComponentAt(0, errors)
        body = component.GetSolidBodyAt(0, errors) if component else None
        if not body or not body.SetLibraryMaterial(str(lib), plan["controls"]["simulation_material"]):
            raise RuntimeError("Simulation не назначил материал валу")
        lr = study.LoadsAndRestraintsManager
        null = win32.VARIANT(pythoncom.VT_DISPATCH, None)
        fixed_array = win32.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_VARIANT, [fixed])
        load_array = win32.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_VARIANT, [load])
        restraint = lr.AddRestraint(0, fixed_array, null, errors)
        if not restraint or errors.value != 0:
            raise RuntimeError(f"Simulation не создал закрепление (код {errors.value})")
        if plan["controls"]["axial_force_n"] > 0:
            force = lr.AddForce2(1, 0, load_array, null, errors)
            if not force or errors.value != 0:
                raise RuntimeError(f"Simulation не создал осевую силу (код {errors.value})")
            force.ForceBeginEdit()
            force.Unit = 0
            force.NormalForceOrTorqueValue = plan["controls"]["axial_force_n"]
            if force.ForceEndEdit != 0:
                raise RuntimeError("Simulation не сохранил осевую силу")
        torque = lr.AddForce2(2, 0, load_array, cylinder, errors)
        if not torque or errors.value != 0:
            raise RuntimeError(f"Simulation не создал крутящий момент (код {errors.value})")
        torque.ForceBeginEdit()
        torque.Unit = 0
        torque.NormalForceOrTorqueValue = plan["controls"]["torque_nm"]
        if torque.ForceEndEdit != 0:
            raise RuntimeError("Simulation не сохранил крутящий момент")

        mesh = study.Mesh
        mesh.MesherType = 0
        mesh.Quality = 1
        default_size = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_R8, 0.0)
        default_tol = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_R8, 0.0)
        mesh.GetDefaultElementSizeAndTolerance(0, default_size, default_tol)
        size = plan["controls"]["mesh_size_mm"] or default_size.value
        tolerance = default_tol.value if plan["controls"]["mesh_size_mm"] is None else size * .05
        mesh_code = study.CreateMesh(0, size, tolerance)
        if mesh_code != 0:
            raise RuntimeError(f"Simulation не построил сетку (код {mesh_code})")
        run_code = study.RunAnalysis
        if run_code != 0:
            raise RuntimeError(f"Решатель Simulation завершился с кодом {run_code}")
        results = study.Results
        if not results:
            raise RuntimeError("Simulation не вернул результаты")
        stress = results.GetMinMaxStress(9, 0, 0, null, 0, errors)
        if errors.value != 0 or not stress:
            raise RuntimeError(f"Не удалось прочитать напряжения (код {errors.value})")
        displacement = results.GetMinMaxDisplacement(3, 0, null, 0, errors)
        if errors.value != 0 or not displacement:
            raise RuntimeError(f"Не удалось прочитать перемещения (код {errors.value})")
        stress_mpa = float(stress[3]) / 1e6
        disp_mm = float(displacement[3])
        if not math.isfinite(stress_mpa) or stress_mpa <= 0 or not math.isfinite(disp_mm):
            raise RuntimeError("Получены некорректные результаты Simulation")
        safety = plan["controls"]["yield_strength_mpa"] / stress_mpa
        passed = safety >= plan["controls"]["required_safety_factor"]
        props = model.Extension.CustomPropertyManager("")
        for key, value in {
            "FEA_STATUS": "PRELIMINARY_PASS" if passed else "PRELIMINARY_FAIL",
            "FEA_STUDY": name,
            "FEA_TORQUE_NM": f"{plan['controls']['torque_nm']:.6g}",
            "FEA_AXIAL_FORCE_N": f"{plan['controls']['axial_force_n']:.6g}",
            "FEA_MAX_VON_MISES_MPA": f"{stress_mpa:.6g}",
            "FEA_MAX_DISPLACEMENT_MM": f"{disp_mm:.6g}",
            "FEA_YIELD_FACTOR": f"{safety:.6g}",
        }.items():
            props.Add3(key, 30, value, 1)
        if not model.Save3(1, errors, warnings):
            raise RuntimeError(f"SolidWorks не сохранил исследование в детали (код {errors.value})")
        return {
            "study_name": name, "material_library": str(lib),
            "library_yield_strength_mpa": library_yield_mpa,
            "mesh_element_size_mm": size, "max_von_mises_mpa": stress_mpa,
            "max_displacement_mm": disp_mm, "yield_safety_factor": safety,
            "required_safety_factor": plan["controls"]["required_safety_factor"],
            "preliminary_check_passed": passed,
        }
    finally:
        if not was_open:
            sw.CloseDoc(title)
        pythoncom.CoUninitialize()


def run_strength(plan: dict) -> dict:
    result = {
        "schema_version": 1,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "preliminary_shaft_fea",
        "assembly": plan["cad"]["assembly"], "shaft_part": plan["shaft_part"],
        "inputs": plan["cad"]["inputs"], "loads": plan["controls"],
        "material_context": plan["material_context"],
        "boundary_conditions": plan["boundary_conditions"],
        "simulation": _simulate(plan),
        "not_checked": ["шнек с осями в сборе", "желоб и опоры", "сварные швы", "подшипники",
                        "контакты компонентов", "усталость", "устойчивость", "сходимость сетки"],
    }
    # The questionnaire's screw pitch is then transferred to the paired CAD copy.
    result["cad_link"] = apply_to_model(plan["cad"])
    report = Path(plan["cad"]["model_dir"]) / "РАСЧЁТ_ПРОЧНОСТИ_ВАЛА.json"
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["report_path"] = str(report)
    return result


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Предварительный прочностной расчёт приводного вала в SolidWorks Simulation")
    parser.add_argument("input", type=Path, help="JSON опросного листа с разделом strength")
    parser.add_argument("--model", type=Path, default=default_model_dir())
    parser.add_argument("--dry-run", action="store_true", help="Проверка исходных данных без изменения CAD")
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        plan = prepare_strength(payload.get("inputs", payload), args.model)
        result = plan if args.dry_run else run_strength(plan)
    except Exception as exc:
        parser.exit(1, f"Ошибка: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
