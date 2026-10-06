"""Run the input gate against a JSON request. No design result is produced."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from screw_calculator import DataStatus, preflight, volume_flow_scenarios
from screw_calculator.io import request_from_dict


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Check screw conveyor calculation inputs")
    parser.add_argument("request_json", type=Path)
    args = parser.parse_args()

    request = request_from_dict(json.loads(args.request_json.read_text(encoding="utf-8")))
    result = preflight(request)
    response: dict[str, object] = {
        "request_id": request.request_id,
        "status": result.status,
        "design_status": "NOT_CALCULATED",
        "issues": [issue.__dict__ for issue in result.issues],
        "reported_unverified": [
            {"component_id": c.component_id, **dict(c.reported_values)}
            for c in request.material.components
            if c.reported_values
        ],
    }
    density_name = "wet_density" if request.material.material_class.value == "SLUDGE_DEWATERED" else "bulk_density"
    density = request.material.properties.get(density_name)
    sand_present = any(c.component_id == "SAND" for c in request.material.components)
    density_applies_to_mixture = not sand_present or bool(request.material.evidence_refs.get("mixture_density_measurement"))
    if density_applies_to_mixture and request.target_flow.status == DataStatus.CONFIRMED and density is not None and density.status == DataStatus.CONFIRMED:
        try:
            flows = volume_flow_scenarios(request.target_flow, density)
            response["required_volume_m3_h"] = {
                "minimum": str(flows.minimum_m3_h),
                "nominal": str(flows.nominal_m3_h),
                "maximum": str(flows.maximum_m3_h),
            }
        except ValueError:
            pass  # The preflight issues explain invalid or incomplete inputs.
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 1 if result.status == "BLOCK" else 0


if __name__ == "__main__":
    raise SystemExit(main())
