"""Measure the real lower pin joint independently of the mate solver status."""
from __future__ import annotations
import math

def transformed(component, vector, point=False):
    matrix = list(component.Transform2.ArrayData)
    return [sum(vector[j] * matrix[j * 3 + i] for j in range(3))
            + (matrix[9 + i] if point else 0) for i in range(3)]

def cylindrical_face(component, diameter_mm):
    faces = [face for body in component.GetModelDoc2.GetBodies2(0, True)
             for face in body.GetFaces() if face.GetSurface.IsCylinder
             and abs(face.GetSurface.CylinderParams[6] * 2000 - diameter_mm) < 1e-5]
    if not faces:
        raise RuntimeError(f"Нет посадочной цилиндрической поверхности Ø{diameter_mm}: {component.Name2}")
    return max(faces, key=lambda face: face.GetArea)

def cylindrical_axis(component, diameter_mm):
    parameters = list(cylindrical_face(component, diameter_mm).GetSurface.CylinderParams)
    return transformed(component, parameters[:3], True), transformed(component, parameters[3:6])

def seating_face(component, x_m):
    choices = []
    for body in component.GetModelDoc2.GetBodies2(0, True):
        for face in body.GetFaces():
            surface = face.GetSurface
            if not surface.IsPlane:
                continue
            point = transformed(component, list(surface.PlaneParams)[3:6], True)
            normal = transformed(component, list(face.Normal))
            if abs(point[0] - x_m) < 1e-5 and abs(normal[0]) > .9999:
                choices.append((face.GetArea, face, point, normal))
    if not choices:
        raise RuntimeError(f"Не найден торец шарнира: {component.Name2}, X={x_m * 1000:g} мм")
    return max(choices, key=lambda item: item[0])[1:]

def verify(top, tolerance_mm=.001):
    components = list(top.GetComponents(False) or [])
    def component(text, instance):
        return next(c for c in components if text in c.Name2 and c.Name2.endswith(f'-{instance}'))
    bush = component(".25.00.05 'Втулка'", 2)
    point, axis = cylindrical_axis(bush, 18)
    axis_norm = math.sqrt(sum(v * v for v in axis))
    axis = [v / axis_norm for v in axis]
    rows = []
    for text, instance, diameter in [(".21.00.11 'Ухо'", 3, 10.8),
                                      (".21.00.11 'Ухо'", 4, 10.8),
                                      (".25.00.09 'Подкос 1'", 1, 18),
                                      (".25.00.09-01 'Подкос 1'", 2, 18)]:
        target = component(text, instance)
        other_point, other_axis = cylindrical_axis(target, diameter)
        delta = [other_point[i] - point[i] for i in range(3)]
        along = sum(delta[i] * axis[i] for i in range(3))
        distance = math.sqrt(sum((delta[i] - along * axis[i]) ** 2 for i in range(3))) * 1000
        dot = abs(sum(other_axis[i] * axis[i] for i in range(3)))
        angle = math.degrees(math.acos(min(1., dot / math.sqrt(sum(v*v for v in other_axis)))))
        rows.append({"component": target.Name2, "axis_offset_mm": distance,
                     "axis_angle_deg": angle, "ok": distance <= tolerance_mm and angle <= .001})
    seats = []
    for instance, x in [(3, -.03), (4, .03)]:
        ear = component(".21.00.11 'Ухо'", instance)
        _, bush_point, _ = seating_face(bush, x)
        _, ear_point, _ = seating_face(ear, x)
        gap = abs(bush_point[0] - ear_point[0]) * 1000
        seats.append({"ear": instance, "gap_mm": gap, "ok": gap <= tolerance_mm})
    support = next(c.GetModelDoc2 for c in top.GetComponents(True) if 'Опора шнековая' in c.Name2)
    mates = []
    for document, name, mate_type, targets in [
        (top, 'Втулка 2 — ухо 3 — соосность', 1, [(".25.00.05 'Втулка'", 2), (".21.00.11 'Ухо'", 3)]),
        (top, 'Втулка 2 — ухо 4 — торцевая посадка', 0, [(".25.00.05 'Втулка'", 2), (".21.00.11 'Ухо'", 4)]),
        (support, 'Подкос 1 — втулка 2 — соосность', 1, [(".25.00.05 'Втулка'", 2), (".25.00.09 'Подкос 1'", 1)])]:
        feature = document.FeatureByName(name)
        valid = bool(feature and not feature.IsSuppressed and feature.GetErrorCode == 0
                     and feature.GetSpecificFeature2.Type == mate_type)
        references = []
        if valid:
            mate = feature.GetSpecificFeature2
            for index in range(mate.GetMateEntityCount):
                entity = mate.MateEntity(index)
                referenced = entity.ReferenceComponent
                references.append({"component": referenced.Name2 if referenced else None,
                                   "present": entity.Reference is not None})
            valid = len(references) == 2 and all(r['present'] for r in references) and all(
                any(text in (r['component'] or '') and r['component'].endswith(f'-{instance}')
                    for r in references) for text, instance in targets)
        mates.append({"name": name, "ok": valid, "references": references})
    mirrored = support.FeatureByName('ЗеркальныйКомпонент1')
    if mirrored is None:
        feature = support.FirstFeature
        while feature:
            if feature.GetTypeName2 == 'MirrorCompFeat':
                mirrored = feature
                break
            feature = feature.GetNextFeature
    mirror_ok = bool(mirrored and not mirrored.IsSuppressed and mirrored.GetErrorCode == 0)
    result = {"ok": all(r['ok'] for r in rows + seats + mates) and mirror_ok,
              "bush": bush.Name2, "axes": rows, "seats": seats, "mates": mates,
              "mirrored_brace_ok": mirror_ok, "tolerance_mm": tolerance_mm}
    if not result['ok']:
        raise RuntimeError(f"Нарушена цепочка уши 3/4 — втулка 2 — подкосы: {result}")
    return result
