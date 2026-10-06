"""Adapter for the actual worker envelope and guarded AI_* part variants.

Only connector-managed linear part dimensions are supported for writes. A verified
parameter update is distinct from CAD acceptance: disk reload, interference and
clearance checks are not provided by the ordinary connector variant command.
"""
from __future__ import annotations

import math
import ntpath
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from calculator.cad_adapter.bridge_transport import BridgeTransport, BridgeError

@dataclass
class ParameterMapEntry:
    app_parameter: str
    solidworks_id: str
    unit: str
    valid_range: tuple[float, float] | None = None
    dependent_components: list[str] = field(default_factory=list)
    control: str = "не задан"
    write_tool: str = "sw_set_parameter"

@dataclass
class RebuildOutcome:
    ok: bool
    errors: list[str] = field(default_factory=list)
    mate_issues: list[str] = field(default_factory=list)
    interference_issues: list[str] = field(default_factory=list)
    clearance_issues: list[str] = field(default_factory=list)
    mass_kg: float | None = None
    center_of_mass_mm: tuple[float, float, float] | None = None
    lost_references: list[str] = field(default_factory=list)
    workspace_path: str | None = None
    raw_steps: dict[str, Any] = field(default_factory=dict)
    parameter_update_verified: bool = False
    unknown_checks: list[str] = field(default_factory=list)

class CadAdapter(ABC):
    @abstractmethod
    def can_read(self) -> bool: ...
    @abstractmethod
    def can_write(self) -> bool: ...
    @abstractmethod
    def read_parameters(self, parameter_map: list[ParameterMapEntry]) -> dict: ...
    @abstractmethod
    def rebuild_project_copy(self, parameter_map: list[ParameterMapEntry], values: dict,
                             *, source_path: str) -> RebuildOutcome: ...


def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Expected a finite numeric dimension")
    return float(value)


def _same_path(a: str, b: str) -> bool:
    return isinstance(a, str) and isinstance(b, str) and ntpath.normcase(ntpath.normpath(a)) == ntpath.normcase(ntpath.normpath(b))


