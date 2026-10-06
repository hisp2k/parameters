@echo off
cd /d "%~dp0"
echo ===============================================
echo  Installing dependencies (requirements.txt)...
echo ===============================================
pip install -r requirements.txt
echo.
echo ===============================================
echo  Starting web UI. Open in your browser:
echo  http://127.0.0.1:5000/
echo  To stop the server, close this window.
echo ===============================================
python -m webapp.app
pause
