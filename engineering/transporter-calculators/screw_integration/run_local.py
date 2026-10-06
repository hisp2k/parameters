"""Start the local calculator on a free loopback port, or reuse this instance."""
from pathlib import Path
import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser

BASE = Path(__file__).resolve().parent
DEPS = BASE / ".deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONPATH"] = str(DEPS) + os.pathsep + str(BASE)
STATE = BASE / ".local-server.json"


def available_port():
    # Let Windows assign one free port. No process is stopped to free a port.
    with socket.socket() as listener:
        if os.name == "nt":
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def healthy(url):
    try:
        with urllib.request.urlopen(url + "/_stcore/health", timeout=1) as result:
            return result.status == 200
    except (OSError, ValueError):
        return False


def existing_server():
    try:
        info = json.loads(STATE.read_text(encoding="utf-8"))
        pid = int(info["pid"])
        # Check the exact launcher path before trusting a stale PID/port record.
        command = f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"
        commandline = subprocess.check_output(["powershell", "-NoProfile", "-Command", command],
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).decode(errors="replace")
        if str(BASE / "run_local.py").lower() in commandline.lower() and "--serve" in commandline and healthy(info["url"]):
            return info
    except (OSError, KeyError, ValueError, subprocess.SubprocessError):
        pass
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", type=int)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if args.serve:
        from streamlit.web import cli
        sys.argv = ["streamlit", "run", str(BASE / "transporter_app_local.py"),
                    "--global.developmentMode=false",
                    "--server.address=127.0.0.1", f"--server.port={args.serve}",
                    "--server.headless=true", "--browser.gatherUsageStats=false",
                    "--server.fileWatcherType=none", "--server.maxUploadSize=20"]
        cli.main()
        return
    info = existing_server()
    if not info:
        for attempt in range(3):
            port = available_port()
            url = f"http://127.0.0.1:{port}"
            with (BASE / "local-server.log").open("ab") as log:
                child = subprocess.Popen([sys.executable, "-X", "utf8", str(BASE / "run_local.py"), "--serve", str(port)],
                    cwd=BASE, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            for tick in range(80):
                if child.poll() is not None:
                    break
                if healthy(url):
                    info = {"pid": child.pid, "port": port, "url": url, "project": str(BASE)}
                    STATE.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
                    break
                time.sleep(0.25)
            if info:
                break
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=10)
        if not info:
            raise RuntimeError("Приложение не запустилось. Подробности: " + str(BASE / "local-server.log"))
    print(info["url"], flush=True)
    if not args.no_browser:
        webbrowser.open(info["url"])


if __name__ == "__main__":
    main()
