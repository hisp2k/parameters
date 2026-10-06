"""Regression coverage for the 52125b2 review. No live SolidWorks calls."""
import copy
import json

import pytest

from calculator.cad_adapter.bridge_transport import FakeBridgeTransport
from calculator.cad_adapter.section_layout import read_trough_section_layout, TroughSectionLayout
from calculator.core.project import Project, TechnicalReview, ReleaseApproval
from calculator.core.roles import Role
from calculator.core.release_gate import evaluate
from calculator.tests.test_section_layout import (
    _ok, _components_page, _four_sections_three_spacers_page, _item,
    DEFAULT_SECTION_NAME_PREFIX, DEFAULT_SPACER_NAME_PREFIX,
)
from calculator.tests.test_project_and_gate import _sample_project
from calculator.tests.test_webapp import VALID_FORM, client


def read(page=None, **kwargs):
    transport = FakeBridgeTransport(responses={
        "sw_status": _ok("sw_status"),
        "sw_components": page if page is not None else _four_sections_three_spacers_page(),
    })
    args = dict(nominal_section_length_mm=3000., target_section_count=4)
    args.update(kwargs)
    return read_trough_section_layout(transport, **args)


@pytest.mark.parametrize("field,value", [
    ("nominal_section_length_mm", float("nan")),
    ("nominal_section_length_mm", float("inf")),
    ("nominal_section_length_mm", True),
    ("target_section_count", 4.5),
    ("target_section_count", True),
    ("target_section_count", 10 ** 1000),
    ("measured_joint_spacer_thickness_mm", -2),
    ("measured_joint_spacer_thickness_mm", float("nan")),
    ("measured_joint_spacer_thickness_mm", float("inf")),
    ("page_limit", 51),
    ("max_pages", 0),
])
def test_invalid_numeric_inputs_rejected_before_bridge(field, value):
    with pytest.raises(ValueError):
        read(**{field: value})


@pytest.mark.parametrize("kind", ["empty", "inner_error", "scope", "truncated_without_next",
                                 "lost_final_page", "repeated_offset", "non_string_name",
                                 "duplicate_instance", "issues"])
def test_malformed_or_incomplete_response_never_publishes_counts(kind):
    page = _four_sections_three_spacers_page()
    inner = page.result["data"]["data"]
    if kind == "empty":
        page.result = {}
    elif kind == "inner_error":
        page.result["ok"] = False
    elif kind == "scope":
        inner["scope"] = "RECURSIVE_INSTANCES"
    elif kind == "truncated_without_next":
        inner["truncated"] = True
        inner["total"] += 1
    elif kind == "lost_final_page":
        inner["total"] += 1
    elif kind == "repeated_offset":
        inner.update(truncated=True, next_offset=0, total=20)
    elif kind == "non_string_name":
        inner["items"][0]["name"] = None
    elif kind == "duplicate_instance":
        inner["items"][1] = inner["items"][0]
    else:
        page.result["data"]["issues"] = ["partial document loading"]
    result = read(page)
    assert not result.ok
    assert result.errors
    assert result.measured_section_count is None
    assert result.measured_overall_length_estimate_mm is None


def test_two_spacers_are_not_inferred_as_three_and_no_length_is_published():
    page = _four_sections_three_spacers_page()
    inner = page.result["data"]["data"]
    inner["items"] = [x for x in inner["items"] if not x["name"].endswith("отсеков-3")]
    inner["total"] = len(inner["items"])
    result = read(page, measured_joint_spacer_thickness_mm=2)
    assert result.ok
    assert result.measured_spacer_count == 2
    assert len(result.spacer_instances) == 2
    assert result.measured_overall_length_estimate_mm is None
    assert any("стыков 3" in w for w in result.warnings)


def test_changed_assembly_between_pages_is_rejected():
    p1 = _components_page([_item(DEFAULT_SECTION_NAME_PREFIX + " Отсек-1")],
                          total=2, next_offset=1, truncated=True)
    p2 = _components_page([_item(DEFAULT_SECTION_NAME_PREFIX + " Отсек-2")], total=2, offset=1)
    p2.result["data"]["context"]["different_document"] = True
    transport = FakeBridgeTransport(responses={
        "sw_status": _ok("sw_status"),
        "sw_components": lambda args: p1 if args["offset"] == 0 else p2,
    })
    result = read_trough_section_layout(transport, nominal_section_length_mm=3000., target_section_count=2)
    assert not result.ok
    assert result.measured_section_count is None


def record(project, layout):
    project.record_trough_section_layout(layout, recorded_by="Инженер", recorded_by_role=Role.ENGINEER)


def test_count_mismatch_cannot_close_full_cad_gate(tmp_path):
    project = _sample_project(tmp_path)
    record(project, read(target_section_count=5))
    assert project.cad_layout_readback.done
    assert not project.cad_sync.done
    assert any("Синхронизация CAD" in r for r in evaluate(project, Role.HEAD))


