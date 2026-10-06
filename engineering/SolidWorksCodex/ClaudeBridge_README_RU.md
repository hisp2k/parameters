# ClaudeBridge — прямой доступ Claude к коннектору

Codex обычно общается с коннектором через MCP по stdio. У Claude (в облачной
сессии) нет постоянного stdio-канала к вашему компьютеру и нет возможности
печатать в командной строке (доступ только "клик" — только левый клик мышью,
без ввода текста). `ClaudeBridge` — это простой файловый мост в обход этого
ограничения, использующий уже проверенный режим `--worker`.

## Как это работает

1. Скопируйте `ClaudeBridge\request.example.json` как
   `ClaudeBridge\request.json`. Затем Claude записывает в `request.json` вызов:
   ```json
   {"tool": "sw_create_plate", "arguments": {"length_mm": 100, "width_mm": 60,
     "thickness_mm": 5, "hole_diameter_mm": 8, "edge_offset_x_mm": 10, "edge_offset_y_mm": 10}}
   ```
2. Claude через компьютерное управление дважды кликает `CLAUDE_CALL.cmd`
   (или `CLAUDE_CALL.ps1`) в корне `SolidWorksCodex`.
3. Скрипт читает `request.json`, вызывает
   `SolidWorksLocal.exe --worker <tool> <base64(arguments)>` — тот же самый
   путь, что уже используют тестовые скрипты (`CREATE_TEST_PLATE.ps1` и
   другие), — и записывает результат в `ClaudeBridge\response.json`.
4. Claude читает `response.json` (через мост к файлам компьютера) и видит
   результат.

## Формат response.json

```json
{
  "ok": true,
  "tool": "sw_create_plate",
  "arguments": { ... },
  "worker_exit_code": 0,
  "requested_at_utc": "2026-09-12T20:00:00.000Z",
  "completed_at_utc": "2026-09-12T20:00:01.500Z",
  "bridge_version": "1.0",
  "result": { "ok": true, "data": { ... } }
}
```

Если `request.json` отсутствует, повреждён, не содержит поле `tool`, или
`SolidWorksLocal.exe` не удалось запустить — `response.json` содержит
`"ok": false` и объект `error` с понятным кодом/сообщением. Ошибка
конкретного инструмента (например `INVALID_ARGUMENTS`,
`GEOMETRY_VERIFICATION_FAILED`) приходит внутри `result`, как обычно.

## Важно

- Мост ничего не обходит: все проверки безопасности и верификации
  (только локальные фиксированные диски, запрет PDM-путей, обязательные
  бэкапы, аналитическая проверка объёма/топологии) отрабатывают точно так
  же, как при вызове через Codex по MCP — они находятся в самом
  `SolidWorksLocal.exe`, а не в мосте.
- `request.json`/`response.json` — временные файлы одного вызова. Мост не
  хранит историю; если нужна история вызовов, смотрите `Reports\` и
  `%LOCALAPPDATA%\SolidWorksCodex\Workspace`.
- В комплекте нет активного `request.json`, поэтому случайный двойной щелчок
  не создаст модель. Пример по умолчанию вызывает только безопасный `sw_status`.
- Список доступных `tool` — те же имена, что видны в `tools/list` MCP
  (`sw_create_plate`, `sw_create_part_from_plan`, `sw_create_turned_part_from_plan`,
  и т.д.). Неверное имя инструмента вернётся как обычная ошибка `Fault` в
  `result.error`.