class LocalBridgeCadAdapter(CadAdapter):
    def __init__(self, transport: BridgeTransport):
        self._transport = transport

    def _call(self, tool: str, args: dict, steps: dict | None = None) -> dict:
        response = self._transport.call(tool, args)
        if steps is not None:
            steps[tool] = response.raw
        if not response.ok or response.tool != tool:
            raise BridgeError(f"{tool}: unsuccessful or mismatched response: {response.error}")
        worker = response.result
        if not isinstance(worker, dict) or worker.get("ok") is not True or not isinstance(worker.get("data"), dict):
            raise BridgeError(f"{tool}: invalid worker envelope")
        result = worker["data"]
        if tool in {"sw_parameters", "sw_document"}:
            if result.get("partial") is not False or result.get("issues") != [] or not isinstance(result.get("data"), dict):
                raise BridgeError(f"{tool}: incomplete read")
            return result["data"]
        return result

    def can_read(self) -> bool:
        try:
            self._call("sw_status", {})
            return True
        except BridgeError:
            return False

    def can_write(self) -> bool:
        try:
            status = self._call("sw_status", {})
            doc = self._call("sw_document", {})
            return ("sw_create_parameter_variant" in status.get("write_tools_available", [])
                    and doc.get("document_type") == "PART"
                    and doc.get("connector_write_allowed") is True
                    and doc.get("has_unsaved_changes") is False)
        except BridgeError:
            return False

    def _inventory(self, steps: dict | None = None) -> dict:
        data = self._call("sw_parameters", {}, steps)
        rows = data.get("items")
        if (data.get("partial") is not False or data.get("issues") != []
                or not isinstance(rows, list) or type(data.get("total")) is not int
                or data["total"] != len(rows)):
            raise BridgeError("Incomplete parameter inventory")
        result = {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("full_name"), str):
                raise BridgeError("Invalid parameter row")
            key = row["full_name"].casefold()
            if key in result:
                raise BridgeError("Ambiguous parameter identity")
            result[key] = row
        return result

    def read_parameters(self, parameter_map: list[ParameterMapEntry]) -> dict:
        inventory = self._inventory()
        result = {}
        for entry in parameter_map:
            if entry.solidworks_id.startswith("уточнить"):
                continue
            row = inventory.get(entry.solidworks_id.casefold())
            if not row or row.get("dimension_kind") != "LINEAR" or entry.unit not in {"мм", "mm"}:
                raise BridgeError(f"Unknown or unsupported parameter: {entry.app_parameter}")
            result[entry.app_parameter] = _number(row.get("value_mm"))
        return result

    def rebuild_project_copy(self, parameter_map: list[ParameterMapEntry], values: dict,
                             *, source_path: str) -> RebuildOutcome:
        # Validate the complete request before any CAD call; never apply a partial map.
        entries = {e.app_parameter: e for e in parameter_map}
        if len(entries) != len(parameter_map) or len({e.solidworks_id.casefold() for e in parameter_map}) != len(parameter_map):
            raise ValueError("Duplicate parameter mapping")
        if not values or set(values) - entries.keys():
            raise ValueError("Empty or unmapped parameter request")
        if not isinstance(source_path, str) or not ntpath.isabs(source_path) or not source_path.lower().endswith(".sldprt"):
            raise ValueError("An explicit absolute source SLDPRT path is required")
        for name, value in values.items():
            e = entries[name]
            value = _number(value)
            if (e.write_tool != "sw_set_parameter" or e.unit not in {"мм", "mm"}
                    or not e.solidworks_id.startswith("AI_") or "@" not in e.solidworks_id):
                raise ValueError(f"Unsupported mapping for {name}: only managed AI_* linear dimensions")
            if not 0.01 <= value <= 2000 or (e.valid_range and not e.valid_range[0] <= value <= e.valid_range[1]):
                raise ValueError(f"Dimension out of range: {name}")
        steps = {}
        outcome = RebuildOutcome(ok=False, raw_steps=steps)
        try:
            doc = self._call("sw_document", {}, steps)
            if (not _same_path(doc.get("path"), source_path) or doc.get("document_type") != "PART"
                    or doc.get("has_unsaved_changes") is not False or doc.get("connector_write_allowed") is not True):
                raise BridgeError("Explicit source must be the active clean writable part")
            inventory = self._inventory(steps)
            changes = []
            for name, value in values.items():
                entry = entries[name]
                row = inventory.get(entry.solidworks_id.casefold())
                if not row or row.get("editable_by_connector") is not True or row.get("dimension_kind") != "LINEAR" or not isinstance(row.get("name"), str):
                    raise BridgeError(f"Dimension is not editable: {name}")
                current = _number(row.get("value_mm"))
                if current == value:
                    continue
                changes.append({"full_name": entry.solidworks_id,
                                "expected_current_mm": current, "new_value_mm": value})
            if not changes:
                outcome.unknown_checks = ["No changes requested; existing CAD acceptance was not checked"]
                return outcome
            # One guarded CAD command owns copy/remapping/rebuild/save, avoiding active-document races.
            result = self._call("sw_create_parameter_variant", {"source_path": source_path, "changes": changes}, steps)
            path = result.get("variant_path")
            outcome.workspace_path = path if isinstance(path, str) else None
            verification = result.get("verification", {})
            save = result.get("save", {})
            if (not isinstance(path, str) or not ntpath.isabs(path) or _same_path(path, source_path)
                    or not _same_path(result.get("source_path"), source_path)
                    or result.get("source_unchanged") is not True
                    or not result.get("source_sha256_before")
                    or result.get("source_sha256_before") != result.get("source_sha256_after")
                    or not isinstance(verification, dict) or verification.get("status") != "PASS"
                    or verification.get("rebuilt") is not True or verification.get("all_requested_values_confirmed") is not True
                    or not isinstance(save, dict) or save.get("api_success") is not True
                    or save.get("errors") != 0 or save.get("warnings") != 0
                    or not _same_path(save.get("file_path"), path)):
                raise BridgeError("UNKNOWN: variant result did not prove source preservation, rebuild and save")
            actual = result.get("changes")
            if not isinstance(actual, list) or len(actual) != len(changes):
                raise BridgeError("Incomplete dimension readback")
            for requested, measured in zip(changes, actual):
                if not isinstance(measured, dict) or measured.get("parameter_name") != inventory[requested["full_name"].casefold()]["name"]:
                    raise BridgeError("Dimension readback identity mismatch")
                if abs(_number(measured.get("actual_mm")) - requested["new_value_mm"]) > 0.001:
                    raise BridgeError("Dimension readback mismatch")
            outcome.parameter_update_verified = True
            outcome.unknown_checks = ["Disk close/reopen verification", "Interference and clearance verification", "Engineering acceptance"]
        except (BridgeError, ValueError) as exc:
            outcome.errors.append(str(exc))
        return outcome


# Карта параметров для будущего заполнения (пусто по существу —
# идентификаторы SolidWorks не подтверждены для BOM-версии сборки, раздел
# 12 — "не выдумывай имена размеров и переменных модели"):
SCREW_CONVEYOR_PARAMETER_MAP: list[ParameterMapEntry] = [
    ParameterMapEntry(
        app_parameter="diameter_mm",
        solidworks_id="уточнить (нет подтверждённой BOM-версии сборки)",
        unit="мм",
        control="сверка после перестроения по sw_parameters/sw_features",
    ),
    ParameterMapEntry(
        app_parameter="step_mm",
        solidworks_id="уточнить",
        unit="мм",
    ),
    ParameterMapEntry(
        app_parameter="working_length_mm",
        solidworks_id="уточнить (см. crossbar_length_mm — прецедент для узла 09, не для шнека)",
        unit="мм",
    ),
]
