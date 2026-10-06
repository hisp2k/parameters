"""Change the screw flight pitch in the supplied SolidWorks copy.

Usage: python set_pitch.py 220
Requires SolidWorks and pywin32 on Windows. The input is in millimetres.
"""
import glob
import math
import os
import sys

import pythoncom
import win32com.client as win32


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python set_pitch.py <pitch_mm>")
    pitch = float(sys.argv[1])
    if not math.isfinite(pitch) or pitch <= 0:
        raise SystemExit("Pitch must be a positive finite number in millimetres")
    root = os.path.dirname(os.path.abspath(__file__))
    part = glob.glob(os.path.join(root, "*02.00.00.01*Шнек*SLDPRT"))
    if len(part) != 1:
        raise SystemExit("The source screw part was not found")

    sw = win32.Dispatch("SldWorks.Application")
    errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    warnings = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    model = sw.OpenDoc6(part[0], 1, 1, "", errors, warnings)
    if not model:
        raise RuntimeError(f"SolidWorks could not open the screw part: {errors.value}")
    sw.ActivateDoc2(model.GetTitle, False, errors)
    equations = model.GetEquationMgr
    index = next((i for i in range(equations.GetCount)
                  if equations.Equation(i).lstrip().startswith('"SCREW_PITCH"')), None)
    if index is None:
        raise RuntimeError("SCREW_PITCH equation is missing")
    equations.Equation(index, f'"SCREW_PITCH" = {pitch:.10g}')
    if not model.EditRebuild3:
        raise RuntimeError("The screw part did not rebuild; change was not saved")

    actual = None
    feature = model.FirstFeature
    while feature:
        if feature.Name == "HELIX_MASTER":
            display = feature.GetFirstDisplayDimension
            while display:
                dimension = display.GetDimension2(0)
                if dimension.FullName.startswith("D4@HELIX_MASTER@"):
                    actual = dimension.SystemValue * 1000
                display = feature.GetNextDisplayDimension(display)
        feature = feature.GetNextFeature
    if actual is None or abs(actual - pitch) > 1e-6:
        raise RuntimeError(f"Pitch verification failed: {actual} mm")

    if not model.Save3(1, errors, warnings):
        raise RuntimeError(f"SolidWorks could not save the part: {errors.value}")
    print(f"Saved screw pitch: {actual:g} mm")
    sw.CloseDoc(model.GetTitle)


if __name__ == "__main__":
    main()
