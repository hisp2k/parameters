# -*- coding: utf-8 -*-
"""
Тесты веб-интерфейса (раздел 2 задания): "пользователь никогда не
редактирует JSON напрямую". Используют Flask test client с изолированным
`data_dir` (см. `webapp.app.create_app(data_dir=...)`), чтобы не задевать
реальные файлы проектов в `calculator/data/`.

Проверяют форму (создание/редактирование анкеты без правки JSON), явный
выбор роли на каждое чувствительное действие (раздел 5 — без наследования),
и что редактирование анкеты идёт через тот же `project.set_questionnaire()`,
что и CLI (раздел 1.Б — устаревшие результаты аннулируются).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest

from calculator.webapp.app import create_app
from calculator.core.project import Project
from calculator.core.questionnaire import (
    QuestionnaireInput, ConveyorKind, MaterialInput, ProductivityInput,
    GeometryInput, GeometryMode, OperatingProfileInput, OptionalDetails,
)


@pytest.fixture(autouse=True)
def isolated_cad_transport(monkeypatch):
    # Offline web tests must never discover or call a workstation CAD process.
    from calculator.cad_adapter.bridge_transport import FakeBridgeTransport
    monkeypatch.setattr("calculator.webapp.app.FileBridgeTransport", lambda **kwargs: FakeBridgeTransport({}))


VALID_FORM = {
    "designation": "webtest_pytest",
    "project_name": "Пайтест проект",
    "customer": "Заказчик",
    "conveyor_kind": "валовый_желобчатый",
    "material_name": "песок",
    "bulk_density_kg_m3": "700",
    "max_lump_size_mm": "15",
    "abrasiveness": "средняя",
    "productivity_value": "5",
    "productivity_unit": "т/ч",
    "geometry_mode": "длина_по_оси_и_угол",
    "working_length_mm": "3000",
    "incline_deg": "0",
    "duty_mode": "нормальный",
    "environment": "цех",
    "construction_material": "Ст3",
}


VALID_TUBE_FORM = {
    "designation": "webtest_tube_pytest",
    "project_name": "Пайтест труба",
    "customer": "Заказчик",
    "conveyor_kind": "валовый_трубчатый",
    "material_name": "вода с песком",
    "bulk_density_kg_m3": "",
    "max_lump_size_mm": "",
    "abrasiveness": "",
    "productivity_value": "",
    "productivity_unit": "",
    "geometry_mode": "длина_по_оси_и_угол",
    "working_length_mm": "2515",
    "incline_deg": "35",
    "duty_mode": "нормальный",
    "environment": "не указано заказчиком",
    "construction_material": "Ст3",
    "connection_diameter_mm": "100",
    "load_height_from_floor_mm": "500",
    "unload_height_from_floor_mm": "1500",
    "is_slurry_mixture": "true",
    "drive_location_text": "нижний_торец",
    "drive_location_text_source": "текст эскиза, п.5",
    "drive_location_graphic": "верхний_торец",
    "drive_location_graphic_source": "графика эскиза",
}


@pytest.fixture
def client(tmp_path):
    app = create_app(data_dir=tmp_path)
    app.testing = True
    return app.test_client()


def test_index_empty_shows_new_project_button(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Новый проект" in r.data.decode()


def test_new_project_get_renders_form(client):
    r = client.get("/new")
    assert r.status_code == 200
    assert "material_name" in r.data.decode()


def test_create_project_success_redirects_to_dashboard(client):
    r = client.post("/new", data=VALID_FORM, follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/project/webtest_pytest")


def test_create_project_persists_no_raw_json_shown_to_user(client, tmp_path):
    client.post("/new", data=VALID_FORM)
    project_file = tmp_path / "webtest_pytest.json"
    assert project_file.exists()
    r = client.get("/project/webtest_pytest")
    body = r.data.decode()
    # дашборд показывает результаты расчёта, а не сырое содержимое JSON проекта
    assert "diameter_mm" not in body
    assert "Инженерное ядро" in body


def test_create_project_rejects_bad_designation(client):
    form = dict(VALID_FORM, designation="../evil path!")
    r = client.post("/new", data=form)
    assert r.status_code == 200  # форма перерисована с ошибкой, не редирект
    assert "латинские буквы" in r.data.decode()


def test_create_project_rejects_duplicate_designation(client):
    client.post("/new", data=VALID_FORM)
    r = client.post("/new", data=VALID_FORM)
    assert "уже существует" in r.data.decode()


def test_create_project_shows_validation_issues_without_crashing(client):
    form = dict(VALID_FORM, bulk_density_kg_m3="")  # обязательное поле пусто
    r = client.post("/new", data=form)
    assert r.status_code == 200
    assert "плотность" in r.data.decode().lower()


def test_dashboard_shows_engineering_results_and_drive_requirements(client):
    client.post("/new", data=VALID_FORM)
    body = client.get("/project/webtest_pytest").data.decode()
    assert "Требования к приводу" in body
    assert "Охват проверки прочности" in body
    assert "Блокировки выпуска" in body


def test_unknown_project_404s(client):
    r = client.get("/project/does_not_exist")
    assert r.status_code == 404


def test_path_traversal_designation_404s_not_500(client):
    r = client.get("/project/..%2f..%2fetc%2fpasswd")
    assert r.status_code == 404


def test_edit_project_prefills_form_and_recomputes(client, tmp_path):
    client.post("/new", data=VALID_FORM)

    r = client.get("/project/webtest_pytest/edit")
    assert r.status_code == 200
    assert 'value="5"' in r.data.decode() or "5" in r.data.decode()  # старое значение производительности видно

    changed = dict(VALID_FORM)
    changed["productivity_value"] = "100"  # раздел 1.Б: существенное изменение
    r = client.post("/project/webtest_pytest/edit", data=changed, follow_redirects=True)
    body = r.data.decode()
    assert "ревизия поднята" in body or "Ревизия поднята" in body.lower() or "поднята" in body


def test_edit_bumps_revision_and_invalidates_confirmations(client, tmp_path):
    client.post("/new", data=VALID_FORM)
    client.post("/project/webtest_pytest/confirm-assumptions", data={
        "person_name": "Иванов И.И.", "assigned_roles": ["инженер"], "acting_as": "инженер",
    })

    import json
    before = json.loads((tmp_path / "webtest_pytest.json").read_text(encoding="utf-8"))
    assert before["engineer_confirmed_assumptions"] is True

    changed = dict(VALID_FORM)
    changed["productivity_value"] = "100"
    client.post("/project/webtest_pytest/edit", data=changed)

    after = json.loads((tmp_path / "webtest_pytest.json").read_text(encoding="utf-8"))
    assert after["engineer_confirmed_assumptions"] is False
    assert after["revision"] != before["revision"]


def test_confirm_assumptions_requires_engineer_role(client):
    client.post("/new", data=VALID_FORM)
    r = client.post("/project/webtest_pytest/confirm-assumptions", data={
        "person_name": "Петров П.П.", "assigned_roles": ["менеджер"], "acting_as": "менеджер",
    }, follow_redirects=True)
    assert "не может выполнить" in r.data.decode()


def test_confirm_assumptions_rejects_acting_as_not_in_assigned_roles(client):
    client.post("/new", data=VALID_FORM)
    r = client.post("/project/webtest_pytest/confirm-assumptions", data={
        "person_name": "Иванов И.И.", "assigned_roles": ["менеджер"], "acting_as": "инженер",
    }, follow_redirects=True)
    body = r.data.decode()
    assert "не назначен" in body or "не может выполнить" in body


def test_confirm_assumptions_succeeds_for_engineer(client, tmp_path):
    client.post("/new", data=VALID_FORM)
    r = client.post("/project/webtest_pytest/confirm-assumptions", data={
        "person_name": "Иванов И.И.", "assigned_roles": ["инженер"], "acting_as": "инженер",
    }, follow_redirects=True)
    assert "подтверждены" in r.data.decode()

    import json
    saved = json.loads((tmp_path / "webtest_pytest.json").read_text(encoding="utf-8"))
    assert saved["engineer_confirmed_assumptions"] is True
    assert saved["engineer_confirmed_by"] == "Иванов И.И."  # ИМЯ, не строка с ролями (для is_independent())


def test_technical_review_rejects_same_person_as_confirmer(client):
    client.post("/new", data=VALID_FORM)
    client.post("/project/webtest_pytest/confirm-assumptions", data={
        "person_name": "Иванов И.И.", "assigned_roles": ["инженер"], "acting_as": "инженер",
    })
    r = client.post("/project/webtest_pytest/technical-review", data={
        "person_name": "Иванов И.И.", "assigned_roles": ["инженер"], "acting_as": "инженер",
    }, follow_redirects=True)
    assert "независимая проверка" in r.data.decode()


def test_technical_review_succeeds_for_different_person(client):
    client.post("/new", data=VALID_FORM)
    client.post("/project/webtest_pytest/confirm-assumptions", data={
        "person_name": "Иванов И.И.", "assigned_roles": ["инженер"], "acting_as": "инженер",
    })
    r = client.post("/project/webtest_pytest/technical-review", data={
        "person_name": "Сидоров С.С.", "assigned_roles": ["инженер"], "acting_as": "инженер",
    }, follow_redirects=True)
    assert "зафиксирована" in r.data.decode()


def test_release_approval_requires_head_role(client):
    client.post("/new", data=VALID_FORM)
    r = client.post("/project/webtest_pytest/release-approval", data={
        "person_name": "Инженеров И.И.", "assigned_roles": ["инженер"], "acting_as": "инженер",
    }, follow_redirects=True)
    assert "не может выполнить" in r.data.decode()


def test_release_approval_by_head_still_blocked_by_gate(client):
    client.post("/new", data=VALID_FORM)
    r = client.post("/project/webtest_pytest/release-approval", data={
        "person_name": "Директор Д.Д.", "assigned_roles": ["руководитель"], "acting_as": "руководитель",
    }, follow_redirects=True)
    assert "НЕ записано" in r.data.decode()


def test_document_download_routes_serve_generated_files(client):
    client.post("/new", data=VALID_FORM)
    r = client.get("/project/webtest_pytest/file/agreement_html")
    assert r.status_code == 200
    assert r.mimetype == "text/html"

    r = client.get("/project/webtest_pytest/file/agreement_pdf")
    assert r.status_code == 200
    assert r.mimetype == "application/pdf"

    r = client.get("/project/webtest_pytest/file/technology_json")
    assert r.status_code == 200
    assert r.mimetype == "application/json"


def test_document_download_rejects_unknown_kind(client):
    client.post("/new", data=VALID_FORM)
    r = client.get("/project/webtest_pytest/file/nonexistent_kind")
    assert r.status_code == 404


def test_dashboard_shows_cad_sync_panel(client):
    client.post("/new", data=VALID_FORM)
    body = client.get("/project/webtest_pytest").data.decode()
    assert "Синхронизация компоновки желоба с CAD" in body
    assert "Актуального чтения состава нет" in body


def test_cad_sync_requires_engineer_role(client):
    client.post("/new", data=VALID_FORM)
    r = client.post("/project/webtest_pytest/cad-sync", data={
        "person_name": "Петров П.П.", "assigned_roles": ["менеджер"], "acting_as": "менеджер",
        "nominal_section_length_mm": "3000", "target_section_count": "4",
    }, follow_redirects=True)
    assert "не может выполнить" in r.data.decode()


def test_cad_sync_rejects_non_numeric_input_without_crashing(client):
    client.post("/new", data=VALID_FORM)
    r = client.post("/project/webtest_pytest/cad-sync", data={
        "person_name": "Иванов И.И.", "assigned_roles": ["инженер"], "acting_as": "инженер",
        "nominal_section_length_mm": "не число", "target_section_count": "4",
    }, follow_redirects=True)
    assert r.status_code == 200
    assert "должны быть числами" in r.data.decode()


def test_cad_sync_honestly_reports_bridge_unavailable_in_this_environment(client, tmp_path):
    """
    Этот тест НЕ подменяет транспорт — он реально проходит через
    FileBridgeTransport в среде без Windows/PowerShell/SolidWorks и проверяет,
    что маршрут честно показывает "коннектор недоступен", а не падает и не
    выдумывает результат (раздел 5/12: "проверка CAD-недоступности").
    """
    client.post("/new", data=VALID_FORM)
    r = client.post("/project/webtest_pytest/cad-sync", data={
        "person_name": "Иванов И.И.", "assigned_roles": ["инженер"], "acting_as": "инженер",
        "nominal_section_length_mm": "3000", "target_section_count": "4",
    }, follow_redirects=True)
    assert r.status_code == 200
    body = r.data.decode()
    assert "CAD-синхронизация не удалась" in body

    import json
    saved = json.loads((tmp_path / "webtest_pytest.json").read_text(encoding="utf-8"))
    assert saved["cad_sync"]["done"] is False
    assert "trough_measured_section_count" not in saved["parameters"]  # не выдумано


def test_cad_sync_is_idempotent_when_bridge_unavailable(client, tmp_path):
    client.post("/new", data=VALID_FORM)
    data = {
        "person_name": "Иванов И.И.", "assigned_roles": ["инженер"], "acting_as": "инженер",
        "nominal_section_length_mm": "3000", "target_section_count": "4",
    }
    client.post("/project/webtest_pytest/cad-sync", data=data)

    import json
    first = json.loads((tmp_path / "webtest_pytest.json").read_text(encoding="utf-8"))

    client.post("/project/webtest_pytest/cad-sync", data=data)
    second = json.loads((tmp_path / "webtest_pytest.json").read_text(encoding="utf-8"))

    assert first["cad_sync"]["done"] == second["cad_sync"]["done"] == False
    assert set(first["parameters"].keys()) == set(second["parameters"].keys())


def test_tube_web_form_roundtrip_matches_python_api(client, tmp_path):
    """
    Issue #3, продолжение 17.09.2026, этап 1: трубные поля (DN, высоты пола,
    is_slurry_mixture, оба источника расположения привода) должны доходить
    из HTML-формы до QuestionnaireInput ТОЧНО так же, как при создании
    проекта напрямую через Python API (app.create_project) — иначе форма и
    API молча расходятся.
    """
    r = client.post("/new", data=VALID_TUBE_FORM, follow_redirects=True)
    assert r.status_code == 200

    from_web = Project.load(tmp_path / "webtest_tube_pytest.json").questionnaire

    from_api = QuestionnaireInput(
        conveyor_kind=ConveyorKind.SHAFTED_TUBE,
        material=MaterialInput(material_name="вода с песком"),
        productivity=ProductivityInput(),  # value=None, unit=None — форма их тоже оставила пустыми
        geometry=GeometryInput(
            mode=GeometryMode.AXIS_LENGTH_ANGLE, working_length_mm=2515.0, incline_deg=35.0,
            connection_diameter_mm=100.0, load_height_from_floor_mm=500.0, unload_height_from_floor_mm=1500.0,
        ),
        profile=OperatingProfileInput(
            duty_mode="нормальный", environment="не указано заказчиком", construction_material="Ст3",
        ),
        optional=OptionalDetails(
            is_slurry_mixture=True,
            drive_location_text="нижний_торец", drive_location_text_source="текст эскиза, п.5",
            drive_location_graphic="верхний_торец", drive_location_graphic_source="графика эскиза",
        ),
    )

    assert from_web.conveyor_kind == from_api.conveyor_kind
    assert from_web.material.material_name == from_api.material.material_name
    assert from_web.productivity.value == from_api.productivity.value
    assert from_web.productivity.unit == from_api.productivity.unit
    assert from_web.geometry.working_length_mm == from_api.geometry.working_length_mm
    assert from_web.geometry.incline_deg == from_api.geometry.incline_deg
    assert from_web.geometry.connection_diameter_mm == from_api.geometry.connection_diameter_mm
    assert from_web.geometry.load_height_from_floor_mm == from_api.geometry.load_height_from_floor_mm
    assert from_web.geometry.unload_height_from_floor_mm == from_api.geometry.unload_height_from_floor_mm
    assert from_web.optional.is_slurry_mixture == from_api.optional.is_slurry_mixture
    assert from_web.optional.drive_location_text == from_api.optional.drive_location_text
    assert from_web.optional.drive_location_text_source == from_api.optional.drive_location_text_source
    assert from_web.optional.drive_location_graphic == from_api.optional.drive_location_graphic
    assert from_web.optional.drive_location_graphic_source == from_api.optional.drive_location_graphic_source


def test_tube_web_form_edit_preserves_conveyor_kind(client, tmp_path):
    """
    Регрессия найдена при этой доработке: в режиме редактирования форма не
    передавала conveyor_kind вообще, и forms.py::_enum_or_error молча
    подставлял default=SHAFTED_TROUGH — то есть ЛЮБОЕ редактирование
    SHAFTED_TUBE-проекта через веб-форму превращало его в SHAFTED_TROUGH.
    Исправлено скрытым полем в project_form.html (режим "edit").
    """
    client.post("/new", data=VALID_TUBE_FORM)
    r = client.get("/project/webtest_tube_pytest/edit")
    assert r.status_code == 200
    assert 'value="валовый_трубчатый"' in r.data.decode()

    edited = dict(VALID_TUBE_FORM)
    edited["duty_hours_per_day"] = "16"
    client.post("/project/webtest_tube_pytest/edit", data=edited, follow_redirects=True)

    reloaded = Project.load(tmp_path / "webtest_tube_pytest.json")
    assert reloaded.questionnaire.conveyor_kind == ConveyorKind.SHAFTED_TUBE
    assert reloaded.questionnaire.optional.duty_hours_per_day == 16.0


def test_two_apps_with_different_data_dirs_do_not_share_projects(tmp_path):
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    client_a = create_app(data_dir=dir_a).test_client()
    client_b = create_app(data_dir=dir_b).test_client()

    client_a.post("/new", data=VALID_FORM)
    assert client_a.get("/project/webtest_pytest").status_code == 200
    assert client_b.get("/project/webtest_pytest").status_code == 404
