"""Local interface for editing the supplied SolidWorks model."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from standards import CATALOG
from calculation import calculate
from bulk_materials import catalog as material_catalog
import journal
import questionnaire
import model_diagnostics

BASE = Path(__file__).resolve().parent
CALC_INPUTS = BASE / "calculation_inputs.json"
APPLY_STATUS = BASE / "last_apply_result.json"
LOCK = threading.Lock()


def save_apply_outcome(request, response):
    saved = json.loads((BASE / "state.json").read_text(encoding="utf-8"))
    outcome = {"timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
               "ok": bool(response.get("ok")), "requested_values": request.get("values", {}),
               "saved_values": saved["values"], "design_mode": request.get("design_mode"),
               "saved_at": saved.get("last_applied"),
               **{key: response[key] for key in ("code", "errors", "snapshot", "failure_stage",
                   "rollback_verified", "restored_geometry", "failed_features", "interferences")
                  if key in response}}
    temporary = APPLY_STATUS.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, APPLY_STATUS)
    return outcome

class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, content_type="application/json; charset=utf-8"):
        payload = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, (BASE / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/state":
            self._send(200, (BASE / "state.json").read_bytes())
        elif self.path == "/api/apply-status":
            self._send(200, APPLY_STATUS.read_bytes() if APPLY_STATUS.exists() else b"null")
        elif self.path == "/api/catalog":
            self._send(200, json.dumps(CATALOG, ensure_ascii=False))
        elif self.path == "/api/materials":
            self._send(200, json.dumps(material_catalog(), ensure_ascii=False))
        elif self.path == "/api/calculation-inputs":
            self._send(200, CALC_INPUTS.read_bytes() if CALC_INPUTS.exists() else b"{}")
        elif self.path == "/api/questionnaire":
            self._send(200, json.dumps(questionnaire.read(), ensure_ascii=False))
        elif self.path == "/api/journal":
            self._send(200, json.dumps(journal.view(), ensure_ascii=False))
        elif self.path == "/api/model-diagnostics":
            self._send(200, json.dumps(model_diagnostics.summary(), ensure_ascii=False))
        else:
            self._send(404, json.dumps({"error": "Not found"}))

    def do_POST(self):
        if self.path == "/api/questionnaire":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 8192:
                    raise ValueError("Некорректный размер опроса")
                raw = json.loads(self.rfile.read(length).decode("utf-8"))
                with LOCK:
                    previous = questionnaire.read()
                    saved = questionnaire.save(raw)
                    entry = journal.record_questionnaire(previous, saved)
                self._send(200, json.dumps({"ok": True, "values": saved, "journal_entry": entry}, ensure_ascii=False))
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                self._send(422, json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        elif self.path == "/api/calculate":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 65536:
                    raise ValueError("Некорректный размер запроса")
                request = json.loads(self.rfile.read(length).decode("utf-8"))
                result = calculate(request["values"], request.get("inputs"))
                CALC_INPUTS.write_text(json.dumps(result["inputs"], ensure_ascii=False, indent=2), encoding="utf-8")
                self._send(200, json.dumps({"ok": True, **result}, ensure_ascii=False))
            except (ValueError, KeyError, TypeError) as exc:
                self._send(422, json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False))
        elif self.path == "/api/apply":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length > 65536:
                    raise ValueError("Слишком большой запрос")
                request = self.rfile.read(length).decode("utf-8")
                requested = json.loads(request)
                with LOCK:
                    previous = json.loads((BASE / "state.json").read_text(encoding="utf-8"))
                    child_env = os.environ.copy()
                    child_env["PYTHONIOENCODING"] = "utf-8"
                    result = subprocess.run(
                        [sys.executable, str(BASE / "bridge.py"), "apply"],
                        input=request, text=True, encoding="utf-8", capture_output=True,
                        cwd=BASE, env=child_env,  # Allow CAD rebuild/rollback to finish; do not kill a model edit.
                    )
                    response = json.loads(result.stdout)
                    if response.get("ok"):
                        entry = journal.record_apply(previous, response)
                        response["journal_entry"] = entry
                    else:
                        response["journal_entry"] = journal.record_failed_apply(previous, requested, response)
                    response["apply_outcome"] = save_apply_outcome(requested, response)
                self._send(200 if response.get("ok") else 422, json.dumps(response, ensure_ascii=False))
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False))
        elif self.path == "/api/open":
            try:
                child_env = os.environ.copy()
                child_env["PYTHONIOENCODING"] = "utf-8"
                with LOCK:
                    result = subprocess.run(
                        [sys.executable, str(BASE / "open_assembly.py")],
                        text=True, encoding="utf-8", capture_output=True,
                        timeout=600, cwd=BASE, env=child_env,
                    )
                    response = json.loads(result.stdout)
                self._send(200 if response.get("ok") else 500, json.dumps(response, ensure_ascii=False))
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False))
        elif self.path == "/api/drawings":
            try:
                with LOCK:
                    child_env = os.environ.copy()
                    child_env["PYTHONIOENCODING"] = "utf-8"
                    result = subprocess.run(
                        [sys.executable, str(BASE / "drawings.py")],
                        text=True, encoding="utf-8", capture_output=True,
                        cwd=BASE, env=child_env,  # Drawing creation must finish or report its own failure.
                    )
                    response = json.loads(result.stdout)
                    if response.get("ok"):
                        response["journal_entry"] = journal.record_drawings(response)
                self._send(200 if response.get("ok") else 500, json.dumps(response, ensure_ascii=False))
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        else:
            self._send(404, json.dumps({"error": "Not found"}))

    def log_message(self, fmt, *args):
        print(fmt % args)

if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 59374), Handler)
    url = f"http://127.0.0.1:{server.server_port}/"
    print("Интерфейс шнека:", url, flush=True)
    if os.environ.get("SHNEK_NO_BROWSER") != "1":
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
