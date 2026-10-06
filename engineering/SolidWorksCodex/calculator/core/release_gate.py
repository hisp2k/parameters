# -*- coding: utf-8 -*-
"""
Блокировки выпуска (раздел 20 задания).

evaluate() возвращает список причин блокировки. Пустой список означает
"выпуск не заблокирован ЭТИМИ проверками" — это НЕ означает, что комплект
готов к производству, если какая-то проверка ещё не реализована в этой
системе (см. README_RU.md калькулятора, раздел "Что предварительное").

ИСПРАВЛЕНИЕ (раздел 1.А задания): раньше можно было получить пустой список
причин, просто расставив `method=ANALYTICAL` по позициям прочности и
`done=True` по модулям, без единого реального результата расчёта. Теперь
evaluate() проверяет:

- завершённость И успешность расчётов (не просто "есть объект результата",
  а requirement_met и motor_selection_ok, раздельно от предупреждений);
- актуальность относительно ТЕКУЩИХ входных данных (project.is_calc_stale(),
  ModuleStatus.is_current(), VerificationRecord.is_current_for());
- реальный охват BOM (strength_coverage.uncovered() с проверкой ревизии);
- действительность обоснованных исключений (NOT_APPLICABLE требует
  утверждённого обоснования, не просто текстового поля);
- согласованность привода и защиты (project.drive_selection в связке с
  core/drive_selection.py — protection_consistent, см. ниже);
- готовность КД и технологии (ModuleStatus.is_current(), не просто done);
- техническую проверку другим специалистом (project.technical_review,
  reviewer != исполнитель);
- утверждение руководителем — отдельная запись `release_approval`, а не
  сам факт того, что evaluate() вызван с requesting_role=HEAD.

Раздел 20 отдельно требует: "согласование заказчиком компоновки не
заменяет инженерную проверку" и "не распространяй блокировку одного
модуля на независимую разработку остальных" — поэтому evaluate()
перечисляет ВСЕ причины сразу, а не останавливается на первой, и не мешает
работать над независимыми модулями (это ответственность вызывающего кода,
не этой функции).
"""

from __future__ import annotations

from calculator.core.project import Project
from calculator.core.strength_coverage import uncovered
from calculator.core.roles import Role, can


def evaluate(project: Project, requesting_role: Role) -> list[str]:
    reasons: list[str] = []

    if not can(requesting_role, "authorize_production_release"):
        reasons.append(
            f"Роль {requesting_role.value!r} не имеет права утверждать производственный выпуск "
            "(раздел 5 — эта роль зарезервирована за руководителем)."
        )

    if project.questionnaire is None:
        reasons.append("Не заполнены исходные данные (опросный лист) — недостаточно критических данных.")

    input_fingerprint = project.compute_input_fingerprint()

    if project.engineering_result is None and project.tube_engineering_result is None:
        reasons.append("Инженерное ядро не рассчитано.")
    elif project.engineering_result is None and project.tube_engineering_result is not None:
        # SHAFTED_TUBE (Issue #3): расчёт запускался (core/tube_engineering.py),
        # но честно вернул статус BLOCKED — это не то же самое, что "не
        # запускался вовсе", поэтому причина формулируется точнее, со ссылкой
        # на конкретные блокеры, а не общей фразой "не рассчитано".
        tr = project.tube_engineering_result
        reasons.append(
            f"Инженерное ядро трубного шнека заблокировано ({len(tr.blockers)} блокер(ов)) — "
            "см. project.tube_engineering_result.blockers; выпуск невозможен, пока не устранены."
        )
        if project.is_calc_stale():
            reasons.append(
                "Инженерный расчёт устарел: входные данные изменились после последнего расчёта "
                "(раздел 1.Б) — требуется пересчёт для текущей ревизии."
            )
    else:
        er = project.engineering_result
        if project.is_calc_stale():
            reasons.append(
                "Инженерный расчёт устарел: входные данные изменились после последнего расчёта "
                "(раздел 1.Б) — требуется пересчёт для текущей ревизии."
            )
        if er.warnings:
            reasons.append(
                f"Инженерный расчёт содержит {len(er.warnings)} предупреждени(е/й), "
                "требующих проверки инженером — расчёт не подтверждён."
            )
        if not er.motor_selection_ok:
            reasons.append("Подходящий мотор не подобран расчётом — привод не согласован.")
        if not er.requirement_met:
            reasons.append(
                f"Требуемая производительность не выполняется расчётом: достижимо "
                f"{er.productivity_achievable_t_per_h} т/ч из требуемых "
                f"{er.productivity_required_t_per_h} т/ч."
            )

    if not project.engineer_confirmed_assumptions:
        reasons.append(
            "Инженер не подтвердил исходные данные и допущения (раздел 2 роли «Инженер»)."
        )

    # --- прочность: реальный охват, а не факт выбора метода -----------------
    if not project.strength_registry:
        reasons.append("Реестр прочности пуст — охват фактической BOM не подтверждён.")
    uncovered_items = uncovered(project.strength_registry, project.revision, input_fingerprint)
    if uncovered_items:
        names = ", ".join(sorted({item.component_class for item in uncovered_items}))
        reasons.append(
            f"{len(uncovered_items)} позици(я/й) BOM без подтверждённого И актуального способа "
            f"проверки прочности (число + критерий + проверка другим специалистом + текущая "
            f"ревизия): {names}."
        )

    # --- модули: is_current(), а не голый done -------------------------------
    for label, module in (
        ("Подбор привода", project.drive_selection),
        ("Синхронизация CAD", project.cad_sync),
        ("КД и BOM", project.kd_bom),
        ("Технология", project.technology),
    ):
        if not module.is_current(project.revision, input_fingerprint):
            reasons.append(f"{label} не завершён(а) или устарел(а) для текущей ревизии: {module.note}")

    # --- согласованность привода и защиты (раздел 4) ------------------------
    # ИСПРАВЛЕНИЕ: раньше это была подстрока "protection_consistent=False" в
    # текстовом evidence — теперь отдельное структурированное поле ModuleStatus
    # (заполняется в app.py из DriveSelectionResult.protection_consistent).
    if project.drive_selection.done and project.drive_selection.protection_consistent is False:
        reasons.append(
            "Подбор привода завершён, но защита (тепловая/токовая отсечка) НЕ согласована "
            "с фактическими характеристиками выбранного привода — раздел 4."
        )

    # --- техническая проверка другим специалистом (раздел 1.А) --------------
    if project.technical_review is None:
        reasons.append("Техническая проверка другим специалистом не зафиксирована (раздел 1.А).")
    else:
        tr = project.technical_review
        if not tr.is_independent():
            reasons.append(
                f"Проверяющий ({tr.reviewer_name!r}) совпадает с исполнителем "
                f"({tr.prepared_by_name!r}) — это не независимая проверка (раздел 1.А)."
            )
        if tr.product_revision != project.revision or tr.input_fingerprint != input_fingerprint:
            reasons.append("Техническая проверка относится к устаревшей ревизии/входным данным.")

    # --- утверждение руководителем — отдельная запись, не факт роли ---------
    if project.release_approval is None:
        reasons.append("Выпуск не утверждён руководителем (нет записи об утверждении, раздел 1.А).")
    elif project.release_approval.product_revision != project.revision:
        reasons.append("Утверждение руководителем относится к устаревшей ревизии — требуется повторное утверждение.")

    return reasons


def is_release_blocked(project: Project, requesting_role: Role) -> bool:
    return len(evaluate(project, requesting_role)) > 0
