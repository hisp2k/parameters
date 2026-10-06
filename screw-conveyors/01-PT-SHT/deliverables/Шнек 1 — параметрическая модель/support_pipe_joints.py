"""Check the support pipe contacts using native SolidWorks geometry."""
import pythoncom
import win32com.client as win32

def distance(document, first, second):
    points = [win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_VARIANT, None) for _ in range(2)]
    value = document.ClosestDistance(first, second, *points)
    if isinstance(value, tuple):
        value = value[0]
    if value < 0:
        raise RuntimeError(f"Не удалось измерить стык {first.Name2} — {second.Name2}")
    return float(value) * 1000

def verify(support, tolerance_mm=.001):
    components = list(support.GetComponents(True))
    def find(text):
        return next(c for c in components if text in c.Name2)
    post1, post2 = find(".25.00.07 '"), find(".25.00.07-01 '")
    brace1, brace2 = find(".25.00.09 '"), find(".25.00.09-01 '")
    pairs = [(brace1, post1), (brace2, post2)] + [
        (c, p) for c in components if 'Балка' in c.Name2 for p in (post1, post2)]
    rows = []
    for first, second in pairs:
        gap = distance(support, first, second)
        rows.append({'first': first.Name2, 'second': second.Name2,
                     'gap_mm': gap, 'ok': gap <= tolerance_mm})
    name = 'Подкос 1 — стойка 1 — стык труб'
    feature = support.FeatureByName(name)
    valid = bool(feature and not feature.IsSuppressed and feature.GetErrorCode == 0
                 and feature.GetSpecificFeature2.Type == 0)
    references = []
    if valid:
        mate = feature.GetSpecificFeature2
        for index in range(mate.GetMateEntityCount):
            entity = mate.MateEntity(index)
            component = entity.ReferenceComponent
            references.append({'component': component.Name2 if component else None,
                               'present': entity.Reference is not None})
        valid = len(references) == 2 and all(r['present'] for r in references) and all(
            any(r['component'] == c.Name2 for r in references) for c in (brace1, post1))
    result = {'ok': len(rows) == 6 and all(r['ok'] for r in rows) and valid,
              'connections': rows, 'mate': {'name': name, 'ok': valid, 'references': references},
              'tolerance_mm': tolerance_mm}
    if not result['ok']:
        raise RuntimeError(f"Нарушены стыки труб опоры: {result}")
    return result