def test_failed_read_clears_old_measurements_and_invalidates_documents(tmp_path):
    project = _sample_project(tmp_path)
    record(project, read(measured_joint_spacer_thickness_mm=2))
    doc = project.issue_document("agreement", "old.pdf")
    record(project, TroughSectionLayout(False, 3000., 4, 12000., errors=["bridge unavailable"]))
    assert not project.cad_layout_readback.done
    assert not project.cad_sync.done
    assert "trough_measured_section_count" not in project.parameters
    assert "trough_overall_length_estimate_mm" not in project.parameters
    assert not doc.is_current(project.revision)


def test_removing_manual_thickness_removes_old_estimate(tmp_path):
    project = _sample_project(tmp_path)
    record(project, read(measured_joint_spacer_thickness_mm=2))
    assert project.parameters["trough_overall_length_estimate_mm"].value == 12006
    record(project, read())
    assert "trough_overall_length_estimate_mm" not in project.parameters
    assert "trough_measured_joint_spacer_thickness_mm" not in project.parameters


def test_identical_read_is_idempotent_but_changed_target_invalidates_approvals(tmp_path):
    project = _sample_project(tmp_path)
    layout = read()
    record(project, layout)
    rev = project.revision
    doc = project.issue_document("agreement", "old.pdf")
    project.technical_review = TechnicalReview("Проверяющий", Role.ENGINEER, "Инженер")
    project.release_approval = ReleaseApproval("Директор", product_revision=rev)
    record(project, copy.deepcopy(layout))
    assert project.revision == rev
    record(project, read(target_section_count=5))
    assert project.revision != rev
    assert not doc.is_current(project.revision)
    assert project.technical_review is None
    assert project.release_approval is None


def test_legacy_counting_success_does_not_restore_cad_approval(tmp_path):
    project = _sample_project(tmp_path)
    record(project, read())
    payload = project.to_dict()
    payload.pop("cad_layout_readback")
    payload.pop("trough_section_layout")
    payload["cad_sync"]["done"] = True
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    loaded = Project.load(path)
    assert not loaded.cad_sync.done
    assert not loaded.cad_layout_readback.done
    assert loaded.revision != project.revision


def test_record_requires_engineer_even_outside_web_route(tmp_path):
    project = _sample_project(tmp_path)
    with pytest.raises(PermissionError):
        project.record_trough_section_layout(read(), recorded_by="Директор", recorded_by_role=Role.HEAD)


CAD_FORM = {
    "person_name": "Инженер", "assigned_roles": ["инженер"], "acting_as": "инженер",
    "nominal_section_length_mm": "3000", "target_section_count": "4",
    "measured_joint_spacer_thickness_mm": "2",
}


def test_web_success_then_exception_clears_stale_cad_and_keeps_release_blocked(client, tmp_path, monkeypatch):
    import calculator.webapp.app as app_module
    client.post("/new", data=VALID_FORM)
    monkeypatch.setattr(app_module, "read_trough_section_layout", lambda *a, **kw: read(measured_joint_spacer_thickness_mm=2))
    response = client.post("/project/webtest_pytest/cad-sync", data=CAD_FORM, follow_redirects=True)
    assert response.status_code == 200
    assert "12006" in response.data.decode()
    saved = Project.load(tmp_path / "webtest_pytest.json")
    assert saved.cad_layout_readback.done
    assert not saved.cad_sync.done

    def broken(*a, **kw):
        raise RuntimeError("bridge interrupted")
    monkeypatch.setattr(app_module, "read_trough_section_layout", broken)
    response = client.post("/project/webtest_pytest/cad-sync", data=CAD_FORM, follow_redirects=True)
    assert "bridge interrupted" in response.data.decode()
    saved = Project.load(tmp_path / "webtest_pytest.json")
    assert not saved.cad_layout_readback.done
    assert "trough_measured_section_count" not in saved.parameters
    assert "12006" not in response.data.decode()


@pytest.mark.parametrize("field,value", [
    ("nominal_section_length_mm", "nan"), ("measured_joint_spacer_thickness_mm", "-2"),
    ("measured_joint_spacer_thickness_mm", "inf"),
])
def test_web_invalid_values_never_call_bridge(client, monkeypatch, field, value):
    import calculator.webapp.app as app_module
    client.post("/new", data=VALID_FORM)
    def unexpected(*a, **kw):
        pytest.fail("invalid input reached bridge")
    monkeypatch.setattr(app_module, "read_trough_section_layout", unexpected)
    response = client.post("/project/webtest_pytest/cad-sync", data={**CAD_FORM, field: value},
                           follow_redirects=True)
    assert response.status_code == 200
    assert "конечное положительное число" in response.data.decode()
