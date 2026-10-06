from decimal import Decimal
import json
from pathlib import Path
import unittest

from screw_calculator import (
    CalculationRequest,
    DataStatus,
    FeedMode,
    MaterialClass,
    MaterialProfile,
    Property,
    QuantityRange,
    preflight,
    volume_flow_scenarios,
)
from screw_calculator.units import UnitError
from screw_calculator.io import request_from_dict
from reference.sludge_reference import calculate as independent_reference


def confirmed(minimum: str, nominal: str, maximum: str, unit: str) -> Property:
    return Property(
        DataStatus.CONFIRMED,
        QuantityRange(Decimal(minimum), Decimal(nominal), Decimal(maximum), unit),
        source="test measurement",
    )


def sludge_request() -> CalculationRequest:
    return CalculationRequest(
        request_id="T-001",
        product_profile_id="SCREW_SLUDGE_CONCEPT_V0",
        material=MaterialProfile(
            material_id="SLUDGE-TEST",
            version="0.1",
            material_class=MaterialClass.SLUDGE_DEWATERED,
            physical_model_id="PM-SLUDGE-DRAFT",
            properties={
                "wet_density": confirmed("900", "1000", "1100", "kg/m3"),
                "dry_solids_mass_fraction": confirmed("15", "18", "21", "%"),
                "max_inclusion_size": confirmed("0", "2", "5", "mm"),
                "temperature": confirmed("10", "20", "30", "C"),
            },
            evidence_refs={
                "adhesion_assessment": "test:adhesion:001",
                "drainage_assessment": "test:drainage:001",
                "fibrous_inclusions_assessment": "test:fibers:001",
            },
        ),
        feed_mode=FeedMode.CONTROLLED,
        target_flow=confirmed("900", "1000", "1100", "kg/h"),
        length=confirmed("4", "4", "4", "m"),
        angle=confirmed("0", "0", "0", "deg"),
    )


class InputStageTests(unittest.TestCase):
    def test_sludge_input_is_ready_only_for_engineering_model(self):
        result = preflight(sludge_request())
        self.assertEqual(result.status, "READY_FOR_ENGINEERING_MODEL")
        self.assertEqual(result.issues, ())

    def test_sludge_cannot_use_bulk_model(self):
        request = sludge_request()
        request = CalculationRequest(**{**request.__dict__, "product_profile_id": "SCREW_TUBE_H_BULK_V1"})
        result = preflight(request)
        self.assertEqual(result.status, "BLOCK")
        self.assertIn("MATERIAL_MODEL_MISMATCH", {x.code for x in result.issues})

    def test_missing_density_is_not_substituted(self):
        request = sludge_request()
        material = MaterialProfile(**{
            **request.material.__dict__,
            "properties": {k: v for k, v in request.material.properties.items() if k != "wet_density"},
        })
        request = CalculationRequest(**{**request.__dict__, "material": material})
        result = preflight(request)
        self.assertEqual(result.status, "UNKNOWN")
        self.assertIn("PROPERTY_REQUIRED", {x.code for x in result.issues})

    def test_mass_flow_extremes_pair_with_opposite_density_extremes(self):
        request = sludge_request()
        scenarios = volume_flow_scenarios(
            request.target_flow, request.material.properties["wet_density"]
        )
        self.assertEqual(scenarios.minimum_m3_h, Decimal("900") / Decimal("1100"))
        self.assertEqual(scenarios.nominal_m3_h, Decimal("1"))
        self.assertEqual(scenarios.maximum_m3_h, Decimal("1100") / Decimal("900"))

    def test_wrong_density_unit_is_blocked(self):
        request = sludge_request()
        props = dict(request.material.properties)
        props["wet_density"] = confirmed("1", "2", "3", "m")
        material = MaterialProfile(**{**request.material.__dict__, "properties": props})
        request = CalculationRequest(**{**request.__dict__, "material": material})
        self.assertEqual(preflight(request).status, "BLOCK")

    def test_fraction_outside_zero_one_is_blocked(self):
        request = sludge_request()
        props = dict(request.material.properties)
        props["dry_solids_mass_fraction"] = confirmed("15", "50", "105", "%")
        material = MaterialProfile(**{**request.material.__dict__, "properties": props})
        request = CalculationRequest(**{**request.__dict__, "material": material})
        self.assertEqual(preflight(request).status, "BLOCK")

    def test_invalid_range_rejected_at_input(self):
        with self.assertRaises(ValueError):
            QuantityRange(Decimal("3"), Decimal("2"), Decimal("4"), "kg/h")

    def test_dimension_error(self):
        with self.assertRaises(UnitError):
            QuantityRange(Decimal("1"), Decimal("1"), Decimal("1"), "mm").si("density")

    def test_published_sludge_intake_matches_independent_reference(self):
        """Cross-check SI conversion without sharing the reference solver's code."""
        result = independent_reference()
        target = confirmed("9000", "9000", "9000", "lb/h")
        density = confirmed("60", "60", "60", "lb/ft3")
        scenarios = volume_flow_scenarios(target, density)
        self.assertAlmostEqual(
            scenarios.nominal_m3_h,
            Decimal(result["volume_m3_h"]),
            delta=Decimal("0.000000001"),
        )

    def test_reported_sand_moisture_remains_unverified(self):
        raw = json.loads(Path("examples/sludge_input_template.json").read_text(encoding="utf-8"))
        request = request_from_dict(raw)
        sand = request.material.components[0]
        self.assertEqual(sand.reported_values["moisture"], "60%")
        self.assertEqual(sand.reported_values["moisture_basis"], "UNKNOWN")
        self.assertEqual(sand.properties["water_content_dry_basis"].status, DataStatus.NOT_MEASURED)
        result = preflight(request)
        self.assertEqual(result.status, "UNKNOWN")
        self.assertIn("MOISTURE_BASIS_REQUIRED", {x.code for x in result.issues})
        self.assertIn("MIXTURE_DENSITY_REQUIRED", {x.code for x in result.issues})


if __name__ == "__main__":
    unittest.main()
