# -*- coding: utf-8 -*-
"""Correlated local ClaudeBridge transport. Requires bridge 3.1 or newer.
Requests/results remain on disk for diagnosis; no implicit retries after failures.
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import math
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional


class BridgeError(RuntimeError):
    """Транспортная ошибка моста — отличать от ошибки конкретного tool-вызова."""


@dataclass
class BridgeResponse:
    ok: bool
    tool: str
    result: Optional[dict]
    raw: dict
    error: Optional[dict] = None

    @staticmethod
    def from_dict(d: dict) -> "BridgeResponse":
        return BridgeResponse(
            ok=d.get("ok") is True, tool=d.get("tool", ""),
            result=d.get("result"), raw=d, error=d.get("error"),
        )


class BridgeTransport(ABC):
    @abstractmethod
    def call(self, tool: str, arguments: dict, timeout_s: float = 60.0) -> BridgeResponse: ...


@dataclass
class FileBridgeTransport(BridgeTransport):
    """
    Реальный транспорт по протоколу ClaudeBridge. `repo_root` — корень
    репозитория SolidWorksCodex НА РАБОЧЕЙ СТАНЦИИ (где лежат
    CLAUDE_CALL.ps1/.cmd и ClaudeBridge/), не путь в этой облачной среде.
    """

    repo_root: Path
    powershell_exe: str = "powershell"   # на некоторых станциях — "pwsh"
    poll_interval_s: float = 0.2

    def _bridge_dir(self) -> Path:
        return self.repo_root / "ClaudeBridge"

    def call(self, tool: str, arguments: dict, timeout_s: float = 60.0) -> BridgeResponse:
        if platform.system() != "Windows":
            raise BridgeError(
                "FileBridgeTransport вызывает CLAUDE_CALL.ps1 через PowerShell — это работает "
                "только на Windows-рабочей станции с установленным SolidWorks. Текущая среда "
                f"выполнения — {platform.system()!r}, что честно означает: живая интеграция "
                "недоступна отсюда (см. cad_adapter/interface.py — LocalBridgeCadAdapter.can_read())."
            )
        if shutil.which(self.powershell_exe) is None:
            raise BridgeError(f"Исполняемый файл {self.powershell_exe!r} не найден в PATH.")

        script = self.repo_root / "CLAUDE_CALL.ps1"
        if not script.exists():
            raise BridgeError(f"Не найден {script} — это не тот каталог репозитория SolidWorksCodex?")

        bridge_dir = self._bridge_dir()
        bridge_dir.mkdir(parents=True, exist_ok=True)
        if isinstance(timeout_s, bool) or not math.isfinite(timeout_s) or not 5 <= timeout_s <= 600:
            raise BridgeError("timeout_s must be finite and between 5 and 600 seconds")
        request_id = uuid.uuid4().hex
        requests_dir = bridge_dir / "requests"
        requests_dir.mkdir(exist_ok=True)
        request_path = requests_dir / f"{request_id}.json"
        response_path = bridge_dir / "responses" / f"{request_id}.json"
        request_path.write_text(json.dumps({
            "request_id": request_id, "tool": tool, "arguments": arguments,
            "timeout_ms": int(timeout_s * 1000),
        }, ensure_ascii=False), encoding="utf-8")
        try:
            process = subprocess.run(
                [self.powershell_exe, "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", str(script), "-RequestFile", str(request_path.resolve())],
                cwd=str(self.repo_root), timeout=timeout_s + 30,
                capture_output=True, check=False,
            )
        except subprocess.TimeoutExpired as e:
            # The worker may still exist. The bridge lock is deliberately not removed.
            raise BridgeError(f"UNKNOWN: bridge deadline exceeded; inspect request {request_id}, do not retry") from e
        except OSError as e:
            raise BridgeError(f"Bridge launch failed: {e}") from e
        try:
            raw = json.loads(response_path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as e:
            raise BridgeError(f"UNKNOWN: missing/invalid response for {request_id}; do not retry") from e
        if not isinstance(raw, dict) or type(raw.get("ok")) is not bool:
            raise BridgeError("Invalid bridge response envelope")
        if raw.get("request_id") != request_id or raw.get("tool") != tool:
            raise BridgeError("Response identity mismatch")
        if raw["ok"] and process.returncode != 0:
            raise BridgeError("Response contradicts bridge exit status")
        if raw["ok"] and (not isinstance(raw.get("result"), dict) or raw["result"].get("ok") is not True):
            raise BridgeError("Bridge success has no successful worker result")
        return BridgeResponse.from_dict(raw)


@dataclass
class FakeBridgeTransport(BridgeTransport):
    """
    Для контрактных тестов адаптера (раздел 5). `responses` — словарь
    tool -> BridgeResponse ИЛИ tool -> callable(arguments) -> BridgeResponse
    (для ответов, зависящих от аргументов вызова).
    """

    responses: dict[str, Any] = field(default_factory=dict)
    calls: list[tuple[str, dict]] = field(default_factory=list)

    def call(self, tool: str, arguments: dict, timeout_s: float = 60.0) -> BridgeResponse:
        self.calls.append((tool, dict(arguments)))
        handler = self.responses.get(tool)
        if handler is None:
            return BridgeResponse(
                ok=False, tool=tool, result=None,
                raw={"ok": False, "tool": tool},
                error={"code": "UNEXPECTED_TOOL", "message": f"Фейковый транспорт не настроен на {tool!r}."},
            )
        if callable(handler):
            return handler(arguments)
        return handler
