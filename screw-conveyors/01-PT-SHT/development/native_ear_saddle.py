"""Create an editable cylindrical saddle, without cached cavity geometry."""
import pythoncom
import win32com.client as w


def create_saddle(sw, part, diameter_mm=141):
    part.FeatureManager.EditRollback(1, '')
    old = part.FeatureByName('Подрезка уха — рабочий корпус')
    assert old and old.GetTypeName2 == 'Cavity'
    part.ClearSelection2(True)
    assert old.Select2(False, 0)
    assert part.Extension.DeleteSelection2(0)
    assert part.FeatureByName('Справа').Select2(False, 0)
    manager = part.SketchManager
    manager.InsertSketch(True)
    sketch = manager.ActiveSketch
    feature = None
    candidate = part.FirstFeature
    while candidate:
        if candidate.GetTypeName2 == 'ProfileFeature':
            feature = candidate
        candidate = candidate.GetNextFeature
    assert feature
    feature.Name = 'Седло корпуса — профиль'
    transform = list(sketch.ModelToSketchTransform.ArrayData)
    center = (0., .086, -.03)
    point = [sum(center[j] * transform[j*3+i] for j in range(3)) + transform[9+i]
             for i in range(3)]
    assert abs(point[2]) < 1e-8, point
    manager.AddToDB = True
    try:
        circle = manager.CreateCircleByRadius(point[0], point[1], 0., diameter_mm/2000)
    finally:
        manager.AddToDB = False
    assert circle
    part.ClearSelection2(True)
    assert circle.GetCenterPoint2.Select4(False, part.SelectionManager.CreateSelectData)
    part.SketchAddConstraints('sgFIXED')
    part.ClearSelection2(True)
    assert circle.Select4(False, part.SelectionManager.CreateSelectData)
    # swInputDimValOnCreate = 10, from the installed swconst.tlb.
    # Preserve the setting; a scripted dimension must not open a modal dialog.
    input_dimension = sw.GetUserPreferenceToggle(10)
    try:
        sw.SetUserPreferenceToggle(10, False)
        assert not sw.GetUserPreferenceToggle(10)
        dimension = part.AddDiameterDimension2(point[0] + .08, point[1], 0.)
    finally:
        sw.SetUserPreferenceToggle(10, input_dimension)
    assert dimension
    dim = dimension.GetDimension2(0)
    dim.SystemValue = diameter_mm/1000
    print('saddle dimension', dim.FullName, 'center', point, flush=True)
    part.ClearSelection2(True)
    manager.InsertSketch(True)
    assert feature.Select2(False, 0)
    cut = part.FeatureManager.FeatureCut4(
        False, False, False, 1, 1, .1, .1,
        False, False, False, False, 0., 0.,
        False, False, False, False, False, False,
        True, False, False, False, 0, 0., False, True)
    assert cut and not cut.GetErrorCode
    cut.Name = 'Седло корпуса — параметрическая подрезка'
    assert part.ForceRebuild3(False)
    return dim.FullName, circle


def saddle_surfaces(part):
    return [list(face.GetSurface.CylinderParams)
            for body in part.GetBodies2(0, True)
            for face in body.GetFaces()
            if face.GetSurface.IsCylinder and face.GetSurface.CylinderParams[6] > .05]
