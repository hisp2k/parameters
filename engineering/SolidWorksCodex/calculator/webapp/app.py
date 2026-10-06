# -*- coding: utf-8 -*-
"""
Flask-приложение веб-интерфейса (раздел 2 задания).

Экраны:
    /                         — список проектов, кнопка "Новый проект"
    /new                      — Экран 1 "Задача" (анкета) для нового проекта
    /project/<designation>    — Экран 2/3/4: результаты, схема, прочность,
                                 привод, технология, ревизии, документы
    /project/<designation>/edit
                              — повторная анкета для СУЩЕСТВУЮЩЕГО проекта
                                (через project.set_questionnaire(), раздел 1.Б)
    /project/<designation>/confirm-assumptions
    /project/<designation>/technical-review
    /project/<designation>/release-approval
                              — три действия, требующие явного выбора роли
                                (раздел 2/5 — совмещение ролей не наследуется
                                автоматически, см. core/roles.RoleContext)
    /project/<designation>/file/<kind>
                              — отдать сгенерированный документ (HTML/PDF/
                                JSON технологии) — единственный "сырой JSON",
                                который видит пользователь, это ЧЕРНОВИК
                                технологии для просмотра, а не редактируемый
                                вход системы (раздел 2: анкета вводится только
                                через форму, а не правкой JSON проекта).

Запуск: `cd calculator && python3 -m webapp.app` (см. __main__ внизу).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort

from calculator.app import (
    DATA_DIR, QuestionnaireValidationError, create_project, recompute_and_save,
)
from calculator.core.questionnaire import (
    ConveyorKind, ProductivityUnit, GeometryMode, Abrasiveness, validate_questionnaire,
)
from calculator.core.screw_engineering import EngineeringInputError
from calculator.core.tube_engineering import TubeEngineeringInputError, DriveLocation
from calculator.core.project import Project, TechnicalReview, ReleaseApproval
from calculator.core.roles import Role, RoleContext
from calculator.core.release_gate import evaluate as evaluate_release_gate
from calculator.core.strength_coverage import coverage_report
from calculator.documents.schematic import SchematicData, render_html_svg
from calculator.webapp.forms import (
    FormError, parse_designation, questionnaire_from_form, form_defaults_from_questionnaire,
)
from calculator.cad_adapter.bridge_transport import FileBridgeTransport
from calculator.cad_adapter.section_layout import (
    TroughSectionLayout, read_trough_section_layout, validate_layout_inputs,
)


# Корень репозитория SolidWorksCodex НА ТОЙ МАШИНЕ, где реально запущен этот
# процесс Flask (см. cad_adapter/bridge_transport.py::FileBridgeTransport) —
# `calculator/webapp/app.py` лежит на два уровня ниже корня репозитория,
# так же, как sys.path.insert() выше в этом файле уже это предполагает.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _project_path(designation: str, data_dir: Path) -> Path:
    return data_dir / f"{designation}.json"


def _load_project_or_404(designation: str, data_dir: Path) -> Project:
    try:
        designation = parse_designation(designation)
    except FormError:
        abort(404)
    path = _project_path(designation, data_dir)
    if not path.exists():
        abort(404)
    return Project.load(path)


def _list_projects(data_dir: Path) -> list[Project]:
    """
    Раздел 2: "хранение проекта" — список читается заново с диска при каждом
    открытии страницы (единственный источник истины — файл проекта, не
    состояние процесса Flask), поэтому список никогда не расходится с тем,
    что реально сохранено (в т.ч. если файл изменён параллельным запуском
    CLI-сценария `app.py`).
    """
    if not data_dir.exists():
        return []
    projects = []
    for path in sorted(data_dir.glob("*.json")):
        if path.stem.endswith("_technology_draft"):
            continue
        try:
            projects.append(Project.load(path))
        except Exception:
            continue  # не проектный JSON (или повреждён) — пропускаем список, не роняем страницу
    projects.sort(key=lambda p: p.updated_at, reverse=True)
    return projects


def _role_context_from_form(form) -> RoleContext | None:
    """
    Раздел 2/5: выбор роли — ВСЕГДА явный, отдельно на каждое чувствительное
    действие, а не один раз на сессию и не подставляемый автоматически по
    "старшей" роли. Возвращает None, если форма не содержит выбора роли
    (вызывающий код сам решает, обязателен ли он для этого действия).
    """
    person_name = (form.get("person_name") or "").strip()
    assigned_raw = form.getlist("assigned_roles")
    acting_as_raw = form.get("acting_as") or ""
    if not person_name or not assigned_raw or not acting_as_raw:
        raise FormError("Укажите ФИО, все совмещаемые роли и роль, от имени которой выполняется действие.")
    try:
        assigned_roles = {Role(r) for r in assigned_raw}
        acting_as = Role(acting_as_raw)
    except ValueError:
        raise FormError("Недопустимая роль в форме.")
    return RoleContext(person_name=person_name, assigned_roles=assigned_roles, acting_as=acting_as)


def create_app(data_dir: Path | None = None) -> Flask:
    """
    `data_dir` — где читать/писать проекты; по умолчанию — та же папка, что
    использует CLI-сценарий `calculator/app.py` (`calculator/data/`). Явный
    параметр (а не только модульная константа) нужен для тестов веб-слоя
    (`tests/test_webapp.py`), чтобы они работали в изолированном временном
    каталоге и не задевали реальные файлы проектов.
    """
    data_dir = data_dir if data_dir is not None else DATA_DIR

    app = Flask(__name__)
    app.secret_key = "screw-conveyor-calculator-local-dev"  # только для flash-сообщений локального инструмента

    form_choices = {
        "conveyor_kinds": list(ConveyorKind),
        "productivity_units": list(ProductivityUnit),
        "geometry_modes": list(GeometryMode),
        "abrasiveness_levels": list(Abrasiveness),
        "roles": list(Role),
        "drive_locations": list(DriveLocation),
    }

    @app.context_processor
    def inject_choices():
        return {"choices": form_choices}

    @app.route("/")
    def index():
        return render_template("index.html", projects=_list_projects(data_dir))

    @app.route("/new", methods=["GET", "POST"])
    def new_project():
        if request.method == "GET":
            default_values = {
                "conveyor_kind": ConveyorKind.SHAFTED_TROUGH.value,
                "productivity_unit": ProductivityUnit.T_H.value,
                "geometry_mode": GeometryMode.AXIS_LENGTH_ANGLE.value,
                "incline_deg": 0,
                "duty_mode": "нормальный",
                "environment": "цех, без агрессивной среды",
                "construction_material": "Ст3",
            }
            return render_template("project_form.html", mode="new", values=default_values, errors=[])

        errors: list[str] = []
        try:
            designation = parse_designation(request.form.get("designation"))
        except FormError as e:
            designation = (request.form.get("designation") or "").strip()
            errors.append(str(e))

        project_name = (request.form.get("project_name") or "").strip()
        customer = (request.form.get("customer") or "").strip()
        if not project_name:
            errors.append("Укажите наименование проекта.")
        if not customer:
            errors.append("Укажите заказчика.")

        if _project_path(designation or "_", data_dir).exists() and not errors:
            errors.append(f"Проект с обозначением {designation!r} уже существует — откройте его для редактирования.")

        questionnaire = None
        try:
            questionnaire = questionnaire_from_form(request.form)
        except FormError as e:
            errors.append(str(e))

        if not errors and questionnaire is not None:
            validation_issues = validate_questionnaire(questionnaire)
            if validation_issues:
                errors.extend(validation_issues)

        if errors:
            return render_template("project_form.html", mode="new", values=request.form, errors=errors)

        try:
            project, outcome = create_project(questionnaire, project_name, customer, designation, data_dir=data_dir)
        except QuestionnaireValidationError as e:
            return render_template("project_form.html", mode="new", values=request.form, errors=e.issues)
        except EngineeringInputError as e:
            return render_template(
                "project_form.html", mode="new", values=request.form,
                errors=[f"Инженерное ядро остановило расчёт: {e}"],
            )
        except TubeEngineeringInputError as e:
            return render_template(
                "project_form.html", mode="new", values=request.form,
                errors=[f"Инженерное ядро трубного шнека остановило расчёт: {e}"],
            )

        flash(f"Проект {designation!r} создан. Ревизия {project.revision}.", "success")
        return redirect(url_for("project_dashboard", designation=designation))

    @app.route("/project/<designation>")
    def project_dashboard(designation: str):
        project = _load_project_or_404(designation, data_dir)

        schematic_svg = None
        if project.questionnaire is not None and project.engineering_result is not None:
            length, _angle = project.questionnaire.geometry.resolved_length_angle()
            if length is not None:
                schematic_svg = render_html_svg(SchematicData(
                    working_length_mm=length,
                    incline_deg=(project.questionnaire.geometry.incline_deg or 0.0),
                    diameter_mm=project.engineering_result.diameter_mm,
                    designation=project.designation,
                    is_preliminary=True,
                ))

        input_fingerprint = project.compute_input_fingerprint()
        coverage = coverage_report(project.strength_registry, project.revision, input_fingerprint)
        coverage_summary = [
            {"item": item, "closed": closed, "reasons": reasons}
            for item, closed, reasons in coverage
        ]

        release_reasons = evaluate_release_gate(project, requesting_role=Role.HEAD)

        return render_template(
            "dashboard.html",
            project=project,
            schematic_svg=schematic_svg,
            coverage_summary=coverage_summary,
            release_reasons=release_reasons,
            is_stale=project.is_calc_stale(),
        )

    @app.route("/project/<designation>/edit", methods=["GET", "POST"])
    def edit_project(designation: str):
        project = _load_project_or_404(designation, data_dir)

        if request.method == "GET":
            values = form_defaults_from_questionnaire(project.questionnaire)
            return render_template("project_form.html", mode="edit", values=values, errors=[], project=project)

        errors: list[str] = []
        questionnaire = None
        try:
            questionnaire = questionnaire_from_form(request.form)
        except FormError as e:
            errors.append(str(e))

        if not errors and questionnaire is not None:
            validation_issues = validate_questionnaire(questionnaire)
            if validation_issues:
                errors.extend(validation_issues)

        if errors:
            return render_template(
                "project_form.html", mode="edit", values=request.form, errors=errors, project=project,
            )

        try:
            invalidated = project.set_questionnaire(questionnaire, reason="изменение анкеты через веб-интерфейс")
            recompute_and_save(project, data_dir)
        except EngineeringInputError as e:
            return render_template(
                "project_form.html", mode="edit", values=request.form,
                errors=[f"Инженерное ядро остановило расчёт: {e}"], project=project,
            )
        except TubeEngineeringInputError as e:
            return render_template(
                "project_form.html", mode="edit", values=request.form,
                errors=[f"Инженерное ядро трубного шнека остановило расчёт: {e}"], project=project,
            )

        if invalidated:
            flash(
                f"Анкета изменилась по существу — ревизия поднята до {project.revision}, "
                "предыдущее подтверждение инженера/техпроверка/утверждение выпуска аннулированы (раздел 1.Б).",
                "warning",
            )
        else:
            flash("Анкета обновлена, пересчитано.", "success")
        return redirect(url_for("project_dashboard", designation=designation))

    @app.route("/project/<designation>/cad-sync", methods=["POST"])
    def cad_sync(designation: str):
        """
        Раздел 4 доп. задания: "изменение модели из калькулятора с обратным
        получением фактических размеров". Эта версия только ЧИТАЕТ фактическую
        компоновку желоба обратно из SolidWorks (число секций/проставок,
        connector_write_allowed) — запись числа секций в сборку коннектором
        не поддерживается в этой редакции (см.
        cad_adapter/section_layout.py::TroughSectionLayout.write_unsupported_reason);
        секции добавляются вручную в SolidWorks («Линейный массив компонентов»).
        """
        project = _load_project_or_404(designation, data_dir)
        try:
            ctx = _role_context_from_form(request.form)
            ctx.require("rebuild_cad_project_copy")
        except (FormError, PermissionError) as e:
            flash(str(e), "error")
            return redirect(url_for("project_dashboard", designation=designation))

        try:
            nominal_section_length_mm = float((request.form.get("nominal_section_length_mm") or "").replace(",", "."))
            target_section_count = int(request.form.get("target_section_count") or "")
        except (TypeError, ValueError):
            flash("Номинальная длина секции и целевое количество секций должны быть числами.", "error")
            return redirect(url_for("project_dashboard", designation=designation))
        measured_thickness_raw = (request.form.get("measured_joint_spacer_thickness_mm") or "").strip()
        measured_joint_spacer_thickness_mm = None
        if measured_thickness_raw:
            try:
                measured_joint_spacer_thickness_mm = float(measured_thickness_raw.replace(",", "."))
            except ValueError:
                flash("Измеренная толщина проставки должна быть числом (или оставьте поле пустым).", "error")
                return redirect(url_for("project_dashboard", designation=designation))

        try:
            validate_layout_inputs(nominal_section_length_mm, target_section_count,
                                   measured_joint_spacer_thickness_mm)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("project_dashboard", designation=designation))

        transport = FileBridgeTransport(repo_root=REPO_ROOT)
        try:
            layout = read_trough_section_layout(
                transport,
                nominal_section_length_mm=nominal_section_length_mm,
                target_section_count=target_section_count,
                measured_joint_spacer_thickness_mm=measured_joint_spacer_thickness_mm,
            )
        except Exception as e:
            # Честная защита от непредвиденного исключения моста — не роняем страницу,
            # но и не скрываем сбой молча (раздел 5 — коннектор недоступен из облачной среды,
            # это ожидаемый и явно показываемый исход, а не скрытая ошибка 500).
            layout = TroughSectionLayout(
                ok=False, nominal_section_length_mm=nominal_section_length_mm,
                target_section_count=target_section_count,
                target_nominal_length_mm=nominal_section_length_mm * target_section_count,
                errors=[f"Чтение компоновки CAD не выполнено: {e}"],
            )

        project.record_trough_section_layout(layout, recorded_by=ctx.person_name, recorded_by_role=ctx.acting_as)
        project.save(_project_path(designation, data_dir))

        if layout.ok and not layout.errors:
            msg = (
                f"Прочитан состав желоба: секций {layout.measured_section_count} "
                f"(цель {layout.target_section_count}), проставок верхнего уровня {layout.measured_spacer_count}. "
                "Полная проверка CAD не выполнена."
            )
            if not layout.count_matches_target:
                msg += " Внимание: фактическое количество секций НЕ совпадает с целевым."
            flash(msg, "warning")
            for warning in layout.warnings:
                flash(warning, "warning")
        else:
            flash(
                "CAD-синхронизация не удалась: "
                + ("; ".join(layout.errors) if layout.errors else "коннектор недоступен."),
                "error",
            )
        return redirect(url_for("project_dashboard", designation=designation))

    @app.route("/project/<designation>/confirm-assumptions", methods=["POST"])
    def confirm_assumptions(designation: str):
        project = _load_project_or_404(designation, data_dir)
        try:
            ctx = _role_context_from_form(request.form)
            ctx.require("confirm_inputs_assumptions")
        except (FormError, PermissionError) as e:
            flash(str(e), "error")
            return redirect(url_for("project_dashboard", designation=designation))

        # ВАЖНО: в engineer_confirmed_by (и ниже, в TechnicalReview.reviewer_name/
        # prepared_by_name) кладём ИМЕННО person_name, а не ctx.label() —
        # is_independent() (раздел 1.А) сравнивает именно ЛИЧНОСТЬ проверяющего
        # и исполнителя. Если бы здесь использовался label() (включающий
        # перечень совмещаемых ролей), один и тот же человек мог бы пройти
        # проверку "независимости" просто отметив другой набор совмещаемых
        # ролей при подтверждении и при проверке — их полные строки-label
        # отличались бы, а физическое лицо было бы тем же самым.
        project.engineer_confirmed_assumptions = True
        project.engineer_confirmed_by = ctx.person_name
        project.save(_project_path(designation, data_dir))
        flash(f"Исходные данные и допущения подтверждены: {ctx.label()}.", "success")
        return redirect(url_for("project_dashboard", designation=designation))

    @app.route("/project/<designation>/technical-review", methods=["POST"])
    def technical_review(designation: str):
        project = _load_project_or_404(designation, data_dir)
        try:
            ctx = _role_context_from_form(request.form)
            ctx.require("review_strength_and_drive")
        except (FormError, PermissionError) as e:
            flash(str(e), "error")
            return redirect(url_for("project_dashboard", designation=designation))

        notes = (request.form.get("notes") or "").strip()
        review = TechnicalReview(
            # См. комментарий в confirm_assumptions() — person_name, не label(),
            # иначе is_independent() сравнивала бы строки с ролями, а не личности.
            reviewer_name=ctx.person_name,
            reviewer_role=ctx.acting_as,
            prepared_by_name=project.engineer_confirmed_by or "(не подтверждено)",
            input_fingerprint=project.compute_input_fingerprint(),
            product_revision=project.revision,
            notes=f"{notes} [{ctx.label()}]".strip() if notes else f"[{ctx.label()}]",
        )
        if not review.is_independent():
            flash(
                "Проверяющий совпадает с тем, кто подтвердил исходные данные — "
                "это не независимая проверка (раздел 1.А), запись не сохранена.",
                "error",
            )
            return redirect(url_for("project_dashboard", designation=designation))

        project.technical_review = review
        project.save(_project_path(designation, data_dir))
        flash(f"Техническая проверка зафиксирована: {ctx.label()}.", "success")
        return redirect(url_for("project_dashboard", designation=designation))

    @app.route("/project/<designation>/release-approval", methods=["POST"])
    def release_approval(designation: str):
        project = _load_project_or_404(designation, data_dir)
        try:
            ctx = _role_context_from_form(request.form)
            ctx.require("authorize_production_release")
        except (FormError, PermissionError) as e:
            flash(str(e), "error")
            return redirect(url_for("project_dashboard", designation=designation))

        reasons = evaluate_release_gate(project, requesting_role=ctx.acting_as)
        if reasons:
            flash(
                f"Утверждение НЕ записано: выпуск по-прежнему заблокирован ({len(reasons)} причин) — "
                "см. список блокировок ниже.",
                "error",
            )
            return redirect(url_for("project_dashboard", designation=designation))

        project.release_approval = ReleaseApproval(approved_by_name=ctx.label(), product_revision=project.revision)
        project.save(_project_path(designation, data_dir))
        flash(f"Выпуск утверждён: {ctx.label()}.", "success")
        return redirect(url_for("project_dashboard", designation=designation))

    @app.route("/project/<designation>/file/<kind>")
    def project_file(designation: str, kind: str):
        project = _load_project_or_404(designation, data_dir)
        kind_to_suffix = {
            "agreement_html": ("_list_soglasovaniya.html", "text/html"),
            "agreement_pdf": ("_list_soglasovaniya.pdf", "application/pdf"),
            "technology_json": ("_technology_draft.json", "application/json"),
        }
        if kind not in kind_to_suffix:
            abort(404)
        suffix, mimetype = kind_to_suffix[kind]
        path = data_dir / f"{project.designation}{suffix}"
        if not path.exists():
            abort(404)
        return send_file(path, mimetype=mimetype)

    return app


if __name__ == "__main__":
    create_app().run(debug=True, port=5000)
